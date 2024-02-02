import logging
import re


from homeassistant.components.notify.const import ATTR_DATA, ATTR_TARGET
from custom_components.supernotify import (
    CONF_OPTIONS,
    METHOD_ALEXA
)
from custom_components.supernotify.delivery_method import DeliveryMethod
from homeassistant.const import CONF_SERVICE

RE_VALID_ALEXA = r"media_player\.[A-Za-z0-9_]+"

_LOGGER = logging.getLogger(__name__)


class AlexaMediaPlayerDeliveryMethod(DeliveryMethod):
    method = METHOD_ALEXA

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def select_target(self, target):
        return re.fullmatch(RE_VALID_ALEXA, target)

    async def _delivery_impl(self, envelope) -> bool:
        _LOGGER.info("SUPERNOTIFY notify_alexa: %s", envelope.message)
        config = self.context.deliveries.get(
            envelope.delivery_name) or self.default_delivery or {}
        media_players = envelope.targets or []

        if not media_players:
            _LOGGER.debug("SUPERNOTIFY skipping alexa, no targets")
            return False
        if config.get(CONF_OPTIONS, {}).get("title_only", True):
            message = envelope.title
        else:
            if envelope.title:
                message = "{} {}".format(envelope.title, envelope.message)
            else:
                message = envelope.message

        service_data = {
            "message": message,
            ATTR_DATA: {"type": "announce"},
            ATTR_TARGET: media_players
        }
        if envelope.data and envelope.data.get("data"):
            service_data[ATTR_DATA].update(envelope.data.get("data"))
        if await self.call_service(config.get(CONF_SERVICE), service_data):
            envelope.delivered = 1
