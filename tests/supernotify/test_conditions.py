from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.helpers import (
    condition,
    config_validation as cv,
)

async def test_not_condition_with_template(hass: HomeAssistant) -> None:
    """Test the 'and' condition."""
    await async_setup_component(
        hass,
        "input_select",
        {
            "input_select": {
                "priority": {"options": ["critical", "high", "medium", "low"], "initial": "medium"},
            }
        },
    )
    config = {
        "condition": "and",
        "conditions": [
            {
                "condition": "state",
                "entity_id": "alarm_control_panel.home_alarm_control",
                "state": ["armed_home", "armed_away"]},
            {
                "condition": "state",
                "entity_id": "input_select.priority",
                "state": "critical",
            },
        ],
    }
    config = cv.CONDITION_SCHEMA(config)
    config = await condition.async_validate_condition_config(hass, config)
    test = await condition.async_from_config(hass, config)

    await hass.services.async_call(
        "input_select",
        "select_option",
        {
            "entity_id": "input_select.priority",
            "option": "critical",
        },
        blocking=True,
    )
    hass.states.async_set("alarm_control_panel.home_alarm_control", "disarmed")
    assert not test(hass)

    hass.states.async_set(
        "alarm_control_panel.home_alarm_control", "armed_home")
    assert test(hass)

    await hass.services.async_call(
        "input_select",
        "select_option",
        {
            "entity_id": "input_select.priority",
            "option": "low",
        },
        blocking=True,
    )
    assert not test(hass)