import logging
import re

from homeassistant.components.notify.const import ATTR_DATA, ATTR_TARGET
from homeassistant.components.supernotify import (
    CONF_OVERRIDE_BASE,
    CONF_OVERRIDE_REPLACE,
    CONF_OVERRIDES,
    METHOD_ALEXA,
    METHOD_MEDIA
)
from homeassistant.components.supernotify.common import DeliveryMethod
from homeassistant.const import CONF_ENTITIES, CONF_SERVICE, CONF_TARGET

RE_VALID_MEDIA_PLAYER = r"media_player\.[A-Za-z0-9_]+"

_LOGGER = logging.getLogger(__name__)

class MediaPlayerImageDeliveryMethod(DeliveryMethod):
    def __init__(self, *args, **kwargs):
        super().__init__(METHOD_MEDIA, False, *args, **kwargs)

    def _delivery_impl(self, message=None,
                       title=None,
                       config=None,
                       recipients=None,
                       data=None,
                       **kwargs):
        _LOGGER.info("SUPERNOTIFY notify_media: %s", message)
        config = config or self.default_delivery
        media_players = []
        for recipient in recipients:
            if METHOD_MEDIA in recipient:
                media_players.append(recipient.get(
                    METHOD_MEDIA, {}).get(CONF_ENTITIES))
            elif ATTR_TARGET in recipient:
                target = recipient.get(ATTR_TARGET)
                if re.fullmatch(RE_VALID_MEDIA_PLAYER, target):
                    media_players.append(target)
        if not media_players:
            media_players = config.get(CONF_ENTITIES, [])
        if not media_players:
            _LOGGER.debug("SUPERNOTIFY skipping media show, no targets")
            return

        snapshot_url = data.get("snapshot_url")
        if snapshot_url is None:
            _LOGGER.debug("SUPERNOTIFY skipping media player, no image url")
            return

        override_config = config.get(CONF_OVERRIDES,{}).get("image_url")
        if override_config:
            new_url = snapshot_url.replace(
                override_config[CONF_OVERRIDE_BASE], override_config[CONF_OVERRIDE_REPLACE])
            _LOGGER.debug(
                "SUPERNOTIFY Overriding image url from %s to %s", snapshot_url, new_url)
            snapshot_url = new_url

        service_data = {
            "media_content_id": snapshot_url,
            "media_content_type": "image",
            "entity_id": media_players
        }
        if data and data.get("data"):
            service_data["extra"] = data.get("data")

        try:
            domain, service = config.get(
                CONF_SERVICE, "media_player.play_media").split(".", 1)
            self.hass.services.call(
                    domain, service,
                    service_data=service_data)
        except Exception as e:
            _LOGGER.error(
                "SUPERNOTIFY Failed to notify via media player (url=%s): %s", snapshot_url, e)
