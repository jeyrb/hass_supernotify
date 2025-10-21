import logging
import re
from typing import Any

from homeassistant.components.notify.const import ATTR_DATA, ATTR_TARGET

from custom_components.supernotify import CONF_DEFAULT_ACTION, METHOD_ALEXA_MEDIA_PLAYER, MessageOnlyPolicy
from custom_components.supernotify.delivery_method import (
    OPTION_MESSAGE_USAGE,
    OPTION_SIMPLIFY_TEXT,
    OPTION_STRIP_URLS,
    DeliveryMethod,
)
from custom_components.supernotify.envelope import Envelope

RE_VALID_ALEXA = r"media_player\.[A-Za-z0-9_]+"
ACTION = "notify.alexa_media"

_LOGGER = logging.getLogger(__name__)


class AlexaMediaPlayerDeliveryMethod(DeliveryMethod):
    """Notify via Amazon Alexa announcements

    options:
        message_usage: standard | use_title | combine_title

    """

    method = METHOD_ALEXA_MEDIA_PLAYER

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs[CONF_DEFAULT_ACTION] = ACTION
        kwargs.setdefault("default_options", {})
        kwargs["default_options"].setdefault(OPTION_SIMPLIFY_TEXT, True)
        kwargs["default_options"].setdefault(OPTION_STRIP_URLS, True)
        kwargs["default_options"].setdefault(OPTION_MESSAGE_USAGE, MessageOnlyPolicy.STANDARD)
        super().__init__(*args, **kwargs)

    def select_target(self, target: str) -> bool:
        return re.fullmatch(RE_VALID_ALEXA, target) is not None

    async def deliver(self, envelope: Envelope) -> bool:
        _LOGGER.info("SUPERNOTIFY notify_alexa: %s", envelope.message)

        media_players = envelope.targets or []

        if not media_players:
            _LOGGER.debug("SUPERNOTIFY skipping alexa, no targets")
            return False

        action_data: dict[str, Any] = {"message": envelope.message, ATTR_DATA: {"type": "announce"}, ATTR_TARGET: media_players}
        if envelope.data and envelope.data.get("data"):
            action_data[ATTR_DATA].update(envelope.data.get("data"))
        return await self.call_action(envelope, action_data=action_data)
