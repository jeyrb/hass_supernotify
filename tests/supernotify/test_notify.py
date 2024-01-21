from unittest.mock import Mock
from .hass_setup_lib import register_mobile_app
from homeassistant.const import (
    CONF_CONDITION,
    CONF_CONDITIONS,
    CONF_ENTITY_ID,
    CONF_SERVICE,
    CONF_STATE,
)
from pytest_unordered import unordered
from .doubles_lib import DummyDeliveryMethod
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from custom_components.supernotify import (
    CONF_DATA,
    CONF_DELIVERY,
    CONF_PRIORITY,
    CONF_SELECTION,
    CONF_TARGET,
    CONF_METHOD,
    CONF_PHONE_NUMBER,
    DELIVERY_SELECTION_EXPLICIT,
    METHOD_ALEXA,
    METHOD_CHIME,
    METHOD_EMAIL,
    METHOD_GENERIC,
    METHOD_PERSISTENT,
    METHOD_SMS,
    SCENARIO_DEFAULT,
    SELECTION_BY_SCENARIO,
    SELECTION_FALLBACK,
)
from custom_components.supernotify.notify import SuperNotificationService

DELIVERY = {
    "email": {CONF_METHOD: METHOD_EMAIL, CONF_SERVICE: "notify.smtp"},
    "text": {CONF_METHOD: METHOD_SMS, CONF_SERVICE: "notify.sms"},
    "chime": {CONF_METHOD: METHOD_CHIME, "entities": ["switch.bell_1", "script.siren_2"]},
    "alexa": {CONF_METHOD: METHOD_ALEXA, CONF_SERVICE: "notify.alexa"},
    "chat": {CONF_METHOD: METHOD_GENERIC, CONF_SERVICE: "notify.my_chat_server"},
    "persistent": {CONF_METHOD: METHOD_PERSISTENT, CONF_SELECTION: SELECTION_BY_SCENARIO},
    "dummy": {CONF_METHOD: "dummy"}
}
SCENARIOS = {
    SCENARIO_DEFAULT:  {CONF_DELIVERY: {"alexa": {}, "chime": {}, "text": {}, "email": {}, "chat": {}}},
    "scenario1": {CONF_DELIVERY: {"persistent": {}}},
    "scenario2": {CONF_DELIVERY: {"persistent": {}}}
}

RECIPIENTS = [
    {"person": "person.new_home_owner",
        "email": "me@tester.net",
        CONF_PHONE_NUMBER: "+447989408889",
        "mobile_devices": [
            "mobile_app.new_iphone"
        ],
        CONF_DELIVERY: {
            "dummy": {CONF_DATA: {"emoji_id": 912393},
                     CONF_TARGET: ["xyz123"]
                     }
        }
     },
    {
        "person": "person.bidey_in",
        CONF_PHONE_NUMBER: "+4489393013834",
        CONF_DELIVERY: {
            "dummy": {
                CONF_TARGET: ["abc789"]
            }
        }
    }
]


async def test_send_message_with_scenario_mismatch() -> None:
    hass = Mock()
    hass.states = Mock()
    uut = SuperNotificationService(
        hass, deliveries=DELIVERY, scenarios=SCENARIOS, recipients=RECIPIENTS)
    await uut.initialize()
    await uut.async_send_message(title="test_title", message="testing 123",
                                 delivery_selection=DELIVERY_SELECTION_EXPLICIT,
                                 delivery={
                                     "pigeon": {},
                                     "persistent": {}
                                 })
    hass.services.async_call.assert_not_called()
    hass.reset_mock()
    await uut.async_send_message(title="test_title", message="testing 123",
                                 delivery_selection=DELIVERY_SELECTION_EXPLICIT,
                                 delivery={
                                     "pigeon": {},
                                     "persistent": {}
                                 },
                                 scenarios=["scenario1"])
    hass.services.async_call.assert_called_with("notify", "persistent_notification",
                                                service_data={"title": "test_title", "message": "testing 123",
                                                              "notification_id": None})


async def test_recipient_delivery_data_override() -> None:
    hass = Mock()
    hass.states = Mock()

    uut = SuperNotificationService(
        hass, deliveries=DELIVERY, recipients=RECIPIENTS)
    await uut.initialize()
    dummy = DummyDeliveryMethod(hass, uut.context)
    await uut.register_delivery_method(dummy)
    await uut.async_send_message(title="test_title", message="testing 123",
                                 delivery_selection=DELIVERY_SELECTION_EXPLICIT,
                                 delivery={
                                     "pigeon": {},
                                     "dummy": {}
                                 })
    assert dummy.test_calls == unordered([
        ['testing 123', 'test_title', ['dummy.bidey_in', 'abc789'], 'medium', {}, None, {'method': 'dummy', 'name': 'dummy'}],
        ['testing 123', 'test_title', ['dummy.new_home_owner', 'xyz123'], 'medium', {}, {'emoji_id': 912393}, {'method': 'dummy', 'name': 'dummy'}]
         ])


async def test_null_delivery() -> None:
    hass = Mock()
    hass.states = Mock()
    uut = SuperNotificationService(hass)
    await uut.initialize()
    await uut.async_send_message("just a test")
    hass.services.async_call.assert_not_called()


async def test_fallback_delivery() -> None:
    hass = Mock()
    hass.states = Mock()
    uut = SuperNotificationService(hass, deliveries={"email": {CONF_METHOD: METHOD_EMAIL,
                                                               CONF_SELECTION: SELECTION_FALLBACK,
                                                               CONF_SERVICE: "notify.smtp"},
                                                     "push": {CONF_METHOD: METHOD_GENERIC,
                                                              CONF_SERVICE: "notify.push",
                                                              CONF_PRIORITY: "critical"}})
    await uut.initialize()
    await uut.async_send_message("just a test")
    hass.services.async_call.assert_not_called()


async def test_autoresolve_mobile_devices_for_no_devices(hass: HomeAssistant) -> None:
    uut = SuperNotificationService(hass)
    await uut.initialize()
    assert uut.mobile_devices_for_person("person.test_user") == []


async def test_autoresolve_mobile_devices_for_devices(hass: HomeAssistant,
                                                      device_registry: dr.DeviceRegistry,
                                                      entity_registry: er.EntityRegistry,) -> None:
    uut = SuperNotificationService(hass)
    await uut.initialize()
    hass.states.async_set("person.test_user", "home", attributes={
                          "device_trackers": ["device_tracker.mobile_app_phone_bob", "dev002"]})
    register_mobile_app(hass, device_registry,
                        entity_registry,
                        device_name="phone_bob",
                        title="Bobs Phone")
    assert uut.mobile_devices_for_person("person.test_user") == [{'device_tracker': 'device_tracker.mobile_app_phone_bob',
                                                                  'manufacturer': "xUnit",
                                                                  'model': "PyTest001",
                                                                  'notify_service': 'mobile_app_bobs_phone'}]


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
                                   CONF_ENTITY_ID: "supernotify.delivery_priority",
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

    uut = SuperNotificationService(hass, deliveries=delivery,
                                   recipients=RECIPIENTS)
    await uut.initialize()
    hass.states.async_set(
        "alarm_control_panel.home_alarm_control", "disarmed")
    hass.states.async_set(
        "supernotify.delivery_priority", "medium")

    await uut.async_send_message(title="test_title", message="testing 123")
    await hass.async_block_till_done()
    assert calls_service_data == []
    hass.states.async_set(
        "alarm_control_panel.home_alarm_control", "armed_away")

    await uut.async_send_message(title="test_title", message="testing 123",
                                 priority="high",
                                 delivery={
                                     "testablity": {
                                         CONF_DATA: {
                                             "test": "unit"
                                         }
                                     }
                                 },
                                 )
    await hass.async_block_till_done()
    assert calls_service_data == [
        {"test": "unit"}]
