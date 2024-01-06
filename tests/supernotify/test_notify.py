from unittest.mock import Mock
from homeassistant.components.supernotify import CONF_PHONE_NUMBER, ATTR_DELIVERY, ATTR_SCENARIOS, CONF_OVERRIDE_BASE, CONF_OVERRIDE_REPLACE, CONF_METHOD, CONF_SCENARIOS, METHOD_ALEXA, METHOD_EMAIL, METHOD_CHIME, METHOD_PERSISTENT, METHOD_SMS
from homeassistant.const import CONF_SERVICE, CONF_TARGET

from homeassistant.components.supernotify.notify import SuperNotificationService

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
        "mobile": {
            CONF_PHONE_NUMBER: "+447989408889",
            "apple_devices": [
                "mobile_app.new_iphone"
            ]
        }
     },
    {
        "person": "person.bidey_in",
        "mobile": {
            CONF_PHONE_NUMBER: "+4489393013834"
        }
    }
]


async def test_send_message_with_scenario_mismatch() -> None:
    hass = Mock()
    hass.states = Mock()
    uut = SuperNotificationService(
        hass, deliveries=DELIVERY)
    uut.send_message(title="test_title", message="testing 123",
                     data={ATTR_DELIVERY: ["pigeon", "persistent"]},
                     recipients=RECIPIENTS)
    hass.services.call.assert_not_called()
    uut.send_message(title="test_title", message="testing 123",
                     data={ATTR_DELIVERY: [
                         "pigeon", "persistent"], ATTR_SCENARIOS: ["scenario1"]},
                     recipients=RECIPIENTS)
    hass.services.call.assert_called_with("notify", "persistent_notification",
                                          service_data={"title": "test_title", "message": "testing 123",
                                                        "notification_id": None})
