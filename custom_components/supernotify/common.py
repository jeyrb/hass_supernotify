import logging
from abc import abstractmethod

from homeassistant.components.notify import ATTR_TARGET
from homeassistant.const import (
    ATTR_DOMAIN,
    ATTR_SERVICE,
    CONF_CONDITION,
    CONF_DEFAULT,
    CONF_ENABLED,
    CONF_ENTITIES,
    CONF_METHOD,
    CONF_NAME,
    CONF_SERVICE,
    CONF_TARGET,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import condition
from homeassistant.helpers import config_validation as cv

from . import (
    ATTR_SCENARIOS,
    CONF_DELIVERY,
    CONF_MESSAGE,
    CONF_OCCUPANCY,
    CONF_PERSON,
    CONF_PRIORITY,
    CONF_RECIPIENTS,
    CONF_TITLE,
    OCCUPANCY_ALL,
    OCCUPANCY_ALL_IN,
    OCCUPANCY_ALL_OUT,
    OCCUPANCY_ANY_IN,
    OCCUPANCY_ANY_OUT,
    OCCUPANCY_NONE,
    OCCUPANCY_ONLY_IN,
    OCCUPANCY_ONLY_OUT,
    PRIORITY_MEDIUM,
)

_LOGGER = logging.getLogger(__name__)


class SuperNotificationContext:
    def __init__(self, hass_url: str = None, hass_name: str = None,
                 links=(), recipients=(),
                 mobile_actions=None,
                 templates=(),
                 method_defaults=None):
        self.hass_url = hass_url
        self.hass_name = hass_name
        self.links = links
        self.recipients = recipients
        self.mobile_actions = mobile_actions or {}
        self.templates = templates
        self.method_defaults = method_defaults or {}
        self.people = {r[CONF_PERSON]: r for r in recipients}


class DeliveryMethod:
    @abstractmethod
    def __init__(self,
                 method: str,
                 service_required: bool,
                 hass: HomeAssistant,
                 context: SuperNotificationContext,
                 deliveries: dict):
        self.hass = hass
        self.context = context
        self.method = method
        self.service_required = service_required
        self.default_delivery = None
        self.valid_deliveries = {}
        self.invalid_deliveries = {}
        self.disabled_deliveries = {}
        self.default_deliveries(deliveries)
        self.validate_deliveries(deliveries)

    def default_deliveries(self, deliveries):
        method_defaults = self.context.method_defaults.get(self.method, {})
        for delivery_config in deliveries.values():
            if not delivery_config.get(CONF_SERVICE) and method_defaults.get(CONF_SERVICE):
                delivery_config[CONF_SERVICE] = method_defaults[CONF_SERVICE]
            if not delivery_config.get(CONF_TARGET) and method_defaults.get(CONF_TARGET):
                delivery_config[CONF_TARGET] = method_defaults[CONF_TARGET]
            if not delivery_config.get(CONF_ENTITIES) and method_defaults.get(CONF_ENTITIES):
                delivery_config[CONF_ENTITIES] = method_defaults[CONF_ENTITIES]

    def validate_deliveries(self, deliveries):
        """
        Validate list of deliveries at startup for this method

        Args:
            deliveries (dict): Dict of delivery name -> delivery configuration
        """
        for d, dc in deliveries.items():
            if dc and dc.get(CONF_METHOD) == self.method:
                if not dc.get(CONF_ENABLED, True):
                    _LOGGER.debug("SUPERNOTIFY Delivery disabled for %s", d)
                    self.disabled_deliveries[d] = dc
                    continue
                if self.service_required and not dc.get(CONF_SERVICE):
                    _LOGGER.debug("SUPERNOTIFY No service for %s", d)
                    self.invalid_deliveries[d] = dc
                    continue
                delivery_condition = dc.get(CONF_CONDITION)
                if delivery_condition:
                    if not condition.async_validate_condition_config(self.hass, delivery_condition):
                        _LOGGER.warning(
                            "SUPERNOTIFY Invalid condition for %s: %s", d, delivery_condition)
                        self.invalid_deliveries[d] = dc
                        continue

                self.valid_deliveries[d] = dc
                if dc.get(CONF_DEFAULT):
                    if self.default_delivery:
                        _LOGGER.warning(
                            "SUPERNOTIFY Multiple default deliveries, skipping %s", d)
                    else:
                        self.default_delivery = dc

    async def deliver(self,
                      message=None,
                      title=None,
                      config=None,
                      scenarios=None,
                      target=None,
                      priority=PRIORITY_MEDIUM,
                      data=None,
                      recipients_override=None):
        """
        Deliver a notification

        Args:
            message (_type_, optional): Message to send. Defaults to None, e.g for methods like chime 
            title (_type_, optional): Title of message. Defaults to None, e.g for methods like chime 
            config (_type_, optional): Delivery Configuration. Defaults to None.
            scenarios (_type_, optional): List of current scenarios. Defaults to None.
            target (_type_, optional): Specific targets, method specific or Person. Defaults to None.
            priority (_type_, optional): Message priority. Defaults to Medium.
            data (_type_, optional): Optional service data. Defaults to None.
        """
        config = config or self.default_delivery or {}
        data = data or {}
        scenarios = scenarios or {}
        # message and title reverse the usual defaulting, delivery config overrides runtime call
        message = config.get(CONF_MESSAGE, message)
        title = config.get(CONF_TITLE, title)

        for reserved in (ATTR_DOMAIN, ATTR_SERVICE):
            if reserved in data:
                _LOGGER.warning(
                    "SUPERNOTIFY Removing reserved keyword from data %s:%s", reserved, data.get(reserved))
                del data[reserved]
        delivery_priorities = config.get(CONF_PRIORITY) or ()
        if priority and delivery_priorities and priority not in delivery_priorities:
            _LOGGER.debug(
                "SUPERNOTIFY Skipping delivery for %s based on priority (%s)", self.method, priority)
            return
        if not await self.evaluate_delivery_conditions(config):
            _LOGGER.debug(
                "SUPERNOTIFY Skipping delivery for %s based on conditions", self.method)
            return

        targets = self.build_targets(config, target, recipients_override)
        delivery_scenarios = config.get(ATTR_SCENARIOS)
        if delivery_scenarios and not any(s in delivery_scenarios for s in scenarios):
            _LOGGER.debug(
                "Skipping delivery without matched scenario (%s) vs (%s)", scenarios, delivery_scenarios)
            return
        await self._delivery_impl(message=message,
                                  title=title,
                                  targets=targets,
                                  priority=priority,
                                  scenarios=scenarios,
                                  data=data,
                                  config=config)

    @abstractmethod
    async def _delivery_impl(message=None, title=None, config=None):
        pass

    def select_target(self, target):
        return True

    def recipient_target(self, recipient):
        return []

    def build_targets(self, delivery_config, target, recipients_override):
        recipients = []
        if target:
            # first priority is explicit target set on notify call, which overrides everything else
            for t in target:
                if t in self.context.people:
                    recipients.append(self.context.people[t])
                else:
                    recipients.append({ATTR_TARGET: t})
            _LOGGER.debug(
                "SUPERNOTIFY %s Overriding with explicit targets: %s", __name__, recipients)
        else:
            # second priority is explicit entities on delivery
            if delivery_config and CONF_ENTITIES in delivery_config:
                recipients.extend({ATTR_TARGET: e}
                                  for e in delivery_config.get(CONF_ENTITIES))
                _LOGGER.debug(
                    "SUPERNOTIFY %s Using delivery config entities: %s", __name__, recipients)
            # third priority is explicit target on delivery
            if delivery_config and CONF_TARGET in delivery_config:

                recipients.extend({ATTR_TARGET: e}
                                  for e in delivery_config.get(CONF_TARGET))
                _LOGGER.debug(
                    "SUPERNOTIFY %s Using delivery config targets: %s", __name__, recipients)

            # next priority is explicit recipients on delivery
            if delivery_config and CONF_RECIPIENTS in delivery_config:
                recipients = delivery_config[CONF_RECIPIENTS]
                _LOGGER.debug("SUPERNOTIFY %s Using overridden recipients: %s",
                              __name__, recipients)

            # If target not specified on service call or delivery, then default to std list of recipients
            elif not delivery_config or (CONF_TARGET not in delivery_config and CONF_ENTITIES not in delivery_config):
                recipients = self.filter_recipients_by_occupancy(
                    delivery_config.get(CONF_OCCUPANCY, OCCUPANCY_ALL))
                recipients = [r for r in recipients if recipients_override is None or r.get(
                    CONF_PERSON) in recipients_override]
                _LOGGER.debug("SUPERNOTIFY %s Using recipients: %s",
                              __name__, recipients)

        # now the list of recipients determined, resolve this to target addresses or entities
        targets = []
        for recipient in recipients:
            # reuse standard recipient attributes like email or phone
            self._safe_extend(targets, self.recipient_target(recipient))
            # use entities or targets set at a method level for recipient
            if CONF_DELIVERY in recipient and delivery_config[CONF_NAME] in recipient.get(CONF_DELIVERY, {}):
                recp_meth_cust = recipient.get(
                    CONF_DELIVERY, {}).get(delivery_config[CONF_NAME], {})
                self._safe_extend(
                    targets, recp_meth_cust.get(CONF_ENTITIES, []))
                self._safe_extend(targets, recp_meth_cust.get(CONF_TARGET, []))
            elif ATTR_TARGET in recipient:
                # non person recipient
                self._safe_extend(targets, recipient.get(ATTR_TARGET))

        pre_filter_count = len(targets)
        _LOGGER.debug("SUPERNOTIFY Prefiltered targets: %s", targets)
        targets = [t for t in targets if self.select_target(t)]
        if len(targets) < pre_filter_count:
            _LOGGER.debug("SUPERNOTIFY %s target list filtered by %s to %s", __name__,
                          pre_filter_count-len(targets), targets)
        if not targets:
            _LOGGER.warning("SUPERNOTIFY %s No targets resolved", __name__)
        return targets

    def _safe_extend(self, target, extension):
        if isinstance(extension, (list, tuple)):
            target.extend(extension)
        elif extension:
            target.append(extension)
        return target

    def filter_recipients_by_occupancy(self, occupancy):
        if occupancy == OCCUPANCY_ALL:
            return self.context.recipients
        elif occupancy == OCCUPANCY_NONE:
            return []

        at_home = []
        away = []
        for r in self.context.recipients:
            # all recipients checked for occupancy, regardless of override
            try:
                tracker = self.hass.states.get(r["person"])
                if tracker is not None and tracker.state == "home":
                    at_home.append(r)
                else:
                    away.append(r)
            except Exception as e:
                _LOGGER.warning(
                    "Unable to determine occupied status for %s: %s", r["person"], e)
        if occupancy == OCCUPANCY_ALL_IN:
            return self.context.recipients if len(away) == 0 else []
        elif occupancy == OCCUPANCY_ALL_OUT:
            return self.context.recipients if len(at_home) == 0 else []
        elif occupancy == OCCUPANCY_ANY_IN:
            return self.context.recipients if len(at_home) > 0 else []
        elif occupancy == OCCUPANCY_ANY_OUT:
            return self.context.recipients if len(away) > 0 else []
        elif occupancy == OCCUPANCY_ONLY_IN:
            return at_home
        elif occupancy == OCCUPANCY_ONLY_OUT:
            return away
        else:
            _LOGGER.warning(
                "SUPERNOTIFY Unknown occupancy tested: %s" % occupancy)
            return []

    async def evaluate_delivery_conditions(self, delivery_config):
        if CONF_CONDITION not in delivery_config:
            return True
        else:
            try:
                conditions = cv.CONDITION_SCHEMA(
                    delivery_config.get(CONF_CONDITION))
                test = await condition.async_from_config(self.hass, conditions)
                return test(self.hass)
            except Exception as e:
                _LOGGER.error("SUPERNOTIFY Condition eval failed: %s", e)
                raise
