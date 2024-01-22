import logging
import re

from custom_components.supernotify import (
    CONF_OVERRIDE_BASE,
    CONF_OVERRIDE_REPLACE,
    CONF_OVERRIDES,
    METHOD_MEDIA,
)
from custom_components.supernotify.delivery_method import DeliveryMethod
from homeassistant.const import CONF_SERVICE

RE_VALID_MEDIA_PLAYER = r"media_player\.[A-Za-z0-9_]+"

_LOGGER = logging.getLogger(__name__)


class MediaPlayerImageDeliveryMethod(DeliveryMethod):
    method = METHOD_MEDIA

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def select_target(self, target):
        return re.fullmatch(RE_VALID_MEDIA_PLAYER, target)

    def validate_service(self, service):
        return service is None

    async def _delivery_impl(self,
                             notification,
                             delivery,
                             targets=None,
                             data=None,
                             **kwargs) -> bool:
        _LOGGER.info("SUPERNOTIFY notify_media: %s", data)
        config = notification.delivery_config.get(
            delivery) or self.default_delivery or {}
        data = data or {}
        media_players = targets or []
        if not media_players:
            _LOGGER.debug("SUPERNOTIFY skipping media show, no targets")
            return False

        snapshot_url = data.get("snapshot_url")
        if snapshot_url is None:
            _LOGGER.debug("SUPERNOTIFY skipping media player, no image url")
            return False

        override_config = config.get(CONF_OVERRIDES, {}).get("image_url")
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

        return await self.call_service(config.get(CONF_SERVICE, "media_player.play_media"), service_data)
