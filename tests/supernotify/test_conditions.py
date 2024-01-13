from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    condition,
    config_validation as cv,
)

''' test bed for checking conditions rather than supernotifier functionality '''


async def test_and_condition(hass: HomeAssistant) -> None:
    """Test the 'and' condition."""

    config = {
        "condition": "and",
        "conditions": [
            {
                "condition": "state",
                "entity_id": "alarm_control_panel.home_alarm_control",
                "state": ["armed_home", "armed_away"]},
            {
                "condition": "state",
                "entity_id": "supernotifier.delivery_priority",
                "state": "critical",
            },
        ],
    }
    config = cv.CONDITION_SCHEMA(config)
    config = await condition.async_validate_condition_config(hass, config)
    test = await condition.async_from_config(hass, config)

    hass.states.async_set("supernotifier.delivery_priority", "critical")
    hass.states.async_set("alarm_control_panel.home_alarm_control", "disarmed")
    assert not test(hass)

    hass.states.async_set(
        "alarm_control_panel.home_alarm_control", "armed_home")
    assert test(hass)

    hass.states.async_set("supernotifier.delivery_priority", "low")
    assert not test(hass)


async def test_template_condition(hass: HomeAssistant) -> None:
    """Test templated conditions."""

    config = {
        "condition": "template",
        "value_template": """
                        {% set n = states('sensor.bedroom_temperature') | float %}
                        {{ 15 <= n <= 20 }}"""
    }
    config = cv.CONDITION_SCHEMA(config)
    config = await condition.async_validate_condition_config(hass, config)
    test = await condition.async_from_config(hass, config)

    hass.states.async_set("sensor.bedroom_temperature", 12)
    assert not test(hass)
    hass.states.async_set("sensor.bedroom_temperature", 21)
    assert not test(hass)
    hass.states.async_set("sensor.bedroom_temperature", 18)
    assert test(hass)
