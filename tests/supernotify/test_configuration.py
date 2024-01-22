from unittest.mock import Mock
from .hass_setup_lib import register_mobile_app
from custom_components.supernotify import CONF_PERSON, CONF_RECIPIENTS
from custom_components.supernotify.configuration import SupernotificationConfiguration
from homeassistant.helpers import device_registry, entity_registry
from custom_components.supernotify.notification import Notification
from .doubles_lib import DummyDeliveryMethod
from homeassistant.core import HomeAssistant


async def test_filter_recipients() -> None:
    hass = Mock()
    context = SupernotificationConfiguration(recipients=[{CONF_PERSON: "person.new_home_owner"},
                                                   {CONF_PERSON: "person.bidey_in"}])
    uut = DummyDeliveryMethod(hass, context, {})
    hass_states = {"person.new_home_owner": Mock(state="not_home"),
                   "person.bidey_in": Mock(state="home")}
    hass.states.get = hass_states.get

    assert len(uut.filter_recipients_by_occupancy("all_in")) == 0
    assert len(uut.filter_recipients_by_occupancy("all_out")) == 0
    assert len(uut.filter_recipients_by_occupancy("any_in")) == 2
    assert len(uut.filter_recipients_by_occupancy("any_out")) == 2
    assert len(uut.filter_recipients_by_occupancy("only_in")) == 1
    assert len(uut.filter_recipients_by_occupancy("only_out")) == 1

    assert {r["person"] for r in uut.filter_recipients_by_occupancy(
        "only_out")} == {"person.new_home_owner"}
    assert {r["person"]
            for r in uut.filter_recipients_by_occupancy("only_in")} == {"person.bidey_in"}


async def test_default_recipients() -> None:
    hass = Mock()
    context = SupernotificationConfiguration(recipients=[{CONF_PERSON: "person.new_home_owner"},
                                                   {CONF_PERSON: "person.bidey_in"}])
    uut = DummyDeliveryMethod(hass, context, {})
    await uut.deliver(Notification(context))
    assert uut.test_calls == [
        [None, None, ['dummy.new_home_owner', 'dummy.bidey_in'], 'medium', {}, {}, {}]]


async def test_default_recipients_with_override() -> None:
    hass = Mock()
    context = SupernotificationConfiguration(recipients=[{CONF_PERSON: "person.new_home_owner"},
                                                   {CONF_PERSON: "person.bidey_in"}])
    uut = DummyDeliveryMethod(hass, context, {})
    await uut.deliver(Notification(context, None,
                                   service_data={CONF_RECIPIENTS: ["person.new_home_owner"]}))
    assert uut.test_calls == [
        [None, None, ['dummy.new_home_owner'], 'medium', {}, {}, {}]]


async def test_autoresolve_mobile_devices_for_no_devices(hass: HomeAssistant) -> None:
    uut = SupernotificationConfiguration(hass)
    await uut.initialize()
    assert uut.mobile_devices_for_person("person.test_user") == []


async def test_autoresolve_mobile_devices_for_devices(hass: HomeAssistant,
                                                      device_registry: device_registry.DeviceRegistry,
                                                      entity_registry: entity_registry.EntityRegistry,) -> None:
    uut = SupernotificationConfiguration(hass)
    await uut.initialize()
    hass.states.async_set("person.test_user", "home", attributes={
                          "device_trackers": ["device_tracker.mobile_app_phone_bob", "dev002"]})
    register_mobile_app(hass, device_registry,
                        entity_registry,
                        device_name="phone_bob",
                        title="Bobs Phone")
    assert uut.mobile_devices_for_person("person.test_user", device_registry, entity_registry) == [{'device_tracker': 'device_tracker.mobile_app_phone_bob',
                                                                                                    'manufacturer': "xUnit",
                                                                                                   'model': "PyTest001",
                                                                                                    'notify_service': 'mobile_app_bobs_phone'}]
