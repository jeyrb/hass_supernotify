from unittest.mock import Mock

from homeassistant.components.supernotify import CONF_PERSON, METHOD_ALEXA
from homeassistant.components.supernotify.common import SuperNotificationContext
from homeassistant.components.supernotify.methods.alexa_media_player import AlexaMediaPlayerDeliveryMethod
from homeassistant.const import CONF_DEFAULT, CONF_EMAIL, CONF_ENTITIES, CONF_METHOD, CONF_SERVICE

DELIVERY = {
    "alexa": {CONF_METHOD: METHOD_ALEXA, CONF_SERVICE: "notify.alexa"},
}

async def test_on_notify_alexa() -> None:
    """Test on_notify_alexa."""
    hass = Mock()
    context = SuperNotificationContext()

    uut = AlexaMediaPlayerDeliveryMethod(hass, context,
         {"default": {CONF_METHOD: METHOD_ALEXA, 
                      CONF_DEFAULT: True, 
                      CONF_SERVICE: "notify.alexa",
                      CONF_ENTITIES:["media_player.hall","media_player.toilet"] }})

    uut.deliver("hello there")
    hass.services.call.assert_called_with("notify", "alexa",
                                          service_data={"message": "hello there", "data": {"type": "announce"}, "target": ["media_player.hall","media_player.toilet"]})

