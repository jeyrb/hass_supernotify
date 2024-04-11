import logging

from homeassistant.const import CONF_ALIAS, CONF_CONDITION
from homeassistant.core import HomeAssistant
from homeassistant.helpers import condition
from homeassistant.helpers import config_validation as cv

from . import ATTR_DEFAULT, CONF_DELIVERY, CONF_DELIVERY_SELECTION, CONF_MEDIA

_LOGGER = logging.getLogger(__name__)


class Scenario:
    def __init__(self, name: str, scenario_definition: dict, hass: HomeAssistant):
        self.hass = hass
        self.name = name
        self.alias = scenario_definition.get(CONF_ALIAS)
        self.condition = scenario_definition.get(CONF_CONDITION)
        self.media = scenario_definition.get(CONF_MEDIA)
        self.delivery_selection = scenario_definition.get(CONF_DELIVERY_SELECTION)
        self.delivery = scenario_definition.get(CONF_DELIVERY) or {}
        self.default = self.name == ATTR_DEFAULT

    async def validate(self):
        """Validate Home Assistant conditiion definition at initiation"""
        if self.condition:
            if not await condition.async_validate_condition_config(self.hass, self.condition):
                _LOGGER.warning("SUPERNOTIFY Disabling scenario %s with failed condition %s", self.name, self.condition)
                return False
        return True

    async def evaluate(self):
        """Evaluate scenario conditions"""
        if self.condition:
            try:
                conditions = cv.CONDITION_SCHEMA(self.condition)
                test = await condition.async_from_config(self.hass, conditions)
                if test(self.hass):
                    return True
            except Exception as e:
                _LOGGER.error("SUPERNOTIFY Scenario condition eval failed: %s", e)
        return False
