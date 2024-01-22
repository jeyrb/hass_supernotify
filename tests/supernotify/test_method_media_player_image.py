from unittest.mock import Mock

from custom_components.supernotify import ATTR_DELIVERY, CONF_DATA, CONF_OVERRIDE_BASE, CONF_OVERRIDE_REPLACE, CONF_OVERRIDES, METHOD_MEDIA
from custom_components.supernotify.configuration import SupernotificationConfiguration
from custom_components.supernotify.methods.media_player_image import MediaPlayerImageDeliveryMethod
from homeassistant.const import CONF_DEFAULT, CONF_ENTITIES, CONF_METHOD, CONF_NAME
from custom_components.supernotify.notification import Notification


async def test_notify_media_image() -> None:
    """Test on_notify_alexa."""
    hass = Mock()
    context = SupernotificationConfiguration()

    uut = MediaPlayerImageDeliveryMethod(hass, context,
                                         {"alexa_show": {
                                             CONF_METHOD: METHOD_MEDIA,
                                             CONF_NAME: "alexa_show",
                                             CONF_DEFAULT: True,
                                             CONF_ENTITIES: ["media_player.echo_show_8",
                                                             "media_player.echo_show_10"],
                                             CONF_OVERRIDES: {"image_url": {
                                                 CONF_OVERRIDE_BASE: "http://10.10.10.10/ftp",
                                                 CONF_OVERRIDE_REPLACE: "https://myserver"}
                                             }
                                         }})
    await uut.initialize()
    await uut.deliver(Notification(context, "hello there", service_data={
        ATTR_DELIVERY: {"alexa_show": {CONF_DATA: {"snapshot_url": "http://10.10.10.10/ftp/pic.jpeg"}}}}))

    hass.services.async_call.assert_called_with("media_player", "play_media",
                                                service_data={"entity_id": ["media_player.echo_show_8",
                                                                            "media_player.echo_show_10"],
                                                              "media_content_id": "https://myserver/pic.jpeg",
                                                              "media_content_type": "image"}
                                                )
