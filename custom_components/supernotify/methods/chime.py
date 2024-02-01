import logging
import re

from homeassistant.components.notify.const import (
    ATTR_MESSAGE,
    ATTR_TITLE
)
from homeassistant.components.script.const import ATTR_VARIABLES
from homeassistant.components.group import expand_entity_ids
from custom_components.supernotify import METHOD_CHIME
from custom_components.supernotify.delivery_method import DeliveryMethod
from homeassistant.const import ATTR_ENTITY_ID

RE_VALID_CHIME = r"(switch|script|group|media_player)\.[A-Za-z0-9_]+"

_LOGGER = logging.getLogger(__name__)


class ChimeDeliveryMethod(DeliveryMethod):
    method = METHOD_CHIME

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate_service(self, service):
        return service is None

    def select_target(self, target):
        return re.fullmatch(RE_VALID_CHIME, target)

    async def _delivery_impl(self, envelope) -> None:
        data = envelope.data or {}
        targets = envelope.targets or []

        chime_repeat = data.pop("chime_repeat", 1)
        chime_interval = data.pop("chime_interval", 3)
        chime_tune = data.pop("chime_tune", None)

        _LOGGER.info("SUPERNOTIFY notify_chime: %s", targets)
        calls = 0
        expanded_targets = expand_entity_ids(self.hass, targets)

        for chime_entity_id in expanded_targets:
            _LOGGER.debug("SUPERNOTIFY chime %s", chime_entity_id)
            service_data = {}
            try:
                sequence = []  # TODO replace appdaemon sequencing
                domain, name = chime_entity_id.split(".", 1)

                if domain == "switch":
                    service = "turn_on"
                    service_data[ATTR_ENTITY_ID] = chime_entity_id
                elif domain == "script":
                    service = name
                    service_data.setdefault(ATTR_VARIABLES, {})
                    self.set_service_data(
                        service_data[ATTR_VARIABLES], ATTR_MESSAGE, envelope.notification.message(envelope.delivery_name))
                    self.set_service_data(
                        service_data[ATTR_VARIABLES], ATTR_TITLE, envelope.notification.title(envelope.delivery_name))
                    if data:
                        service_data.update(data)
                elif domain == "media_player":
                    service = "play_media"
                    service_data[ATTR_ENTITY_ID] = chime_entity_id
                    service_data["media_content_type"] = "sound"
                    service_data["media_content_id"] = chime_tune
                    if data:
                        service_data.update(data)
                if chime_repeat == 1:
                    await self.hass.services.async_call(
                        domain, service, service_data=service_data)
                    calls += 1
                else:
                    raise NotImplementedError("Repeat not implemented")
            except Exception as e:
                _LOGGER.error("SUPERNOTIFY Failed to chime %s: %s [%s]",
                              chime_entity_id, service_data, e)
        if calls > 0:
            envelope.delivered = True
