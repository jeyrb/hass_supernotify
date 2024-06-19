import logging
from typing import TYPE_CHECKING

from homeassistant.const import CONF_ALIAS, CONF_CONDITION
from homeassistant.core import HomeAssistant
from homeassistant.helpers import condition
from homeassistant.helpers import config_validation as cv

from . import ATTR_DEFAULT, CONF_DELIVERY, CONF_DELIVERY_SELECTION, CONF_MEDIA

if TYPE_CHECKING:
    from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)


class Scenario:
    def __init__(self, name: str, scenario_definition: dict, hass: HomeAssistant) -> None:
        self.hass: HomeAssistant = hass
        self.name: str = name
        self.alias: str | None = scenario_definition.get(CONF_ALIAS)
        self.condition: ConfigType | None = scenario_definition.get(CONF_CONDITION)
        self.media: dict | None = scenario_definition.get(CONF_MEDIA)
        self.delivery_selection: str | None = scenario_definition.get(CONF_DELIVERY_SELECTION)
        self.delivery: dict = scenario_definition.get(CONF_DELIVERY) or {}
        self.default: bool = self.name == ATTR_DEFAULT

    async def validate(self) -> bool:
        """Validate Home Assistant conditiion definition at initiation"""
        if self.condition:
            if not await condition.async_validate_condition_config(self.hass, self.condition):
                _LOGGER.warning("SUPERNOTIFY Disabling scenario %s with failed condition %s", self.name, self.condition)
                return False
        return True

    def attributes(self) -> dict[str, str | None | dict | bool]:
        """Return scenario attributes"""
        return {
            "name": self.name,
            "alias": self.alias,
            "media": self.media,
            "delivery_selection": self.delivery_selection,
            "delivery": self.delivery,
            "default": self.default,
            "condition": self.condition,
        }

    async def evaluate(self) -> bool:
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
