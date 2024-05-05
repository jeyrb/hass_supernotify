from homeassistant.const import CONF_SERVICE
from homeassistant.core import Context, Event, HomeAssistant
from homeassistant.helpers import device_registry, entity_registry

from custom_components.supernotify import (
    ATTR_ACTION,
    ATTR_PRIORITY,
    ATTR_USER_ID,
    CONF_METHOD,
    CONF_PERSON,
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
from tests.supernotify.hass_setup_lib import register_mobile_app

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
        Snooze(QualifiedTargetType.DELIVERY, RecipientType.EVERYONE, "foo", snooze_for=3600)
    ]
    assert all(s["target"] == "foo" for s in uut.enquire_snoozes())
    assert all(s.snooze_until is not None and s.snooze_until - s.snoozed_at == 3600 for s in uut.context.snoozes.values())

    uut.on_mobile_action(Event("mobile_action", data={ATTR_ACTION: "SUPERNOTIFY_SILENCE_EVERYONE_DELIVERY_foo"}))
    assert list(uut.context.snoozes.values()) == [Snooze(QualifiedTargetType.DELIVERY, RecipientType.EVERYONE, "foo")]
    assert all(s.snooze_until is None for s in uut.context.snoozes.values())

    uut.on_mobile_action(Event("mobile_action", data={ATTR_ACTION: "SUPERNOTIFY_SNOOZE_EVERYONE_DELIVERY_foo_33"}))
    assert list(uut.context.snoozes.values()) == [Snooze(QualifiedTargetType.DELIVERY, RecipientType.EVERYONE, "foo")]
    assert all(s.snooze_until is not None and s.snooze_until - s.snoozed_at == 33 for s in uut.context.snoozes.values())

    uut.on_mobile_action(Event("mobile_action", data={ATTR_ACTION: "SUPERNOTIFY_NORMAL_EVERYONE_DELIVERY_foo"}))
    assert list(uut.context.snoozes.values()) == []


def test_snooze_everything(mock_hass: HomeAssistant) -> None:
    uut = SuperNotificationService(mock_hass)
    uut.on_mobile_action(Event("mobile_action", data={ATTR_ACTION: "SUPERNOTIFY_SNOOZE_EVERYONE_EVERYTHING"}))
    assert list(uut.context.snoozes.values()) == [Snooze(GlobalTargetType.EVERYTHING, recipient_type=RecipientType.EVERYONE)]
    assert all(
        s.target is None and s.snooze_until is not None and s.snooze_until - s.snoozed_at == 3600
        for s in uut.context.snoozes.values()
    )

    uut.on_mobile_action(Event("mobile_action", data={ATTR_ACTION: "SUPERNOTIFY_NORMAL_EVERYONE_EVERYTHING"}))
    assert list(uut.context.snoozes.values()) == []

    uut.on_mobile_action(Event("mobile_action", data={ATTR_ACTION: "SUPERNOTIFY_SNOOZE_EVERYONE_EVERYTHING_99"}))
    assert list(uut.context.snoozes.values()) == [Snooze(GlobalTargetType.EVERYTHING, recipient_type=RecipientType.EVERYONE)]
    assert all(
        s.target is None and s.snooze_until is not None and s.snooze_until - s.snoozed_at == 99
        for s in uut.context.snoozes.values()
    )


async def test_check_notification_for_snooze_global(mock_hass: HomeAssistant):
    uut = SuperNotificationService(mock_hass, deliveries=DELIVERY)
    await uut.initialize()

    plain_notify = Notification(uut.context, "hello")
    assert plain_notify.check_for_snoozes() == (False, [])

    uut.on_mobile_action(Event("mobile_action", data={ATTR_ACTION: "SUPERNOTIFY_SNOOZE_EVERYONE_EVERYTHING"}))
    assert plain_notify.check_for_snoozes() == (True, [(Snooze(GlobalTargetType.EVERYTHING, RecipientType.EVERYONE))])

    uut.on_mobile_action(Event("mobile_action", data={ATTR_ACTION: "SUPERNOTIFY_SNOOZE_EVERYONE_NONCRITICAL"}))
    crit_notify = Notification(uut.context, "hello", service_data={ATTR_PRIORITY: PRIORITY_CRITICAL})
    assert crit_notify.check_for_snoozes() == (
        False,
        [],
    )
    assert plain_notify.check_for_snoozes() == (True, [Snooze(GlobalTargetType.EVERYTHING, RecipientType.EVERYONE)])
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
            Snooze(QualifiedTargetType.DELIVERY, RecipientType.EVERYONE, "chime"),
            Snooze(QualifiedTargetType.CAMERA, RecipientType.EVERYONE, "Yard"),
            Snooze(QualifiedTargetType.METHOD, RecipientType.EVERYONE, "email"),
        ],
    )
    uut.shutdown()


async def test_snooze_everything_for_person(
    hass: HomeAssistant, device_registry: device_registry.DeviceRegistry, entity_registry: entity_registry.EntityRegistry
) -> None:
    uut = SuperNotificationService(
        hass,
        recipients=[
            {CONF_PERSON: "person.bob_mctest", ATTR_USER_ID: "eee999111"},
            {CONF_PERSON: "person.jane_macunit", ATTR_USER_ID: "fff444222"},
        ],
        deliveries=DELIVERY,
    )
    await uut.initialize()
    register_mobile_app(hass, device_registry, entity_registry, person="person.bob_mctest")
    plain_notify = Notification(uut.context, "hello")
    await plain_notify.initialize()
    assert ["person.bob_mctest", "person.jane_macunit"] == [
        p[CONF_PERSON] for p in plain_notify.generate_recipients("email", uut.context.delivery_method("email"))
    ]

    uut.on_mobile_action(
        Event("mobile_action", data={ATTR_ACTION: "SUPERNOTIFY_SNOOZE_USER_EVERYTHING"}, context=Context(user_id="eee999111"))
    )
    assert list(uut.context.snoozes.values()) == [
        Snooze(GlobalTargetType.EVERYTHING, recipient_type=RecipientType.USER, recipient="person.bob_mctest")
    ]
    await plain_notify.initialize()
    assert ["person.jane_macunit"] == [
        p[CONF_PERSON] for p in plain_notify.generate_recipients("email", uut.context.delivery_method("email"))
    ]

    uut.on_mobile_action(
        Event("mobile_action", data={ATTR_ACTION: "SUPERNOTIFY_NORMAL_USER_EVERYTHING"}, context=Context(user_id="eee999111"))
    )
    assert list(uut.context.snoozes.values()) == []
    await plain_notify.initialize()
    assert ["person.bob_mctest", "person.jane_macunit"] == [
        p[CONF_PERSON] for p in plain_notify.generate_recipients("email", uut.context.delivery_method("email"))
    ]

    uut.shutdown()
