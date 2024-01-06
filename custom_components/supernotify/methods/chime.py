import logging
import re

from homeassistant.components.notify.const import ATTR_TARGET
from homeassistant.components.supernotify import METHOD_CHIME
from homeassistant.components.supernotify.common import DeliveryMethod
from homeassistant.const import CONF_ENTITIES

RE_VALID_CHIME = r"(switch|script)\.[A-Za-z0-9_]+"

_LOGGER = logging.getLogger(__name__)


class ChimeDeliveryMethod(DeliveryMethod):
    def __init__(self, *args, **kwargs):
        super().__init__(METHOD_CHIME, False, *args, **kwargs)

    def _delivery_impl(self,
                       config=None,
                       recipients=None,
                       data=None,
                       **kwargs):
        config = config or {}
        data = data or {}
        entities = []
        for recipient in recipients:
            if METHOD_CHIME in recipient:
                entities.append(recipient.get(
                    METHOD_CHIME, {}).get(CONF_ENTITIES))
            elif ATTR_TARGET in recipient:
                target = recipient.get(ATTR_TARGET)
                if re.fullmatch(RE_VALID_CHIME, target):
                    entities.append(target)
        if not entities:
            entities = config.get(CONF_ENTITIES, [])
        chime_repeat = data.get("chime_repeat", 1)
        chime_interval = data.get("chime_interval", 3)
        data = data or {}
        _LOGGER.info("SUPERNOTIFY notify_chime: %s", entities)
        for chime_entity_id in entities:
            _LOGGER.debug("SUPERNOTIFY chime %s", entities)
            try:
                sequence = []  # TODO replace appdaemon sequencing
                chime_type = chime_entity_id.split(".")[0]
                if chime_type == "script":
                    domain = "script"
                    service = "turn_on"
                else:
                    domain = "switch"
                    service = "turn_on"
                service_data = {
                    "entity_id": chime_entity_id,
                }
                if chime_repeat == 1:
                    self.hass.services.call(
                        domain, service, service_data=service_data)
                else:
                    raise NotImplementedError("Repeat not implemented")
            except Exception as e:
                _LOGGER.error("SUPERNOTIFY Failed to chime %s: %s",
                              chime_entity_id, e)
