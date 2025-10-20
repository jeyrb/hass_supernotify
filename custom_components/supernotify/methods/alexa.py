import logging
import re
from typing import Any

from homeassistant.components.notify.const import ATTR_MESSAGE
from homeassistant.const import ATTR_ENTITY_ID

from custom_components.supernotify import CONF_DEFAULT_ACTION, METHOD_ALEXA, MessageOnlyPolicy
from custom_components.supernotify.delivery_method import (
    OPTION_MESSAGE_USAGE,
    OPTION_SIMPLIFY_TEXT,
    OPTION_STRIP_URLS,
    DeliveryMethod,
)
from custom_components.supernotify.envelope import Envelope

_LOGGER = logging.getLogger(__name__)
ACTION = "notify.send_message"


class AlexaDeliveryMethod(DeliveryMethod):
    """Notify via Home Assistant's built-in Alexa integration

    options:
        message_usage: standard | use_title | combine_title

    """

    method = METHOD_ALEXA

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault(CONF_DEFAULT_ACTION, ACTION)
        kwargs.setdefault("default_options", {})
        kwargs["default_options"].setdefault(OPTION_SIMPLIFY_TEXT, True)
        kwargs["default_options"].setdefault(OPTION_STRIP_URLS, True)
        kwargs["default_options"].setdefault(OPTION_MESSAGE_USAGE, MessageOnlyPolicy.STANDARD)
        super().__init__(*args, **kwargs)

    def select_target(self, target: str) -> bool:
        return (
            re.fullmatch(r"notify\.[a-z0-9_]+\_(speak|announce)", target) is not None
            or re.fullmatch(r"group\.[a-z0-9_]+", target) is not None
        )

    async def deliver(self, envelope: Envelope) -> bool:
        _LOGGER.info("SUPERNOTIFY notify_alexa: %s", envelope.message)

        targets = envelope.targets or []

        if not targets:
            _LOGGER.debug("SUPERNOTIFY skipping alexa, no targets")
            return False

        action_data: dict[str, Any] = {ATTR_MESSAGE: self.simplify(envelope.message, strip_urls=True) or ""}
        target_data: dict[str, Any] = {ATTR_ENTITY_ID: targets}

        return await self.call_action(envelope, action_data=action_data, target_data=target_data)
