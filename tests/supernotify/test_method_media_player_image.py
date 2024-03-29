from unittest.mock import Mock

from custom_components.supernotify import ATTR_DELIVERY, CONF_DATA, METHOD_MEDIA
from custom_components.supernotify.configuration import SupernotificationConfiguration
from custom_components.supernotify.methods.media_player_image import MediaPlayerImageDeliveryMethod
from homeassistant.const import CONF_DEFAULT, CONF_ENTITIES, CONF_METHOD, CONF_NAME
from custom_components.supernotify.notification import Envelope, Notification


async def test_notify_media_image(mock_hass) -> None:
    """Test on_notify_alexa."""
    context = SupernotificationConfiguration()
    context.hass_external_url = "https://myserver"

    uut = MediaPlayerImageDeliveryMethod(
        mock_hass,
        context,
        {
            "alexa_show": {
                CONF_METHOD: METHOD_MEDIA,
                CONF_NAME: "alexa_show",
                CONF_DEFAULT: True
            }
        },
    )
    await uut.initialize()
    await uut.deliver(
        Envelope(
            "alexa_show",
            Notification(
                context,
                "hello there",
                service_data={ATTR_DELIVERY: {"alexa_show": {CONF_DATA: {"snapshot_url": "/ftp/pic.jpeg"}}}},
            ),
            targets=["media_player.echo_show_8", "media_player.echo_show_10"]
        )
    )

    mock_hass.services.async_call.assert_called_with(
        "media_player",
        "play_media",
        service_data={
            "entity_id": ["media_player.echo_show_8", "media_player.echo_show_10"],
            "media_content_id": "https://myserver/ftp/pic.jpeg",
            "media_content_type": "image",
        },
    )
