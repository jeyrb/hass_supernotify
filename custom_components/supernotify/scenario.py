import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
from typing import Any

from homeassistant.components.trace import DATA_TRACE, async_setup, async_store_trace
from homeassistant.components.trace.models import ActionTrace
from homeassistant.const import CONF_ALIAS, CONF_CONDITION
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import condition
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.trace import trace_get, trace_path
from homeassistant.helpers.typing import ConfigType

from . import ATTR_DEFAULT, CONF_DELIVERY, CONF_DELIVERY_SELECTION, CONF_MEDIA, ConditionVariables

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
        self.last_trace: ActionTrace | None = None

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

    async def evaluate(self, condition_variables: ConditionVariables | None = None) -> bool:
        """Evaluate scenario conditions"""
        if self.condition:
            try:
                conditions = cv.CONDITION_SCHEMA(self.condition)
                test = await condition.async_from_config(self.hass, conditions)
            except Exception as e:
                _LOGGER.error("SUPERNOTIFY Scenario condition create failed: %s", e)
                return False
            try:
                if test(self.hass, asdict(condition_variables) if condition_variables else None):
                    return True
            except Exception as e:
                _LOGGER.error("SUPERNOTIFY Scenario condition eval failed: %s, vars: %s", e, condition_variables)
        return False

    async def trace(self, condition_variables: ConditionVariables | None = None, config: ConfigType | None = None) -> bool:
        """Trace scenario delivery"""
        result = None
        config = config or {}
        if DATA_TRACE not in self.hass.data:
            await async_setup(self.hass, config)
        with trace_action(self.hass, f"scenario_{self.name}", config) as scenario_trace:
            scenario_trace.set_trace(trace_get())
            self.last_trace = scenario_trace
            with trace_path(["condition", "conditions"]) as _tp:  # type: ignore
                result = await self.evaluate(condition_variables)
            _LOGGER.info(scenario_trace.as_dict())
        return result


@contextmanager
def trace_action(
    hass: HomeAssistant,
    item_id: str,
    config: dict[str, Any],
    context: Context | None = None,
    stored_traces: int = 5,
) -> Iterator[ActionTrace]:
    """Trace execution of a scenario."""
    trace = ActionTrace(item_id, config, None, context or Context())
    async_store_trace(hass, trace, stored_traces)

    try:
        yield trace
    except Exception as ex:
        if item_id:
            trace.set_error(ex)
        raise
    finally:
        if item_id:
            trace.finished()
