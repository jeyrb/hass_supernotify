import logging
import re

from homeassistant.components.notify.const import ATTR_DATA, ATTR_TARGET
from custom_components.supernotify import METHOD_CHIME
from custom_components.supernotify.common import DeliveryMethod
from homeassistant.const import ATTR_ENTITY_ID

RE_VALID_CHIME = r"(switch|script|media_player)\.[A-Za-z0-9_]+"

_LOGGER = logging.getLogger(__name__)


class ChimeDeliveryMethod(DeliveryMethod):
    def __init__(self, *args, **kwargs):
        super().__init__(METHOD_CHIME, False, *args, **kwargs)

    def select_target(self, target):
        return re.fullmatch(RE_VALID_CHIME, target)
    
    async def _delivery_impl(self,
                       config=None,
                       targets=None,
                       data=None,
                       **kwargs):
        config = config or {}
        data = data or {}
        targets = targets or []

        chime_repeat = data.get("chime_repeat", 1)
        chime_interval = data.get("chime_interval", 3)
        chime_tune = data.get("chime_tune")
        data = data or {}
        _LOGGER.info("SUPERNOTIFY notify_chime: %s", targets)
        service_data={}
        for chime_entity_id in targets:
            _LOGGER.debug("SUPERNOTIFY chime %s", chime_entity_id)
            try:
                sequence = []  # TODO replace appdaemon sequencing
                domain, name = chime_entity_id.split(".",1)

                if domain == "switch":
                    service = "turn_on"
                    service_data[ATTR_ENTITY_ID] = chime_entity_id
                elif domain == "script":
                    service = name
                    if data:
                        service_data[ATTR_DATA] = data
                elif domain == "media_player":
                    service = "play_media"
                    service_data[ATTR_DATA]["media_content_type"] = "sound"
                    service_data[ATTR_DATA]["media_content_id"] = chime_tune
                    if data:
                        service_data[ATTR_DATA].update(data)
                if chime_repeat == 1:
                    await self.hass.services.async_call(
                        domain, service, service_data=service_data)
                else:
                    raise NotImplementedError("Repeat not implemented")
            except Exception as e:
                _LOGGER.error("SUPERNOTIFY Failed to chime %s: %s [%s]",
                              chime_entity_id, service_data, e)
