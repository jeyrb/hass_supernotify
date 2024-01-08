from abc import abstractmethod
import asyncio
import logging

from homeassistant.components.notify import ATTR_TARGET
from homeassistant.const import (
    CONF_CONDITION,
    CONF_DEFAULT,
    CONF_ENTITIES,
    CONF_METHOD,
    CONF_SERVICE,
    CONF_TARGET,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import condition, config_validation as cv

from . import (
    ATTR_SCENARIOS,
    CONF_DELIVERY,
    CONF_OCCUPANCY,
    CONF_PERSON,
    CONF_PRIORITY,
    OCCUPANCY_ALL,
    OCCUPANCY_ALL_IN,
    OCCUPANCY_ALL_OUT,
    OCCUPANCY_ANY_IN,
    OCCUPANCY_ANY_OUT,
    OCCUPANCY_NONE,
    OCCUPANCY_ONLY_IN,
    OCCUPANCY_ONLY_OUT,
)

_LOGGER = logging.getLogger(__name__)


class SuperNotificationContext:
    def __init__(self, hass_url: str = None, hass_name: str = None,
                 links=(), recipients=(),
                 mobile_actions=(),
                 templates=()):
        self.hass_url = hass_url
        self.hass_name = hass_name
        self.links = links
        self.recipients = recipients
        self.mobile_actions = mobile_actions
        self.templates = templates
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
        if deliveries:
            for d, dc in deliveries.items():
                if dc and dc.get(CONF_METHOD) == method:
                    if not self.service_required or dc.get(CONF_SERVICE):
                        self.valid_deliveries[d] = dc
                        if dc.get(CONF_DEFAULT):
                            self.default_delivery = dc
                    else:
                        self.invalid_deliveries[d] = dc

    async def deliver(self,
                message=None,
                title=None,
                config=None,
                scenarios=None,
                target=None,
                priority=None,
                data=None):
        config = config or self.default_delivery or {}
        data = data or {}
        delivery_priorities = config.get(CONF_PRIORITY) or ()
        if priority and delivery_priorities and priority not in delivery_priorities:
            _LOGGER.debug(
                "SUPERNOTIFY Skipping delivery for %s based on priority (%s)", self.method, priority)
            return
        if not await self.evaluate_delivery_conditions(config):
            _LOGGER.debug(
                "SUPERNOTIFY Skipping delivery for %s based on conditions", self.method)
            return
        targets = self.build_targets(config, target)
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

    def build_targets(self, delivery_config, target):
        recipients = []
        if target:
            # first priority is explicit target set on notify call, which overrides everything else
            for t in target:
                if t in self.context.people:
                    recipients.append(self.context.people[t])
                else:
                    recipients.append({ATTR_TARGET: t})
        elif delivery_config and CONF_ENTITIES in delivery_config:
            # second priority is explicit entities on delivery
            recipients = [{ATTR_TARGET: e}
                          for e in delivery_config.get(CONF_ENTITIES)]
        elif delivery_config and CONF_TARGET in delivery_config:
            # thirdt priority is explicit target on delivery
            recipients = [{ATTR_TARGET: e}
                          for e in delivery_config.get(CONF_TARGET)]
        elif delivery_config:
            # If target not specified on service call or delivery, then use the list of recipients
            recipients = self.filter_recipients(
                delivery_config.get(CONF_OCCUPANCY, OCCUPANCY_ALL))
        else:
            _LOGGER.debug("SUPERNOTIFY Neither target not recipients defined")
        # now the list of recipients determined, resolve this to target addresses or entities
        targets = []
        for recipient in recipients:
            # reuse standard recipient attributes like email or phone
            self._safe_extend(targets, self.recipient_target(recipient))
            # use entities or targets set at a method level for recipient
            if CONF_DELIVERY in recipient and self.name in recipient.get(CONF_DELIVERY, {}):
                recp_meth_cust = recipient.get(
                    CONF_DELIVERY, {}).get(self.name, {})
                self._safe_extend(
                    targets, recp_meth_cust.get(CONF_ENTITIES, []))
                self._safe_extend(targets, recp_meth_cust.get(CONF_TARGET, []))
            elif ATTR_TARGET in recipient:
                # non person recipient
                self._safe_extend(targets, recipient.get(ATTR_TARGET))

        targets = [t for t in targets if self.select_target(t)]
        return targets

    def _safe_extend(self, target, extension):
        if isinstance(extension, (list, tuple)):
            target.extend(extension)
        elif extension:
            target.append(extension)
        return target

    def filter_recipients(self, occupancy):
        at_home = []
        away = []
        for r in self.context.recipients:
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
        elif occupancy == OCCUPANCY_ALL:
            return self.context.recipients
        elif occupancy == OCCUPANCY_NONE:
            return []
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
