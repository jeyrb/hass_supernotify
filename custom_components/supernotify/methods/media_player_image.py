import logging
import re

from custom_components.supernotify import (
    METHOD_MEDIA,
)
import urllib.parse
from custom_components.supernotify.delivery_method import DeliveryMethod
from homeassistant.const import CONF_SERVICE

from custom_components.supernotify.notification import Envelope

RE_VALID_MEDIA_PLAYER = r"media_player\.[A-Za-z0-9_]+"

_LOGGER = logging.getLogger(__name__)


class MediaPlayerImageDeliveryMethod(DeliveryMethod):
    method = METHOD_MEDIA

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def select_target(self, target):
        return re.fullmatch(RE_VALID_MEDIA_PLAYER, target)

    def validate_service(self, service):
        return service is None or service == "media_player.play_media"

    async def _delivery_impl(self, envelope: Envelope) -> None:

        _LOGGER.info("SUPERNOTIFY notify_media: %s", envelope.data)
        config = self.context.deliveries.get(envelope.delivery_name) or self.default_delivery or {}
        data = envelope.data or {}
        media_players = envelope.targets or []
        if not media_players:
            _LOGGER.debug("SUPERNOTIFY skipping media show, no targets")
            return False

        snapshot_url = data.get("snapshot_url")
        if snapshot_url is None:
            _LOGGER.debug("SUPERNOTIFY skipping media player, no image url")
            return False
        else:
            # absolutize relative URL for external URl, probably preferred by Alexa Show etc
            snapshot_url = urllib.parse.urljoin(self.context.hass_external_url, snapshot_url)

        service_data = {"media_content_id": snapshot_url, "media_content_type": "image", "entity_id": media_players}
        if data and data.get("data"):
            service_data["extra"] = data.get("data")

        await self.call_service(envelope, config.get(CONF_SERVICE, "media_player.play_media"), service_data)
