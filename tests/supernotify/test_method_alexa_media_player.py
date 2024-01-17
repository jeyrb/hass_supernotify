from unittest.mock import Mock

from custom_components.supernotify import METHOD_ALEXA
from custom_components.supernotify.common import SuperNotificationContext
from custom_components.supernotify.methods.alexa_media_player import AlexaMediaPlayerDeliveryMethod
from homeassistant.const import CONF_DEFAULT, CONF_ENTITIES, CONF_METHOD, CONF_SERVICE

DELIVERY = {
    "alexa": {CONF_METHOD: METHOD_ALEXA, CONF_SERVICE: "notify.alexa"},
}


async def test_notify_alexa() -> None:
    """Test on_notify_alexa."""
    hass = Mock()
    context = SuperNotificationContext()

    uut = AlexaMediaPlayerDeliveryMethod(hass, context,
                                         {"default": {CONF_METHOD: METHOD_ALEXA,
                                                      CONF_DEFAULT: True,
                                                      CONF_SERVICE: "notify.alexa",
                                                      CONF_ENTITIES: ["media_player.hall",
                                                                      "media_player.toilet"]}})

    await uut.deliver("hello there")
    hass.services.async_call.assert_called_with("notify", "alexa",
                                                service_data={"message": "hello there",
                                                              "data": {"type": "announce"},
                                                              "target": ["media_player.hall",
                                                                         "media_player.toilet"]})


async def test_notify_alexa_with_method_default() -> None:
    """Test on_notify_alexa."""
    hass = Mock()
    context = SuperNotificationContext(method_defaults={METHOD_ALEXA: {
        CONF_SERVICE: "notify.alexa",
        CONF_ENTITIES: ["media_player.hall",
                        "media_player.toilet"]
    }})

    uut = AlexaMediaPlayerDeliveryMethod(hass, context,
                                         {"announce": {CONF_METHOD: METHOD_ALEXA}})

    await uut.deliver("hello there")
    hass.services.async_call.assert_called_with("notify", "alexa",
                                                service_data={"message": "hello there",
                                                              "data": {"type": "announce"},
                                                              "target": ["media_player.hall",
                                                                         "media_player.toilet"]})
