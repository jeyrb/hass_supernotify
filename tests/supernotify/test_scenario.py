import logging

from homeassistant.const import CONF_ALIAS, CONF_CONDITION
from homeassistant.core import HomeAssistant
from pytest_unordered import unordered

from custom_components.supernotify import (
    ATTR_SCENARIOS_APPLY,
    ATTR_SCENARIOS_CONSTRAIN,
    PLATFORM_SCHEMA,
    PRIORITY_CRITICAL,
    PRIORITY_MEDIUM,
    SCENARIO_SCHEMA,
    ConditionVariables,
)
from custom_components.supernotify.configuration import Context
from custom_components.supernotify.notification import Notification
from custom_components.supernotify.scenario import Scenario

_LOGGER = logging.getLogger(__name__)


async def test_simple_create(hass: HomeAssistant) -> None:
    uut = Scenario("testing", {}, hass)
    assert await uut.validate()
    assert not uut.default
    assert await uut.validate()
    assert not await uut.evaluate()


async def test_simple_trace(hass: HomeAssistant) -> None:
    uut = Scenario("testing", {}, hass)
    assert await uut.validate()
    assert not uut.default
    assert await uut.validate()
    assert not await uut.trace()


async def test_conditional_create(hass: HomeAssistant) -> None:
    uut = Scenario(
        "testing",
        SCENARIO_SCHEMA({
            CONF_ALIAS: "test001",
            CONF_CONDITION: {
                "condition": "and",
                "conditions": [
                    {
                        "condition": "state",
                        "entity_id": "alarm_control_panel.home_alarm_control",
                        "state": ["armed_home", "armed_away"],
                    },
                    {
                        "condition": "template",
                        "value_template": "{{notification_priority in ['critical']}}",
                    },
                ],
            },
        }),
        hass,
    )
    assert await uut.validate()
    assert not uut.default
    assert await uut.validate()
    assert not await uut.evaluate(ConditionVariables([], [], [], PRIORITY_MEDIUM, {}))

    hass.states.async_set("alarm_control_panel.home_alarm_control", "armed_home")

    assert await uut.evaluate(ConditionVariables([], [], [], PRIORITY_CRITICAL, {}))


async def test_select_scenarios(hass: HomeAssistant) -> None:
    config = PLATFORM_SCHEMA({
        "platform": "supernotify",
        "scenarios": {
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
    })
    context = Context(hass, scenarios=config["scenarios"])
    hass.states.async_set("sensor.outside_temperature", "15")
    await context.initialize()
    assert len(context.scenarios) == 3
    uut = Notification(context)
    await uut.initialize()
    hass.states.async_set("sensor.outside_temperature", "42")
    enabled = await uut.select_scenarios()
    assert enabled == ["hot_day"]

    hass.states.async_set("sensor.outside_temperature", "5")
    enabled = await uut.select_scenarios()
    assert enabled == ["cold_day"]

    hass.states.async_set("sensor.outside_temperature", "15")
    enabled = await uut.select_scenarios()
    assert enabled == []


async def test_scenario_constraint(mock_context: Context) -> None:
    mock_context.delivery_by_scenario = {"DEFAULT": ["plain_email", "mobile"], "Mostly": ["siren"], "Alarm": ["chime"]}
    mock_context.deliveries = {"plain_email": {}, "mobile": {}, "chime": {}, "siren": {}}
    mock_context.scenarios = {
        "Mostly": Scenario(
            "Mostly",
            SCENARIO_SCHEMA({
                CONF_ALIAS: "test001",
                CONF_CONDITION: {
                    "condition": "and",
                    "conditions": [
                        {
                            "condition": "template",
                            "value_template": "{{notification_priority not in ['critical']}}",
                        },
                    ],
                },
            }),
            mock_context.hass,  # type: ignore
        )
    }
    uut = Notification(mock_context, "testing 123", action_data={ATTR_SCENARIOS_APPLY: ["Alarm"]})
    await uut.initialize()
    assert uut.selected_delivery_names == unordered("plain_email", "mobile", "chime", "siren")
    uut = Notification(
        mock_context, "testing 123", action_data={ATTR_SCENARIOS_CONSTRAIN: ["NULL"], ATTR_SCENARIOS_APPLY: ["Alarm"]}
    )
    await uut.initialize()
    assert uut.selected_delivery_names == unordered("plain_email", "mobile", "chime")


async def test_attributes(hass: HomeAssistant) -> None:
    uut = Scenario(
        "testing",
        SCENARIO_SCHEMA({
            "delivery_selection": "implicit",
            "media": {"camera_entity_id": "camera.doorbell"},
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
        }),
        hass,
    )
    assert await uut.validate()
    attrs = uut.attributes()
    assert attrs["delivery_selection"] == "implicit"

    assert attrs["delivery"]["doorbell_chime_alexa"]["data"]["amazon_magic_id"] == "a77464"  # type: ignore


async def test_secondary_scenario(hass: HomeAssistant) -> None:
    uut = Scenario(
        "testing",
        SCENARIO_SCHEMA({
            CONF_CONDITION: {"condition": "template", "value_template": '{{"scenario-possible-danger" in applied_scenarios}}'}
        }),
        hass,
    )
    assert await uut.validate()
    cvars = ConditionVariables(["scenario-no-danger", "sunny"], [], [], PRIORITY_MEDIUM, {})
    assert not uut.default
    assert await uut.validate()
    assert not await uut.evaluate(cvars)
    cvars.applied_scenarios.append("scenario-possible-danger")
    assert await uut.evaluate(cvars)


async def test_trace(hass: HomeAssistant) -> None:
    uut = Scenario(
        "testing",
        SCENARIO_SCHEMA({
            CONF_CONDITION: {"condition": "template", "value_template": "{{'scenario-alert' in applied_scenarios}}"}
        }),
        hass,
    )
    assert await uut.validate()
    assert not uut.default
    assert await uut.trace(ConditionVariables(["scenario-alert"], [], [], PRIORITY_MEDIUM, {"AT_HOME": [{"name": "bob"}]}))
    assert uut.last_trace is not None
    _LOGGER.info("trace: %s", uut.last_trace.as_dict())
