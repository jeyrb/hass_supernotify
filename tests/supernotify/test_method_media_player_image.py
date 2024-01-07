from unittest.mock import Mock

from homeassistant.components.supernotify import CONF_OVERRIDE_BASE, CONF_OVERRIDE_REPLACE, CONF_OVERRIDES, CONF_PERSON, METHOD_MEDIA
from homeassistant.components.supernotify.common import SuperNotificationContext
from homeassistant.components.supernotify.methods.media_player import MediaPlayerImageDeliveryMethod
from homeassistant.const import CONF_DEFAULT, CONF_ENTITIES, CONF_METHOD

DELIVERY = {
    "alexa_show": {CONF_METHOD: METHOD_MEDIA},
}


async def test_notify_media_image() -> None:
    """Test on_notify_alexa."""
    hass = Mock()
    context = SuperNotificationContext()

    uut = MediaPlayerImageDeliveryMethod(hass, context,
                                         {"default": {CONF_METHOD: METHOD_MEDIA,
                                                      CONF_DEFAULT: True,
                                                      CONF_ENTITIES: ["media_player.echo_show_8", "media_player.echo_show_10"],
                                                      CONF_OVERRIDES: {"image_url": {CONF_OVERRIDE_BASE: "http://10.10.10.10/ftp",
                                                                                     CONF_OVERRIDE_REPLACE: "https://myserver"}
                                                                       }
                                                      }
                                          })

    await uut.deliver("hello there", data={
                "snapshot_url": "http://10.10.10.10/ftp/pic.jpeg"})

    hass.services.call.assert_called_with("media_player", "play_media",
                                          service_data={"entity_id": ["media_player.echo_show_8", "media_player.echo_show_10"],
                                                        "media_content_id": "https://myserver/pic.jpeg",
                                                        "media_content_type": "image"}
                                          )
