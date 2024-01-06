from abc import abstractmethod
import asyncio
from homeassistant.helpers import condition, config_validation as cv
import logging

from homeassistant.components.notify import ATTR_TARGET
from homeassistant.const import CONF_CONDITION, CONF_DEFAULT, CONF_METHOD, CONF_SERVICE
from homeassistant.core import HomeAssistant

from . import ATTR_SCENARIOS, CONF_OCCUPANCY, CONF_PERSON, CONF_PRIORITY, OCCUPANCY_ALL, OCCUPANCY_ALL_IN, OCCUPANCY_ALL_OUT, OCCUPANCY_ANY_IN, OCCUPANCY_ANY_OUT, OCCUPANCY_NONE, OCCUPANCY_ONLY_IN, OCCUPANCY_ONLY_OUT

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
                        self.invalid_deliveries[d]=dc

    def deliver(self, message=None, title=None, config=None,
                scenarios=None,
                target=None, 
                priority=None, 
                data=None):
        config = config or self.default_delivery or {}
        data = data or {}
        delivery_priorities=config.get(CONF_PRIORITY) or ()
        if priority and delivery_priorities and priority not in delivery_priorities:
            _LOGGER.debug(
                "SUPERNOTIFY Skipping delivery for %s based on priority (%s)", self.method, priority)
            return
        if not self.evaluate_delivery_conditions(config):
            _LOGGER.debug(
                    "SUPERNOTIFY Skipping delivery for %s based on conditions", self.method)
            return
        delivery_scenarios = config.get(ATTR_SCENARIOS)
        if delivery_scenarios and not any(s in delivery_scenarios for s in scenarios):
            _LOGGER.debug(
                    "Skipping delivery without matched scenario (%s) vs (%s)", scenarios, delivery_scenarios)
            return
        self._delivery_impl(message=message,
                            title=title,
                            recipients=self.select_recipients(config, target),
                            priority=priority,
                            scenarios=scenarios,
                            data=data,
                            config=config)

    @abstractmethod
    def _delivery_impl(message=None, title=None, config=None):
        pass

    def select_recipients(self, delivery_config, target):
        recipients = []
        if target:
            for t in target:
                if t in self.context.people:
                    recipients.append(self.context.people[t])
                else:
                    recipients.append({ATTR_TARGET: t})
        elif delivery_config:
            recipients = self.filter_recipients(
                delivery_config.get(CONF_OCCUPANCY, OCCUPANCY_ALL))
        else:
            _LOGGER.debug("SUPERNOTIFY Neither target not recipients defined")

        return recipients

    def filter_recipients(self, occupancy):
        at_home = []
        away = []
        try:
            for r in self.context.recipients:
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

    def evaluate_delivery_conditions(self, delivery_config):
        if CONF_CONDITION not in delivery_config:
            return True
        else:
            try:
                conditions = cv.CONDITION_SCHEMA(
                    delivery_config.get(CONF_CONDITION))
                test = asyncio.run_coroutine_threadsafe(
                    condition.async_from_config(
                        self.hass, conditions), self.hass.loop
                ).result()
                return test(self.hass)
            except Exception as e:
                _LOGGER.error("SUPERNOTIFY Condition eval failed: %s", e)
                raise