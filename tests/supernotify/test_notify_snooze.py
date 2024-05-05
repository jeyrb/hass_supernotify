from homeassistant.const import CONF_SERVICE
from homeassistant.core import Event, HomeAssistant

from custom_components.supernotify import (
    ATTR_ACTION,
    ATTR_PRIORITY,
    CONF_METHOD,
    CONF_SELECTION,
    METHOD_ALEXA,
    METHOD_CHIME,
    METHOD_EMAIL,
    METHOD_GENERIC,
    METHOD_PERSISTENT,
    METHOD_SMS,
    PRIORITY_CRITICAL,
    SELECTION_BY_SCENARIO,
    GlobalTargetType,
    QualifiedTargetType,
    RecipientType,
    Snooze,
)
from custom_components.supernotify.notification import Notification
from custom_components.supernotify.notify import SuperNotificationService

DELIVERY: dict[str, dict] = {
    "email": {CONF_METHOD: METHOD_EMAIL, CONF_SERVICE: "notify.smtp"},
    "text": {CONF_METHOD: METHOD_SMS, CONF_SERVICE: "notify.sms"},
    "chime": {CONF_METHOD: METHOD_CHIME, "entities": ["switch.bell_1", "script.siren_2"]},
    "alexa": {CONF_METHOD: METHOD_ALEXA, CONF_SERVICE: "notify.alexa"},
    "chat": {CONF_METHOD: METHOD_GENERIC, CONF_SERVICE: "notify.my_chat_server"},
    "persistent": {CONF_METHOD: METHOD_PERSISTENT, CONF_SELECTION: SELECTION_BY_SCENARIO},
    "dummy": {CONF_METHOD: "dummy"},
}


def test_snooze_delivery(mock_hass: HomeAssistant) -> None:
    uut = SuperNotificationService(mock_hass)

    uut.on_mobile_action(Event("mobile_action", data={ATTR_ACTION: "SUPERNOTIFY_SNOOZE_EVERYONE_DELIVERY_foo"}))
    assert list(uut.context.snoozes.values()) == [
        Snooze(QualifiedTargetType.DELIVERY, "foo", RecipientType.EVERYONE, snooze_for=3600)
    ]
    assert all(s["target"] == "foo" for s in uut.enquire_snoozes())
    assert all(s.snooze_until is not None and s.snooze_until - s.snoozed_at == 3600 for s in uut.context.snoozes.values())

    uut.on_mobile_action(Event("mobile_action", data={ATTR_ACTION: "SUPERNOTIFY_SILENCE_EVERYONE_DELIVERY_foo"}))
    assert list(uut.context.snoozes.values()) == [Snooze(QualifiedTargetType.DELIVERY, "foo", RecipientType.EVERYONE)]
    assert all(s.snooze_until is None for s in uut.context.snoozes.values())

    uut.on_mobile_action(Event("mobile_action", data={ATTR_ACTION: "SUPERNOTIFY_SNOOZE_EVERYONE_DELIVERY_foo_33"}))
    assert list(uut.context.snoozes.values()) == [Snooze(QualifiedTargetType.DELIVERY, "foo", RecipientType.EVERYONE)]
    assert all(s.snooze_until is not None and s.snooze_until - s.snoozed_at == 33 for s in uut.context.snoozes.values())

    uut.on_mobile_action(Event("mobile_action", data={ATTR_ACTION: "SUPERNOTIFY_NORMAL_EVERYONE_DELIVERY_foo"}))
    assert list(uut.context.snoozes.values()) == []


def test_snooze_everything(mock_hass: HomeAssistant) -> None:
    uut = SuperNotificationService(mock_hass)
    uut.on_mobile_action(Event("mobile_action", data={ATTR_ACTION: "SUPERNOTIFY_SNOOZE_EVERYONE_EVERYTHING"}))
    assert list(uut.context.snoozes.values()) == [Snooze(GlobalTargetType.EVERYTHING, "ALL", RecipientType.EVERYONE)]
    assert all(
        s.target == "ALL" and s.snooze_until is not None and s.snooze_until - s.snoozed_at == 3600
        for s in uut.context.snoozes.values()
    )

    uut.on_mobile_action(Event("mobile_action", data={ATTR_ACTION: "SUPERNOTIFY_NORMAL_EVERYONE_EVERYTHING"}))
    assert list(uut.context.snoozes.values()) == []

    uut.on_mobile_action(Event("mobile_action", data={ATTR_ACTION: "SUPERNOTIFY_SNOOZE_EVERYONE_EVERYTHING_99"}))
    assert list(uut.context.snoozes.values()) == [Snooze(GlobalTargetType.EVERYTHING, "ALL", RecipientType.EVERYONE)]
    assert all(
        s.target == "ALL" and s.snooze_until is not None and s.snooze_until - s.snoozed_at == 99
        for s in uut.context.snoozes.values()
    )


async def test_check_notification_for_snooze_global(mock_hass: HomeAssistant):
    uut = SuperNotificationService(mock_hass, deliveries=DELIVERY)
    await uut.initialize()
    ctx = uut.context

    plain_notify = Notification(ctx, "hello")
    assert plain_notify.check_for_snoozes() == (False, [])

    uut.on_mobile_action(Event("mobile_action", data={ATTR_ACTION: "SUPERNOTIFY_SNOOZE_EVERYONE_EVERYTHING"}))
    assert plain_notify.check_for_snoozes() == (True, [])

    uut.on_mobile_action(Event("mobile_action", data={ATTR_ACTION: "SUPERNOTIFY_SNOOZE_EVERYONE_NONCRITICAL"}))
    crit_notify = Notification(ctx, "hello", service_data={ATTR_PRIORITY: PRIORITY_CRITICAL})
    assert crit_notify.check_for_snoozes() == (
        False,
        [],
    )
    assert plain_notify.check_for_snoozes() == (True, [])
    uut.shutdown()


async def test_check_notification_for_snooze_qualified(mock_hass: HomeAssistant):
    uut = SuperNotificationService(mock_hass, deliveries=DELIVERY)
    await uut.initialize()
    ctx = uut.context
    notification = Notification(ctx, "hello")
    await notification.initialize()
    uut.on_mobile_action(Event("mobile_action", data={ATTR_ACTION: "SUPERNOTIFY_SNOOZE_EVERYONE_DELIVERY_chime"}))
    uut.on_mobile_action(Event("mobile_action", data={ATTR_ACTION: "SUPERNOTIFY_SILENCE_EVERYONE_CAMERA_Yard"}))
    uut.on_mobile_action(Event("mobile_action", data={ATTR_ACTION: "SUPERNOTIFY_SNOOZE_EVERYONE_METHOD_email"}))
    uut.on_mobile_action(Event("mobile_action", data={ATTR_ACTION: "SUPERNOTIFY_SNOOZE_EVERYONE_METHOD_LASER"}))
    assert notification.check_for_snoozes() == (
        False,
        [
            Snooze(QualifiedTargetType.DELIVERY, "chime", RecipientType.EVERYONE),
            Snooze(QualifiedTargetType.CAMERA, "Yard", RecipientType.EVERYONE),
            Snooze(QualifiedTargetType.METHOD, "email", RecipientType.EVERYONE),
        ],
    )
    uut.shutdown()
