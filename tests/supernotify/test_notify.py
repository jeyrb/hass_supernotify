import time
from unittest.mock import AsyncMock, Mock, patch
import os.path
import tempfile
import json
from homeassistant.const import CONF_CONDITION, CONF_CONDITIONS, CONF_ENTITY_ID, CONF_SERVICE, CONF_STATE, CONF_ENABLED

from custom_components.supernotify.notification import Envelope, Notification
from .doubles_lib import DummyDeliveryMethod
from homeassistant.core import HomeAssistant, callback
from custom_components.supernotify import (
    ATTR_DUPE_POLICY_NONE,
    ATTR_PRIORITY,
    CONF_ARCHIVE_DAYS,
    CONF_ARCHIVE_PATH,
    CONF_DATA,
    CONF_DELIVERY,
    CONF_DUPE_POLICY,
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
    "dummy": {CONF_METHOD: "dummy"},
}
SCENARIOS = {
    SCENARIO_DEFAULT: {CONF_DELIVERY: {"alexa": {}, "chime": {}, "text": {}, "email": {}, "chat": {}}},
    "scenario1": {CONF_DELIVERY: {"persistent": {}}},
    "scenario2": {CONF_DELIVERY: {"persistent": {}}},
}

RECIPIENTS = [
    {
        "person": "person.new_home_owner",
        "email": "me@tester.net",
        CONF_PHONE_NUMBER: "+447989408889",
        "mobile_devices": ["mobile_app.new_iphone"],
        CONF_DELIVERY: {"dummy": {CONF_DATA: {"emoji_id": 912393}, CONF_TARGET: ["xyz123"]}},
    },
    {"person": "person.bidey_in", CONF_PHONE_NUMBER: "+4489393013834", CONF_DELIVERY: {"dummy": {CONF_TARGET: ["abc789"]}}},
]


async def test_send_message_with_scenario_mismatch() -> None:
    hass = Mock()
    hass.states = Mock()
    hass.services.async_call = AsyncMock()
    uut = SuperNotificationService(
        hass,
        deliveries=DELIVERY,
        scenarios=SCENARIOS,
        recipients=RECIPIENTS,
        dupe_check={CONF_DUPE_POLICY: ATTR_DUPE_POLICY_NONE},
    )
    await uut.initialize()
    await uut.async_send_message(
        title="test_title",
        message="testing 123",
        data={"delivery_selection": DELIVERY_SELECTION_EXPLICIT, "delivery": {"pigeon": {}, "persistent": {}}},
    )
    hass.services.async_call.assert_not_called()
    hass.reset_mock()
    await uut.async_send_message(
        title="test_title",
        message="testing 123",
        data={
            "delivery_selection": DELIVERY_SELECTION_EXPLICIT,
            "delivery": {"pigeon": {}, "persistent": {}},
            "scenarios": ["scenario1"],
        },
    )
    hass.services.async_call.assert_called_with(
        "notify",
        "persistent_notification",
        service_data={"title": "test_title", "message": "testing 123", "notification_id": None},
    )


async def inject_dummy_delivery_method(hass: HomeAssistant, uut: SuperNotificationService) -> None:
    dummy = DummyDeliveryMethod(hass, uut.context)
    await dummy.initialize()
    await uut.context.register_delivery_methods([dummy])
    return dummy


async def test_recipient_delivery_data_override() -> None:
    hass = Mock()
    hass.states = Mock()
    hass.services.async_call = AsyncMock()
    hass.data = {}
    hass.data["device_registry"] = Mock()
    hass.data["entity_registry"] = Mock()
    uut = SuperNotificationService(hass, deliveries=DELIVERY, recipients=RECIPIENTS)
    await uut.initialize()
    dummy = await inject_dummy_delivery_method(hass, uut)
    await uut.async_send_message(
        title="test_title",
        message="testing 123",
        data={"delivery_selection": DELIVERY_SELECTION_EXPLICIT, "delivery": {"pigeon": {}, "dummy": {}}},
    )
    assert len(dummy.test_calls) == 2
    assert dummy.test_calls == [
        Envelope("dummy", uut.last_notification, targets=["dummy.new_home_owner", "xyz123"], data={"emoji_id": 912393}),
        Envelope("dummy", uut.last_notification, targets=["dummy.bidey_in", "abc789"]),
    ]


async def test_null_delivery() -> None:
    hass = Mock()
    hass.states = Mock()
    uut = SuperNotificationService(hass)
    await uut.initialize()
    await uut.async_send_message("just a test")
    hass.services.async_call.assert_not_called()

async def test_archive() -> None:
    hass = Mock()
    hass.states = Mock()
    with tempfile.TemporaryDirectory() as archive:
        uut = SuperNotificationService(hass, archive={CONF_ENABLED: True, CONF_ARCHIVE_PATH: archive})
        await uut.initialize()
        await uut.async_send_message("just a test", target="person.bob")
        obj_name = os.path.join(archive, "%s.json" % uut.last_notification.id)
        assert os.path.exists(obj_name)
        with open(obj_name, "r") as stream:
            reobj = json.load(stream)
        assert reobj["_message"] == "just a test"
        assert reobj["target"] == ["person.bob"]


async def test_cleanup_archive() -> None:
    hass = Mock()
    hass.states = Mock()
    archive = "config/archive/test"
    uut = SuperNotificationService(hass, archive={CONF_ENABLED: True, CONF_ARCHIVE_DAYS: 7, CONF_ARCHIVE_PATH: archive})
    await uut.initialize()
    old_time = Mock(return_value=Mock(st_ctime=time.time() - (8 * 24 * 60 * 60)))
    new_time = Mock(return_value=Mock(st_ctime=time.time() - (5 * 24 * 60 * 60)))
    with patch("os.scandir") as scan:
        with patch("os.remove") as rmfr:
            scan.return_value.__enter__.return_value = [
                Mock(path="abc", stat=new_time),
                Mock(path="def", stat=new_time),
                Mock(path="xyz", stat=old_time),
            ]
            uut.cleanup_archive()
            rmfr.assert_called_once_with("xyz")
    # skip cleanup for a few hours
    first_purge = uut.last_purge
    uut.cleanup_archive()
    assert first_purge == uut.last_purge


async def test_fallback_delivery() -> None:
    hass = Mock()
    uut = SuperNotificationService(
        hass,
        deliveries={
            "generic": {CONF_METHOD: METHOD_GENERIC, CONF_SELECTION: SELECTION_FALLBACK, CONF_SERVICE: "notify.dummy"},
            "push": {CONF_METHOD: METHOD_GENERIC, CONF_SERVICE: "notify.push", CONF_PRIORITY: "critical"},
        },
    )
    await uut.initialize()
    await uut.async_send_message("just a test", data={"priority": "low"})
    hass.services.async_call.assert_called_once_with(
        "notify", "dummy", service_data={"message": "just a test", "target": [], "data": {}}
    )


async def test_send_message_with_condition(hass: HomeAssistant) -> None:
    delivery = {
        "testablity": {
            CONF_METHOD: METHOD_GENERIC,
            CONF_SERVICE: "testing.mock_notification",
            CONF_CONDITION: {
                CONF_CONDITION: "or",
                CONF_CONDITIONS: [
                    {
                        CONF_CONDITION: "state",
                        CONF_ENTITY_ID: "alarm_control_panel.home_alarm_control",
                        CONF_STATE: ["armed_away", "armed_night"],
                    },
                    {
                        CONF_CONDITION: "state",
                        CONF_ENTITY_ID: "supernotify.delivery_priority",
                        CONF_STATE: ["critical", "high"],
                    },
                ],
            },
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

    uut = SuperNotificationService(hass, deliveries=delivery, recipients=RECIPIENTS)
    await uut.initialize()
    hass.states.async_set("alarm_control_panel.home_alarm_control", "disarmed")
    hass.states.async_set("supernotify.delivery_priority", "medium")

    await uut.async_send_message(title="test_title", message="testing 123")
    await hass.async_block_till_done()
    assert calls_service_data == []
    hass.states.async_set("alarm_control_panel.home_alarm_control", "armed_away")

    await uut.async_send_message(
        title="test_title",
        message="testing 123",
        data={"priority": "high", "delivery": {"testablity": {CONF_DATA: {"test": "unit"}}}},
    )
    await hass.async_block_till_done()
    assert calls_service_data == [{"test": "unit"}]


async def test_dupe_check_suppresses_same_priority_and_message() -> None:
    hass = Mock()
    context = Mock()
    uut = SuperNotificationService(hass)
    await uut.initialize()
    n1 = Notification(context, "message here", "title here")
    assert uut.dupe_check(n1) is False
    n2 = Notification(context, "message here", "title here")
    assert uut.dupe_check(n2) is True


async def test_dupe_check_allows_higher_priority_and_same_message() -> None:
    hass = Mock()
    context = Mock()
    uut = SuperNotificationService(hass)
    await uut.initialize()
    n1 = Notification(context, "message here", "title here")
    assert uut.dupe_check(n1) is False
    n2 = Notification(context, "message here", "title here", service_data={ATTR_PRIORITY: "high"})
    assert uut.dupe_check(n2) is False
