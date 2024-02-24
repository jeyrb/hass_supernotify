import logging
import re


from homeassistant.components.notify.const import ATTR_DATA, ATTR_TARGET
from custom_components.supernotify import METHOD_ALEXA
from custom_components.supernotify.delivery_method import DeliveryMethod
from homeassistant.const import CONF_SERVICE

from custom_components.supernotify.notification import Envelope

RE_VALID_ALEXA = r"media_player\.[A-Za-z0-9_]+"

_LOGGER = logging.getLogger(__name__)


class AlexaMediaPlayerDeliveryMethod(DeliveryMethod):
    """
    options:
        TITLE_ONLY: true

    """

    method = METHOD_ALEXA

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def select_target(self, target):
        return re.fullmatch(RE_VALID_ALEXA, target)

    async def _delivery_impl(self, envelope: Envelope) -> bool:
        _LOGGER.info("SUPERNOTIFY notify_alexa: %s", envelope.message)

        media_players = envelope.targets or []

        if not media_players:
            _LOGGER.debug("SUPERNOTIFY skipping alexa, no targets")
            return False

        message = self.combined_message(envelope, default_title_only=True)

        service_data = {"message": message or "", ATTR_DATA: {"type": "announce"}, ATTR_TARGET: media_players}
        if envelope.data and envelope.data.get("data"):
            service_data[ATTR_DATA].update(envelope.data.get("data"))
        await self.call_service(envelope, service_data=service_data)
