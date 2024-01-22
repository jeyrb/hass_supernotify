
from homeassistant.const import (
    CONF_CONDITION,
)
from homeassistant.core import HomeAssistant
from custom_components.supernotify.configuration import SupernotificationConfiguration
from custom_components.supernotify.notification import Notification
from custom_components.supernotify.scenario import Scenario


async def test_simple_create(hass: HomeAssistant) -> None:
    uut = Scenario("testing", {}, hass)
    assert not uut.default
    assert await uut.validate()
    assert not await uut.evaluate()


async def test_conditional_create(hass: HomeAssistant) -> None:
    uut = Scenario("testing", {
        CONF_CONDITION:  {
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
    }, hass)
    assert not uut.default
    assert await uut.validate()
    assert not await uut.evaluate()
    
    hass.states.async_set("supernotifier.delivery_priority", "critical")
    hass.states.async_set("alarm_control_panel.home_alarm_control", "armed_home")
 
    assert await uut.evaluate()

async def test_select_scenarios(hass: HomeAssistant) -> None:
    context = SupernotificationConfiguration(hass, scenarios={"select_only": {},
                                                    "cold_day": {
        "alias": "Its a cold day",
        "condition": {
            "condition": "template",
            "value_template": """
                            {% set n = states('sensor.outside_temperature') | float %}
                            {{ n <= 10 }}"""
        }
    },
        "hot_day": {
        "alias": "Its a very hot day",
        "condition": {
            "condition": "template",
            "value_template": """
                                    {% set n = states('sensor.outside_temperature') | float %}
                                    {{ 30 <= n }}"""
        }
    }
    })
    await context.initialize()
    uut = Notification(context)
    hass.states.async_set("sensor.outside_temperature", 42)
    enabled = await uut.select_scenarios()
    assert enabled == ['hot_day']

    hass.states.async_set("sensor.outside_temperature", 5)
    enabled = await uut.select_scenarios()
    assert enabled == ['cold_day']

    hass.states.async_set("sensor.outside_temperature", 15)
    enabled = await uut.select_scenarios()
    assert enabled == []