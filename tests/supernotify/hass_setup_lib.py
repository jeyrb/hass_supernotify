"""Test fixture support"""

import logging

from homeassistant import config_entries

from custom_components.supernotify.configuration import SupernotificationConfiguration

_LOGGER = logging.getLogger(__name__)


def register_mobile_app(
    context: SupernotificationConfiguration,
    person="person.test_user",
    manufacturer="xUnit",
    model="PyTest001",
    device_name="phone01",
    domain="test",
    source="unit_test",
    title="Test Device",
):
    config_entry = config_entries.ConfigEntry(
        domain=domain, data={}, version=1, minor_version=1, unique_id=None, options=None, title=title, source=source
    )
    if context is None or context.hass is None:
        _LOGGER.warning("Unable to mess with HASS config entries for mobile app faking")
        return
    try:
        context.hass.config_entries._entries[config_entry.entry_id] = config_entry  # type: ignore
        context.hass.config_entries._domain_index.setdefault(config_entry.domain, []).append(config_entry)  # type: ignore
    except Exception as e:
        _LOGGER.warning("Unable to mess with HASS config entries for mobile app faking: %s", e)
    context.hass.states.async_set(
        person, "home", attributes={"device_trackers": [f"device_tracker.mobile_app_{device_name}", "dev002"]}
    )
    device_registry = context.device_registry()
    device_entry = None
    if device_registry:
        device_entry = device_registry.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            manufacturer=manufacturer,
            model=model,
            identifiers={(domain, f"device-id_{device_name}")},
        )
    entity_registry = context.entity_registry()
    if entity_registry and device_entry:
        entity_registry.async_get_or_create("device_tracker", "mobile_app", device_name, device_id=device_entry.id)
