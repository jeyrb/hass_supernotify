import logging
import re


from homeassistant.components.notify.const import ATTR_DATA, ATTR_TARGET
from homeassistant.components.supernotify import (
    METHOD_ALEXA
)
from homeassistant.components.supernotify.common import DeliveryMethod
from homeassistant.const import CONF_ENTITIES, CONF_SERVICE, CONF_TARGET

RE_VALID_ALEXA = r"media_player\.[A-Za-z0-9_]+"

_LOGGER = logging.getLogger(__name__)


class AlexaMediaPlayerDeliveryMethod(DeliveryMethod):
    def __init__(self, *args, **kwargs):
        super().__init__(METHOD_ALEXA, True, *args, **kwargs)

    def _delivery_impl(self, message=None,
                       title=None,
                       config=None,
                       recipients=None,
                       data=None,
                       **kwargs):
        _LOGGER.info("SUPERNOTIFY notify_alexa: %s", message)
        config = config or self.default_delivery
        media_players = []
        for recipient in recipients:
            if METHOD_ALEXA in recipient:
                media_players.append(recipient.get(
                    METHOD_ALEXA, {}).get(CONF_ENTITIES))
            elif ATTR_TARGET in recipient:
                target = recipient.get(ATTR_TARGET)
                if re.fullmatch(RE_VALID_ALEXA, target):
                    media_players.append(target)

        if not media_players:
            media_players = config.get(CONF_ENTITIES, [])
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
            self.hass.services.call(
                domain, service, service_data=service_data)
        except Exception as e:
            _LOGGER.error("Failed to notify via Alexa (m=%s): %s", message, e)
