import logging
import re


from homeassistant.components.notify.const import ATTR_DATA, ATTR_TARGET
from . import (
    METHOD_ALEXA
)
from .common import DeliveryMethod
from homeassistant.const import CONF_ENTITIES, CONF_SERVICE, CONF_TARGET

RE_VALID_ALEXA = r"media_player\.[A-Za-z0-9_]+"

_LOGGER = logging.getLogger(__name__)


class AlexaMediaPlayerDeliveryMethod(DeliveryMethod):
    def __init__(self, *args, **kwargs):
        super().__init__(METHOD_ALEXA, True, *args, **kwargs)

    def select_target(self, target):
        return re.fullmatch(RE_VALID_ALEXA, target)
    
    async def _delivery_impl(self, message=None,
                       title=None,
                       config=None,
                       targets=None,
                       data=None,
                       **kwargs):
        _LOGGER.info("SUPERNOTIFY notify_alexa: %s", message)
        config = config or self.default_delivery
        media_players = targets or []

        if not media_players:
            _LOGGER.debug("SUPERNOTIFY skipping alexa, no targets")
            return
        if title:
            message = "{} {}".format(title, message)
        service_data = {
            "message": message,
            ATTR_DATA: {"type": "announce"},
            ATTR_TARGET: media_players
        }
        if data and data.get("data"):
            service_data[ATTR_DATA].update(data.get("data"))
        try:
            domain, service = config.get(CONF_SERVICE).split(".", 1)
            await self.hass.services.async_call(
                domain, service, service_data=service_data)
        except Exception as e:
            _LOGGER.error("Failed to notify via Alexa (m=%s): %s", message, e)
