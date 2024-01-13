from unittest.mock import Mock

from homeassistant.const import (
    CONF_CONDITION,
    CONF_CONDITIONS,
    CONF_ENTITY_ID,
    CONF_SERVICE,
    CONF_STATE,
)
from homeassistant.core import HomeAssistant, callback

from custom_components.supernotify import (
    ATTR_DELIVERY,
    ATTR_DELIVERY_SELECTION,
    ATTR_SCENARIOS,
    CONF_DATA,
    CONF_METHOD,
    CONF_PHONE_NUMBER,
    CONF_SCENARIOS,
    DELIVERY_SELECTION_EXPLICIT,
    METHOD_ALEXA,
    METHOD_CHIME,
    METHOD_EMAIL,
    METHOD_GENERIC,
    METHOD_PERSISTENT,
    METHOD_SMS,
)
from custom_components.supernotify.notify import SuperNotificationService

DELIVERY = {
    "email": {CONF_METHOD: METHOD_EMAIL, CONF_SERVICE: "notify.smtp"},
    "text": {CONF_METHOD: METHOD_SMS, CONF_SERVICE: "notify.sms"},
    "chime": {CONF_METHOD: METHOD_CHIME, "entities": ["switch.bell_1", "script.siren_2"]},
    "alexa": {CONF_METHOD: METHOD_ALEXA, CONF_SERVICE: "notify.alexa"},
    "persistent": {CONF_METHOD: METHOD_PERSISTENT, CONF_SCENARIOS: ["scenario1", "scenario2"]}
}

RECIPIENTS = [
    {"person": "person.new_home_owner",
        "email": "me@tester.net",
        CONF_PHONE_NUMBER: "+447989408889",
        "mobile_devices": [
            "mobile_app.new_iphone"
        ]
     },
    {
        "person": "person.bidey_in",
        CONF_PHONE_NUMBER: "+4489393013834"
    }
]


async def test_send_message_with_scenario_mismatch() -> None:
    hass = Mock()
    hass.states = Mock()
    uut = SuperNotificationService(
        hass, deliveries=DELIVERY)
    await uut.async_send_message(title="test_title", message="testing 123",
                                 data={
                                     ATTR_DELIVERY_SELECTION: DELIVERY_SELECTION_EXPLICIT,
                                     ATTR_DELIVERY: {
                                         "pigeon": {},
                                         "persistent": {}}
                                 },
                                 recipients=RECIPIENTS)
    hass.services.async_call.assert_not_called()
    hass.reset_mock()
    await uut.async_send_message(title="test_title", message="testing 123",
                                 data={
                                     ATTR_DELIVERY_SELECTION: DELIVERY_SELECTION_EXPLICIT,
                                     ATTR_DELIVERY: {
                                        "pigeon": {}, 
                                        "persistent": {}
                                     },
                                     ATTR_SCENARIOS: ["scenario1"]},
                                 recipients=RECIPIENTS)
    hass.services.async_call.assert_called_with("notify", "persistent_notification",
                                                service_data={"title": "test_title", "message": "testing 123",
                                                              "notification_id": None})


async def test_null_delivery() -> None:
    hass = Mock()
    hass.states = Mock()
    uut = SuperNotificationService(hass)
    await uut.async_send_message("just a test")
    hass.services.async_call.assert_not_called()


async def test_select_scenarios(hass: HomeAssistant) -> None:
    uut = SuperNotificationService(hass, scenarios={"select_only": {},
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

    hass.states.async_set("sensor.outside_temperature", 42)
    enabled = await uut.select_scenarios()
    assert enabled == ['hot_day']

    hass.states.async_set("sensor.outside_temperature", 5)
    enabled = await uut.select_scenarios()
    assert enabled == ['cold_day']

    hass.states.async_set("sensor.outside_temperature", 15)
    enabled = await uut.select_scenarios()
    assert enabled == []


async def test_autoresolve_mobile_devices_for_no_devices(hass: HomeAssistant) -> None:
    uut = SuperNotificationService(hass)
    assert uut.mobile_devices_for_person("person.test_user") == []


async def test_send_message_with_condition(hass: HomeAssistant) -> None:
    delivery = {
        "testablity": {CONF_METHOD: METHOD_GENERIC,
                       CONF_SERVICE: "testing.mock_notification",
                       CONF_CONDITION: {
                           CONF_CONDITION: "or",
                           CONF_CONDITIONS: [
                               {
                                   CONF_CONDITION: "state",
                                   CONF_ENTITY_ID: "alarm_control_panel.home_alarm_control",
                                   CONF_STATE: ["armed_away", "armed_night"]
                               },
                               {
                                   CONF_CONDITION: "state",
                                   CONF_ENTITY_ID: "input_select.supernotify_priority",
                                   CONF_STATE: ["critical", "high"]
                               }
                           ]
                       }
                       }
    }
    calls_service_data = []

    @callback
    def mock_service_log(call):
        calls_service_data.append(call.data)

    hass.services.async_register(
        "testing",
        "mock_notification",
        mock_service_log,
    )

    uut = SuperNotificationService(hass, deliveries=delivery)
    hass.states.async_set(
        "alarm_control_panel.home_alarm_control", "disarmed")
    hass.states.async_set(
        "input_select.supernotify_priority", "medium")

    await uut.async_send_message(title="test_title", message="testing 123",
                                 recipients=RECIPIENTS)
    await hass.async_block_till_done()
    assert calls_service_data == []
    hass.states.async_set(
        "alarm_control_panel.home_alarm_control", "armed_away")

    await uut.async_send_message(title="test_title", message="testing 123",
                                 priority="high", 
                                 data={
                                    ATTR_DELIVERY: {
                                         "testablity": {
                                            CONF_DATA: {
                                                "test": "unit"
                                            }
                                         }
                                    },
                                 },
                                 recipients=RECIPIENTS)
    await hass.async_block_till_done()
    assert calls_service_data == [
        {"test": "unit"}]
