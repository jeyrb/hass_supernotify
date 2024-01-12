from http import HTTPStatus
from unittest.mock import Mock
from custom_components.supernotify import CONF_PHONE_NUMBER, ATTR_DELIVERY, ATTR_SCENARIOS, CONF_METHOD, CONF_SCENARIOS, METHOD_ALEXA, METHOD_EMAIL, METHOD_CHIME, METHOD_PERSISTENT, METHOD_SMS
from homeassistant.const import CONF_SERVICE
from homeassistant.core import HomeAssistant
from custom_components.supernotify.notify import SuperNotificationService
from homeassistant.setup import async_setup_component
from homeassistant.config_entries import ConfigEntry

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
                                 data={ATTR_DELIVERY: [
                                     "pigeon", "persistent"]},
                                 recipients=RECIPIENTS)
    hass.services.async_call.assert_not_called()
    hass.reset_mock()
    await uut.async_send_message(title="test_title", message="testing 123",
                                 data={ATTR_DELIVERY: [
                                     "pigeon", "persistent"], ATTR_SCENARIOS: ["scenario1"]},
                                 recipients=RECIPIENTS)
    hass.services.async_call.assert_called_with("notify", "persistent_notification",
                                          service_data={"title": "test_title", "message": "testing 123",
                                                        "notification_id": None})


async def test_null_delivery(hass: HomeAssistant) -> None:
    uut = SuperNotificationService(hass)
    deliveries, errors = await uut.async_send_message("just a test")
    assert errors == 0


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
