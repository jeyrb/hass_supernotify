import logging
import re

from homeassistant.components.notify.const import ATTR_TARGET
from custom_components.supernotify  import (
    CONF_OVERRIDE_BASE,
    CONF_OVERRIDE_REPLACE,
    CONF_OVERRIDES,
    METHOD_MEDIA,
)
from custom_components.supernotify.common import DeliveryMethod
from homeassistant.const import CONF_ENTITIES, CONF_SERVICE

RE_VALID_MEDIA_PLAYER = r"media_player\.[A-Za-z0-9_]+"

_LOGGER = logging.getLogger(__name__)

class MediaPlayerImageDeliveryMethod(DeliveryMethod):
    def __init__(self, *args, **kwargs):
        super().__init__(METHOD_MEDIA, False, *args, **kwargs)

    def select_target(self, target):
        return re.fullmatch(RE_VALID_MEDIA_PLAYER, target)
    
    async def _delivery_impl(self, message=None,
                       title=None,
                       config=None,
                       targets=None,
                       data=None,
                       **kwargs):
        _LOGGER.info("SUPERNOTIFY notify_media: %s", message)
        config = config or self.default_delivery
        media_players = targets or []
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
            await self.hass.services.async_call(
                    domain, service,
                    service_data=service_data)
        except Exception as e:
            _LOGGER.error(
                "SUPERNOTIFY Failed to notify via media player (url=%s): %s", snapshot_url, e)
