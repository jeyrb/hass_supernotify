from .hass_setup_lib import register_mobile_app
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry, entity_registry

from custom_components.supernotify import CONF_PERSON, CONF_RECIPIENTS, SCENARIO_DEFAULT
from custom_components.supernotify.configuration import SupernotificationConfiguration
from custom_components.supernotify.notification import Notification
from custom_components.supernotify.envelope import Envelope

from .doubles_lib import DummyDeliveryMethod


async def test_default_recipients(mock_hass) -> None:
    context = SupernotificationConfiguration(
        mock_hass, recipients=[{CONF_PERSON: "person.new_home_owner"}, {CONF_PERSON: "person.bidey_in"}]
    )
    await context.initialize()
    dummy = DummyDeliveryMethod(mock_hass, context, {})
    await context.register_delivery_methods([dummy],set_as_default=True)
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
    await uut.initialize()
    hass.states.async_set(
        "person.test_user", "home", attributes={"device_trackers": ["device_tracker.mobile_app_phone_bob", "dev002"]}
    )
    register_mobile_app(hass, device_registry, entity_registry, device_name="phone_bob", title="Bobs Phone")
    assert uut.mobile_devices_for_person("person.test_user", device_registry, entity_registry) == [
        {
            "device_tracker": "device_tracker.mobile_app_phone_bob",
            "manufacturer": "xUnit",
            "model": "PyTest001",
            "notify_service": "mobile_app_bobs_phone",
        }
    ]
