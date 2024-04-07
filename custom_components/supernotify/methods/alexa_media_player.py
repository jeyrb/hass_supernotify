import logging
import re


from homeassistant.components.notify.const import ATTR_DATA, ATTR_TARGET
from custom_components.supernotify import METHOD_ALEXA
from custom_components.supernotify.delivery_method import DeliveryMethod

from custom_components.supernotify.envelope import Envelope

RE_VALID_ALEXA = r"media_player\.[A-Za-z0-9_]+"

_LOGGER = logging.getLogger(__name__)


class AlexaMediaPlayerDeliveryMethod(DeliveryMethod):
    """
    options:
        TITLE_ONLY: true

    """

    method = METHOD_ALEXA
    DEFAULT_TITLE_ONLY = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def select_target(self, target) -> bool:
        return re.fullmatch(RE_VALID_ALEXA, target) is not None

    async def deliver(self, envelope: Envelope) -> bool:
        _LOGGER.info("SUPERNOTIFY notify_alexa: %s", envelope.message)

        media_players = envelope.targets or []

        if not media_players:
            _LOGGER.debug("SUPERNOTIFY skipping alexa, no targets")
            return False

        message = self.combined_message(envelope, default_title_only=self.DEFAULT_TITLE_ONLY)

        service_data = {"message": message or "", ATTR_DATA: {"type": "announce"}, ATTR_TARGET: media_players}
        if envelope.data and envelope.data.get("data"):
            service_data[ATTR_DATA].update(envelope.data.get("data"))
        return await self.call_service(envelope, service_data=service_data)
