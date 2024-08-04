from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry, entity_registry

from custom_components.supernotify import CONF_PERSON, CONF_RECIPIENTS
from custom_components.supernotify.configuration import SupernotificationConfiguration
from custom_components.supernotify.envelope import Envelope
from custom_components.supernotify.notification import Notification

from .doubles_lib import DummyDeliveryMethod
from .hass_setup_lib import register_mobile_app


async def test_default_recipients(mock_hass) -> None:
    context = SupernotificationConfiguration(
        mock_hass, recipients=[{CONF_PERSON: "person.new_home_owner"}, {CONF_PERSON: "person.bidey_in"}]
    )
    await context.initialize()
    dummy = DummyDeliveryMethod(mock_hass, context, {})
    await context.register_delivery_methods([dummy], set_as_default=True)
    uut = Notification(context)
    await uut.initialize()
    await uut.deliver()
    assert dummy.test_calls == [Envelope("dummy", uut, targets=["dummy.new_home_owner", "dummy.bidey_in"])]


async def test_default_recipients_with_override(mock_hass) -> None:
    context = SupernotificationConfiguration(
        mock_hass, recipients=[{CONF_PERSON: "person.new_home_owner"}, {CONF_PERSON: "person.bidey_in"}]
    )
    await context.initialize()
    dummy = DummyDeliveryMethod(mock_hass, context, {})
    await context.register_delivery_methods([dummy], set_as_default=True)
    uut = Notification(context, "testing", service_data={CONF_RECIPIENTS: ["person.new_home_owner"]})
    await uut.initialize()
    await uut.deliver()
    assert dummy.test_calls == [Envelope("dummy", uut, targets=["dummy.new_home_owner"])]


async def test_delivery_override_method(mock_hass) -> None:
    delivery_config = {
        "quiet_alert": {
            "method": "dummy",
            "entities": ["switch.pillow_vibrate"],
            "target": None,
            "selection": "explicit",
        },
        "regular_alert": {"method": "dummy", "entities": ["switch.pillow_vibrate"], "selection": "explicit"},
        "day_alert": {"method": "dummy", "selection": "explicit"},
    }
    context = SupernotificationConfiguration(
        mock_hass, method_defaults={"dummy": {"target": ["media_player.hall"]}}, deliveries=delivery_config
    )
    dummy = DummyDeliveryMethod(mock_hass, context, delivery_config)
    await context.initialize()
    await context.register_delivery_methods([dummy], set_as_default=False)
    uut = Notification(context, "testing", service_data={"delivery": ["regular_alert"]})
    await uut.initialize()
    await uut.deliver()
    envelope = uut.delivered_envelopes[0]
    assert envelope.targets == ["switch.pillow_vibrate", "media_player.hall"]

    uut = Notification(context, "testing", service_data={"delivery": ["quiet_alert"]})
    await uut.initialize()

    await uut.deliver()
    envelope = uut.delivered_envelopes[0]
    assert envelope.targets == ["switch.pillow_vibrate"]

    uut = Notification(context, "testing", service_data={"delivery": ["day_alert"]})
    await uut.initialize()

    await uut.deliver()
    envelope = uut.delivered_envelopes[0]
    assert envelope.targets == ["media_player.hall"]


async def test_autoresolve_mobile_devices_for_no_devices(hass: HomeAssistant) -> None:
    uut = SupernotificationConfiguration(hass)
    await uut.initialize()
    assert uut.mobile_devices_for_person("person.test_user") == []


async def test_autoresolve_mobile_devices_for_devices(
    hass: HomeAssistant,
    device_registry: device_registry.DeviceRegistry,
    entity_registry: entity_registry.EntityRegistry,
) -> None:
    uut = SupernotificationConfiguration(hass)
    uut._device_registry = device_registry
    uut._entity_registry = entity_registry
    await uut.initialize()
    device = await register_mobile_app(uut, person="person.test_user", device_name="phone_bob", title="Bobs Phone")
    assert device is not None
    assert uut.mobile_devices_for_person("person.test_user") == [
        {
            "manufacturer": "xUnit",
            "model": "PyTest001",
            "notify_service": "notify.mobile_app_bobs_phone",
            "device_tracker": "device_tracker.mobile_app_phone_bob",
            "device_id": device.id,
            "device_name": "Bobs Phone",
            # "device_labels": set(),
        }
    ]
