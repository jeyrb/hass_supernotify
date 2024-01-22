import logging
import voluptuous as vol
from homeassistant.components.notify import (
    ATTR_DATA,
)
from homeassistant.const import (
    CONF_ENABLED,
)

from . import (
    ATTR_DELIVERY,
    ATTR_DELIVERY_SELECTION,
    ATTR_PRIORITY,
    ATTR_RECIPIENTS,
    ATTR_SCENARIOS,
    CONF_DATA,
    CONF_SELECTION,
    DELIVERY_SELECTION_EXPLICIT,
    DELIVERY_SELECTION_FIXED,
    DELIVERY_SELECTION_IMPLICIT,
    PRIORITY_MEDIUM,
    SCENARIO_DEFAULT,
    SELECTION_BY_SCENARIO,
    SERVICE_DATA_SCHEMA,
)
from .configuration import SupernotificationConfiguration, ensure_list, ensure_dict

_LOGGER = logging.getLogger(__name__)


class Notification:
    def __init__(self,
                 context: SupernotificationConfiguration,
                 message: str = None,
                 title: str = None,
                 target: list = None,
                 service_data: dict = None) -> None:

        self.message = message
        self.context = context
        service_data = service_data or {}
        self.target = ensure_list(target)
        self.title = title

        try:
            SERVICE_DATA_SCHEMA(service_data)
        except vol.Invalid as e:
            _LOGGER.warning("SUPERNOTIFY invalid service data %s: %s", service_data, e)
            raise

        self.priority = service_data.get(ATTR_PRIORITY, PRIORITY_MEDIUM)
        self.requested_scenarios = ensure_list(
            service_data.get(ATTR_SCENARIOS))
        self.delivery_selection = service_data.get(ATTR_DELIVERY_SELECTION)
        self.delivery_overrides = ensure_dict(service_data.get(ATTR_DELIVERY))
        self.recipients_override = service_data.get(ATTR_RECIPIENTS)
        self.common_data = service_data.get(ATTR_DATA) or {}

        self.selected_delivery_names = []
        self.enabled_scenarios = []

    async def intialize(self):

        if self.delivery_selection is None:
            if self.delivery_overrides or self.requested_scenarios:
                self.delivery_selection = DELIVERY_SELECTION_EXPLICIT
            else:
                self.delivery_selection = DELIVERY_SELECTION_IMPLICIT

        self.enabled_scenarios = self.requested_scenarios or []
        self.enabled_scenarios.extend(await self.select_scenarios())
        scenario_enable_deliveries = []
        default_enable_deliveries = []
        override_enable_deliveries = []
        override_disable_deliveries = []
        scenario_disable_deliveries = []

        if self.delivery_selection != DELIVERY_SELECTION_FIXED:
            for scenario in self.enabled_scenarios:
                scenario_enable_deliveries.extend(
                    self.context.delivery_by_scenario.get(scenario, ()))
            if self.delivery_selection == DELIVERY_SELECTION_IMPLICIT:
                default_enable_deliveries = self.context.delivery_by_scenario.get(
                    SCENARIO_DEFAULT, [])

        for delivery, delivery_override in self.delivery_overrides.items():
            if (delivery_override is None or delivery_override.get(CONF_ENABLED, True)) and delivery in self.context.deliveries:
                override_enable_deliveries.append(delivery)
            elif delivery_override is not None and not delivery_override.get(CONF_ENABLED, True):
                override_disable_deliveries.append(delivery)

        if self.delivery_selection != DELIVERY_SELECTION_FIXED:
            scenario_disable_deliveries = [d for d, dc in self.context.deliveries.items()
                                           if dc.get(CONF_SELECTION) == SELECTION_BY_SCENARIO
                                           and d not in scenario_enable_deliveries]
        all_enabled = list(set(scenario_enable_deliveries +
                           default_enable_deliveries + override_enable_deliveries))
        all_disabled = scenario_disable_deliveries + override_disable_deliveries
        self.selected_delivery_names = [
            d for d in all_enabled if d not in all_disabled]

    def delivery_data(self, delivery_name):
        return self.delivery_overrides.get(delivery_name, {}).get(CONF_DATA) if delivery_name else {}

    def delivery_scenarios(self, delivery_name):
        return {k: self.context.scenarios.get(k, {}) for k in self.enabled_scenarios if delivery_name in self.context.delivery_by_scenario.get(k, [])}

    async def select_scenarios(self):
        scenarios = []
        for scenario in self.context.scenarios.values():
            if await scenario.evaluate():
                scenarios.append(scenario.name)
        return scenarios
