from homeassistant.const import CONF_CONDITION
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
    uut = Scenario(
        "testing",
        {
            CONF_CONDITION: {
                "condition": "and",
                "conditions": [
                    {
                        "condition": "state",
                        "entity_id": "alarm_control_panel.home_alarm_control",
                        "state": ["armed_home", "armed_away"],
                    },
                    {
                        "condition": "state",
                        "entity_id": "supernotifier.delivery_priority",
                        "state": "critical",
                    },
                ],
            }
        },
        hass,
    )
    assert not uut.default
    assert await uut.validate()
    assert not await uut.evaluate()

    hass.states.async_set("supernotifier.delivery_priority", "critical")
    hass.states.async_set("alarm_control_panel.home_alarm_control", "armed_home")

    assert await uut.evaluate()


async def test_select_scenarios(hass: HomeAssistant) -> None:
    context = SupernotificationConfiguration(
        hass,
        scenarios={
            "select_only": {},
            "cold_day": {
                "alias": "Its a cold day",
                "condition": {
                    "condition": "template",
                    "value_template": """
                            {% set n = states('sensor.outside_temperature') | float %}
                            {{ n <= 10 }}""",
                },
            },
            "hot_day": {
                "alias": "Its a very hot day",
                "condition": {
                    "condition": "template",
                    "value_template": """
                                    {% set n = states('sensor.outside_temperature') | float %}
                                    {{ 30 <= n }}""",
                },
            },
        },
    )
    await context.initialize()
    uut = Notification(context)
    hass.states.async_set("sensor.outside_temperature", "42")
    enabled = await uut.select_scenarios()
    assert enabled == ["hot_day"]

    hass.states.async_set("sensor.outside_temperature", "5")
    enabled = await uut.select_scenarios()
    assert enabled == ["cold_day"]

    hass.states.async_set("sensor.outside_temperature", "15")
    enabled = await uut.select_scenarios()
    assert enabled == []


async def test_attributes(hass: HomeAssistant) -> None:
    uut = Scenario(
        "testing",
        {
            "delivery_selection": "implicit",
            "media": {},
            "camera_entity_id": "camera.doorbell",
            "delivery": {"doorbell_chime_alexa": {"data": {"amazon_magic_id": "a77464"}}, "email": {}},
            "condition": {
                "condition": "and",
                "conditions": [
                    {
                        "condition": "not",
                        "conditions": [
                            {"condition": "state", "entity_id": "alarm_control_panel.home_alarm_control", "state": "disarmed"}
                        ],
                    },
                    {"condition": "time", "after": "21:30:00", "before": "06:30:00"},
                ],
            },
        },
        hass,
    )

    attrs = uut.attributes()
    assert attrs["delivery_selection"] == "implicit"
    assert attrs["delivery"]["doorbell_chime_alexa"]["data"]["amazon_magic_id"] == "a77464"  # type: ignore


async def test_secondary_scenario(hass: HomeAssistant) -> None:
    uut = Scenario(
        "testing",
        {
            CONF_CONDITION: {
                "condition": "state",
                "entity_id": "supernotifier.delivery_scenarios",
                "state": ["scenario-attention", "scenario-possible-danger"],
            }
        },
        hass,
    )
    assert not uut.default
    assert await uut.validate()
    assert not await uut.evaluate()

    hass.states.async_set("supernotifier.delivery_scenarios", "scenario-possible-danger")

    assert await uut.evaluate()
