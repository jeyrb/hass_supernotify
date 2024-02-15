'''
Test fixture support
'''

from homeassistant import config_entries
import logging
_LOGGER = logging.getLogger(__name__)


def register_mobile_app(hass,
                        device_registry,
                        entity_registry,
                        manufacturer="xUnit",
                        model="PyTest001",
                        device_name="phone01",
                        domain="test",
                        source="unit_test",
                        title="Test Device"):
    config_entry = config_entries.ConfigEntry(domain=domain, data={
    }, version=1, minor_version=0.1, title=title, source=source)
    try:
        hass.config_entries._entries[config_entry.entry_id] = config_entry
        hass.config_entries._domain_index.setdefault(
            config_entry.domain, []).append(config_entry)
    except Exception as e:
        _LOGGER.warn(
            "Unable to mess with HASS config entries for mobile app faking: %s", e)

    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        manufacturer=manufacturer,
        model=model,
        identifiers={(domain, "device-id_%s" % device_name)}
    )
    entity_registry.async_get_or_create(
        "device_tracker",
        "mobile_app",
        device_name,
        device_id=device_entry.id
    )
