import json
import tempfile
import time
from pathlib import Path
from typing import cast
from unittest.mock import Mock, patch

import aiofiles
from homeassistant.const import CONF_CONDITION, CONF_CONDITIONS, CONF_ENABLED, CONF_ENTITY_ID, CONF_SERVICE, CONF_STATE
from homeassistant.core import HomeAssistant, ServiceCall, callback

from custom_components.supernotify import (
    ATTR_DUPE_POLICY_NONE,
    ATTR_PRIORITY,
    CONF_ARCHIVE_DAYS,
    CONF_ARCHIVE_PATH,
    CONF_DATA,
    CONF_DELIVERY,
    CONF_DUPE_POLICY,
    CONF_METHOD,
    CONF_OPTIONS,
    CONF_PHONE_NUMBER,
    CONF_PRIORITY,
    CONF_SELECTION,
    CONF_TARGET,
    CONF_TARGETS_REQUIRED,
    DELIVERY_SELECTION_EXPLICIT,
    METHOD_ALEXA,
    METHOD_CHIME,
    METHOD_EMAIL,
    METHOD_GENERIC,
    METHOD_MOBILE_PUSH,
    METHOD_PERSISTENT,
    METHOD_SMS,
    SCENARIO_DEFAULT,
    SELECTION_BY_SCENARIO,
    SELECTION_FALLBACK,
)
from custom_components.supernotify.configuration import SupernotificationConfiguration
from custom_components.supernotify.delivery_method import DeliveryMethod
from custom_components.supernotify.envelope import Envelope
from custom_components.supernotify.notification import Notification
from custom_components.supernotify.notify import SuperNotificationService
from tests.supernotify.doubles_lib import BrokenDeliveryMethod, DummyDeliveryMethod

DELIVERY: dict[str, dict] = {
    "email": {CONF_METHOD: METHOD_EMAIL, CONF_SERVICE: "notify.smtp"},
    "text": {CONF_METHOD: METHOD_SMS, CONF_SERVICE: "notify.sms"},
    "chime": {CONF_METHOD: METHOD_CHIME, "entities": ["switch.bell_1", "script.siren_2"]},
    "alexa": {CONF_METHOD: METHOD_ALEXA, CONF_SERVICE: "notify.alexa"},
    "chat": {CONF_METHOD: METHOD_GENERIC, CONF_SERVICE: "notify.my_chat_server"},
    "persistent": {CONF_METHOD: METHOD_PERSISTENT, CONF_SELECTION: SELECTION_BY_SCENARIO},
    "dummy": {CONF_METHOD: "dummy"},
}
SCENARIOS: dict[str, dict] = {
    SCENARIO_DEFAULT: {CONF_DELIVERY: {"alexa": {}, "chime": {}, "text": {}, "email": {}, "chat": {}}},
    "scenario1": {CONF_DELIVERY: {"persistent": {}}},
    "scenario2": {CONF_DELIVERY: {"persistent": {}}},
}

RECIPIENTS: list[dict] = [
    {
        "person": "person.new_home_owner",
        "email": "me@tester.net",
        CONF_PHONE_NUMBER: "+447989408889",
        "mobile_devices": [{"notify_service": "mobile_app_new_iphone"}],
        CONF_DELIVERY: {"dummy": {CONF_DATA: {"emoji_id": 912393}, CONF_TARGET: ["xyz123"]}},
    },
    {"person": "person.bidey_in", CONF_PHONE_NUMBER: "+4489393013834", CONF_DELIVERY: {"dummy": {CONF_TARGET: ["abc789"]}}},
]

METHOD_DEFAULTS: dict[str, dict] = {
    METHOD_GENERIC: {CONF_SERVICE: "notify.slackity", CONF_ENTITY_ID: ["entity.1", "entity.2"]},
    METHOD_EMAIL: {CONF_OPTIONS: {"jpeg_args": {"progressive": True}}},
    "dummy": {CONF_TARGETS_REQUIRED: False},
}


async def test_send_message_with_scenario_mismatch(mock_hass: Mock) -> None:
    uut = SuperNotificationService(
        mock_hass,
        deliveries=DELIVERY,
        scenarios=SCENARIOS,
        recipients=RECIPIENTS,
        method_defaults=METHOD_DEFAULTS,
        dupe_check={CONF_DUPE_POLICY: ATTR_DUPE_POLICY_NONE},
    )
    await uut.initialize()
    await uut.async_send_message(
        title="test_title",
        message="testing 123",
        data={"delivery_selection": DELIVERY_SELECTION_EXPLICIT, "delivery": {"pigeon": {}, "persistent": {}}},
    )
    mock_hass.services.async_call.assert_not_called()
    mock_hass.reset_mock()
    await uut.async_send_message(
        title="test_title",
        message="testing 123",
        data={
            "delivery_selection": DELIVERY_SELECTION_EXPLICIT,
            "delivery": {"pigeon": {}, "persistent": {}},
            "apply_scenarios": ["scenario1"],
        },
    )
    mock_hass.services.async_call.assert_called_with(
        "notify",
        "persistent_notification",
        service_data={"title": "test_title", "message": "testing 123", "notification_id": None},
    )


async def inject_dummy_delivery_method(
    hass: HomeAssistant, uut: SuperNotificationService, delivery_method_class: type, delivery_config=None
) -> DeliveryMethod:
    dm = delivery_method_class(hass, uut.context, deliveries=delivery_config)
    await dm.initialize()
    await uut.context.register_delivery_methods([dm], set_as_default=True)
    return dm


async def test_recipient_delivery_data_override(mock_hass: HomeAssistant) -> None:
    uut = SuperNotificationService(mock_hass, deliveries=DELIVERY, method_defaults=METHOD_DEFAULTS, recipients=RECIPIENTS)
    await uut.initialize()
    dummy: DummyDeliveryMethod = cast(
        DummyDeliveryMethod, await inject_dummy_delivery_method(mock_hass, uut, DummyDeliveryMethod)
    )
    assert dummy is not None
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


async def test_broken_delivery(mock_hass: HomeAssistant) -> None:
    delivery_config = {"broken": {CONF_METHOD: "broken"}}
    uut = SuperNotificationService(
        mock_hass, deliveries=delivery_config, method_defaults=METHOD_DEFAULTS, recipients=RECIPIENTS
    )
    await uut.initialize()
    await inject_dummy_delivery_method(mock_hass, uut, BrokenDeliveryMethod, delivery_config=delivery_config)
    await uut.async_send_message(
        title="test_title",
        message="testing 123",
        data={"delivery_selection": DELIVERY_SELECTION_EXPLICIT, "delivery": {"broken"}},
    )
    notification = uut.last_notification
    assert notification is not None
    assert len(notification.undelivered_envelopes) == 1
    assert isinstance(notification.undelivered_envelopes[0], Envelope)
    assert isinstance(notification.undelivered_envelopes[0].delivery_error, list)
    assert len(notification.undelivered_envelopes[0].delivery_error) == 4
    assert notification.undelivered_envelopes[0].delivery_error[3] == "OSError: a self-inflicted error has occurred\n"


async def test_null_delivery(mock_hass: HomeAssistant) -> None:
    uut = SuperNotificationService(mock_hass)
    await uut.initialize()
    await uut.async_send_message("just a test")
    mock_hass.services.async_call.assert_not_called()  # type: ignore


async def test_archive(mock_hass: HomeAssistant) -> None:
    with tempfile.TemporaryDirectory() as archive:
        uut = SuperNotificationService(
            mock_hass,
            deliveries=DELIVERY,
            scenarios=SCENARIOS,
            recipients=[],  # recipients will generate mock person_config data and break json
            method_defaults=METHOD_DEFAULTS,
            archive={CONF_ENABLED: True, CONF_ARCHIVE_PATH: archive},
        )
        await uut.initialize()
        await uut.async_send_message("just a test", target="person.bob")
        assert uut.last_notification is not None
        obj_path: Path = Path(archive) / f"{uut.last_notification.created.isoformat()[:16]}_{uut.last_notification.id}.json"
        assert obj_path.exists()
        async with aiofiles.open(obj_path, mode="r") as stream:
            blob: str = "".join(await stream.readlines())
            reobj = json.loads(blob)
        assert reobj["_message"] == "just a test"
        assert reobj["target"] == ["person.bob"]
        assert len(reobj["delivered_envelopes"]) == 5


async def test_cleanup_archive(mock_hass: HomeAssistant) -> None:
    archive = "config/archive/test"
    uut = SuperNotificationService(mock_hass, archive={CONF_ENABLED: True, CONF_ARCHIVE_DAYS: 7, CONF_ARCHIVE_PATH: archive})
    await uut.initialize()
    old_time = Mock(return_value=Mock(st_ctime=time.time() - (8 * 24 * 60 * 60)))
    new_time = Mock(return_value=Mock(st_ctime=time.time() - (5 * 24 * 60 * 60)))
    with patch("os.scandir") as scan:
        with patch("pathlib.Path.unlink") as rmfr:
            scan.return_value.__enter__.return_value = [
                Mock(path="abc", stat=new_time),
                Mock(path="def", stat=new_time),
                Mock(path="xyz", stat=old_time),
            ]
            uut.cleanup_archive()
            rmfr.assert_called_once_with()
    # skip cleanup for a few hours
    first_purge = uut.last_purge
    uut.cleanup_archive()
    assert first_purge == uut.last_purge


async def test_archive_size(mock_hass: HomeAssistant):
    with tempfile.TemporaryDirectory() as tmp_path:
        uut = SuperNotificationService(
            mock_hass, archive={CONF_ENABLED: True, CONF_ARCHIVE_DAYS: 7, CONF_ARCHIVE_PATH: tmp_path}
        )
        await uut.initialize()
        assert uut.archive_size() == 0
        async with aiofiles.open(Path(tmp_path) / "test.foo", mode="w") as f:
            await f.write("{}")
        assert uut.archive_size() == 1


async def test_fallback_delivery(mock_hass: HomeAssistant) -> None:
    uut = SuperNotificationService(
        mock_hass,
        deliveries={
            "generic": {CONF_METHOD: METHOD_GENERIC, CONF_SELECTION: SELECTION_FALLBACK, CONF_SERVICE: "notify.dummy"},
            "push": {CONF_METHOD: METHOD_MOBILE_PUSH, CONF_SERVICE: "notify.push", CONF_PRIORITY: "critical"},
        },
        method_defaults=METHOD_DEFAULTS,
    )
    await uut.initialize()
    await uut.async_send_message("just a test", data={"priority": "low"})
    mock_hass.services.async_call.assert_called_once_with(  # type: ignore
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
                    {CONF_CONDITION: "template", "value_template": '{{priority in ["critical", "high"]}}'},
                ],
            },
        }
    }
    calls_service_data = []

    @callback
    def mock_service_log(call: ServiceCall):
        calls_service_data.append(call.data)

    hass.services.async_register(
        "testing",
        "mock_notification",
        mock_service_log,
    )

    uut = SuperNotificationService(hass, deliveries=delivery, recipients=RECIPIENTS)
    await uut.initialize()
    hass.states.async_set("alarm_control_panel.home_alarm_control", "disarmed")

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


async def test_dupe_check_suppresses_same_priority_and_message(mock_hass: HomeAssistant) -> None:
    context = Mock(spec=SupernotificationConfiguration)
    uut = SuperNotificationService(mock_hass)
    await uut.initialize()
    n1 = Notification(context, "message here", "title here")
    assert uut.dupe_check(n1) is False
    n2 = Notification(context, "message here", "title here")
    assert uut.dupe_check(n2) is True


async def test_dupe_check_allows_higher_priority_and_same_message(mock_hass: HomeAssistant) -> None:
    context = Mock(SupernotificationConfiguration)
    uut = SuperNotificationService(mock_hass)
    await uut.initialize()
    n1 = Notification(context, "message here", "title here")
    assert uut.dupe_check(n1) is False
    n2 = Notification(context, "message here", "title here", service_data={ATTR_PRIORITY: "high"})
    assert uut.dupe_check(n2) is False
