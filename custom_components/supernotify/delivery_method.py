import copy
import logging
from abc import abstractmethod
from homeassistant.components.notify import (
    ATTR_TARGET,
)
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
    CONF_DELIVERY,
    CONF_MESSAGE,
    CONF_OCCUPANCY,
    CONF_PERSON,
    CONF_PRIORITY,
    CONF_RECIPIENTS,
    CONF_TITLE,
    CONF_DATA,
    OCCUPANCY_ALL,
    OCCUPANCY_ALL_IN,
    OCCUPANCY_ALL_OUT,
    OCCUPANCY_ANY_IN,
    OCCUPANCY_ANY_OUT,
    OCCUPANCY_NONE,
    OCCUPANCY_ONLY_IN,
    OCCUPANCY_ONLY_OUT,
    RESERVED_DELIVERY_NAMES,
)
from .notification import Notification
from .configuration import SupernotificationConfiguration

_LOGGER = logging.getLogger(__name__)


class DeliveryMethod:
    @abstractmethod
    def __init__(self,
                 hass: HomeAssistant,
                 context: SupernotificationConfiguration,
                 deliveries: dict):
        self.hass = hass
        self.context = context
        self.default_delivery = None
        self.method_deliveries = {d: dc for d, dc in deliveries.items(
        ) if dc.get(CONF_METHOD) == self.method} if deliveries else {}

    async def initialize(self):
        assert self.method is not None
        self.apply_method_defaults()
        self.valid_deliveries = await self.validate_deliveries()

    def validate_service(self, service):
        ''' Override in subclass if delivery method has fixed service or doesn't require one'''
        return service is not None and service.startswith("notify.")

    def apply_method_defaults(self):
        method_defaults = self.context.method_defaults.get(self.method, {})
        for delivery_name, delivery_config in self.method_deliveries.items():
            if not delivery_config.get(CONF_NAME):
                delivery_config[CONF_NAME] = delivery_name  # for minimal tests
            if not delivery_config.get(CONF_SERVICE) and method_defaults.get(CONF_SERVICE):
                delivery_config[CONF_SERVICE] = method_defaults[CONF_SERVICE]
                _LOGGER.debug("SUPERNOTIFY Defaulting delivery % to service %s",
                              delivery_name, delivery_config[CONF_SERVICE])
            if not delivery_config.get(CONF_TARGET) and method_defaults.get(CONF_TARGET):
                delivery_config[CONF_TARGET] = method_defaults[CONF_TARGET]
                _LOGGER.debug("SUPERNOTIFY Defaulting delivery % to target %s",
                              delivery_name, delivery_config[CONF_TARGET])
            if not delivery_config.get(CONF_ENTITIES) and method_defaults.get(CONF_ENTITIES):
                delivery_config[CONF_ENTITIES] = method_defaults[CONF_ENTITIES]
                _LOGGER.debug("SUPERNOTIFY Defaulting delivery % to entities %s",
                              delivery_name, delivery_config[CONF_ENTITIES])

    async def validate_deliveries(self):
        """
        Validate list of deliveries at startup for this method

        Args:
            deliveries (dict): Dict of delivery name -> delivery configuration
        """
        valid_deliveries = {}
        for d, dc in self.method_deliveries.items():
            # don't care about ENABLED here since disabled deliveries can be overridden
            if d in RESERVED_DELIVERY_NAMES:
                _LOGGER.warning(
                    "SUPERNOTIFY Delivery uses reserved word %s", d)
                continue             
            if not self.validate_service(dc.get(CONF_SERVICE)):
                _LOGGER.warning(
                    "SUPERNOTIFY Invalid service definition for delivery %s (%s)", d, dc.get(CONF_SERVICE))
                continue
            delivery_condition = dc.get(CONF_CONDITION)
            if delivery_condition:
                if not await condition.async_validate_condition_config(self.hass, delivery_condition):
                    _LOGGER.warning(
                        "SUPERNOTIFY Invalid delivery condition for %s: %s", d, delivery_condition)
                    continue

            valid_deliveries[d] = dc

            if dc.get(CONF_DEFAULT):
                if self.default_delivery:
                    _LOGGER.warning(
                        "SUPERNOTIFY Multiple default deliveries, skipping %s", d)
                else:
                    self.default_delivery = dc

        if not self.default_delivery:
            method_definition = self.context.method_defaults.get(self.method)
            if method_definition:
                _LOGGER.info(
                    "SUPERNOTIFY Building default delivery for %s from method %s", self.method, method_definition)
                self.default_delivery = method_definition

        return valid_deliveries

    async def deliver(self,
                      notification: Notification,
                      delivery_config: dict = None) -> bool:
        """
        Deliver a notification

        Args:
            message (_type_, optional): Message to send. Defaults to None, e.g for methods like chime 
            delivery_config (_type_, optional): Delivery Configuration. Defaults to None.
        """
        delivery_config = delivery_config or self.default_delivery or {}
        data = notification.delivery_data(delivery_config.get(CONF_NAME))
        scenarios = notification.delivery_scenarios(
            delivery_config.get(CONF_NAME))
        # message and title reverse the usual defaulting, delivery config overrides runtime call
        message = delivery_config.get(CONF_MESSAGE, notification.message)
        title = delivery_config.get(CONF_TITLE, notification.title)

        for reserved in (ATTR_DOMAIN, ATTR_SERVICE):
            if data and reserved in data:
                _LOGGER.warning(
                    "SUPERNOTIFY Removing reserved keyword from data %s:%s", reserved, data.get(reserved))
                del data[reserved]
        delivery_priorities = delivery_config.get(CONF_PRIORITY) or ()
        if notification.priority and delivery_priorities and notification.priority not in delivery_priorities:
            _LOGGER.debug(
                "SUPERNOTIFY Skipping delivery for %s based on priority (%s)", self.method, notification.priority)
            return False
        if not await self.evaluate_delivery_conditions(delivery_config):
            _LOGGER.debug(
                "SUPERNOTIFY Skipping delivery for %s based on conditions", self.method)
            return False

        target_bundles = self.build_targets(
            delivery_config, notification.target, notification.recipients_override)
        deliveries = 0
        for targets, custom_data in target_bundles:
            if custom_data:
                target_data = copy.deepcopy(data) if data else {}
                target_data |= custom_data
            else:
                target_data = data
            success = await self._delivery_impl(message=message,
                                                title=title,
                                                targets=targets,
                                                priority=notification.priority,
                                                scenarios=scenarios,
                                                data=target_data,
                                                config=delivery_config)
            if success:
                deliveries += 1
        return deliveries > 0

    @abstractmethod
    async def _delivery_impl(message=None, title=None,
                             targets=None, priority=None,
                             scenarios=None, data=None, config=None) -> bool:
        return False

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
                recipients.extend(delivery_config[CONF_RECIPIENTS])
                _LOGGER.debug("SUPERNOTIFY %s Using overridden recipients: %s",
                              self.method, recipients)

            # If target not specified on service call or delivery, then default to std list of recipients
            elif not delivery_config or (CONF_TARGET not in delivery_config and CONF_ENTITIES not in delivery_config):
                recipients = self.filter_recipients_by_occupancy(
                    delivery_config.get(CONF_OCCUPANCY, OCCUPANCY_ALL))
                recipients = [r for r in recipients if recipients_override is None or r.get(
                    CONF_PERSON) in recipients_override]
                _LOGGER.debug("SUPERNOTIFY %s Using recipients: %s",
                              self.method, recipients)

        # now the list of recipients determined, resolve this to target addresses or entities
        default_targets = []
        custom_targets = []
        for recipient in recipients:
            recipient_targets = []
            enabled = True
            custom_data = {}
            # reuse standard recipient attributes like email or phone
            self._safe_extend(recipient_targets,
                              self.recipient_target(recipient))
            # use entities or targets set at a method level for recipient
            if CONF_DELIVERY in recipient and delivery_config[CONF_NAME] in recipient.get(CONF_DELIVERY, {}):
                recp_meth_cust = recipient.get(
                    CONF_DELIVERY, {}).get(delivery_config[CONF_NAME], {})
                self._safe_extend(
                    recipient_targets, recp_meth_cust.get(CONF_ENTITIES, []))
                self._safe_extend(recipient_targets,
                                  recp_meth_cust.get(CONF_TARGET, []))
                custom_data = recp_meth_cust.get(CONF_DATA)
                enabled = recp_meth_cust.get(CONF_ENABLED, True)
            elif ATTR_TARGET in recipient:
                # non person recipient
                self._safe_extend(default_targets, recipient.get(ATTR_TARGET))
            if enabled:
                if custom_data:
                    custom_targets.append((recipient_targets, custom_data))
                else:
                    default_targets.extend(recipient_targets)

        bundled_targets = custom_targets + [(default_targets, None)]
        filtered_bundles = []
        for targets, custom_data in bundled_targets:
            pre_filter_count = len(targets)
            _LOGGER.debug("SUPERNOTIFY Prefiltered targets: %s", targets)
            targets = [t for t in targets if self.select_target(t)]
            if len(targets) < pre_filter_count:
                _LOGGER.debug("SUPERNOTIFY %s target list filtered by %s to %s", self.method,
                              pre_filter_count-len(targets), targets)
            if not targets:
                _LOGGER.warning(
                    "SUPERNOTIFY %s No targets resolved", self.method)
            else:
                filtered_bundles.append((targets, custom_data))
        if not filtered_bundles:
            # not all delivery methods require explicit targets, or can default them internally
            filtered_bundles = [([], None)]
        return filtered_bundles

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
