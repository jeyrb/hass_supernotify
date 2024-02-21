from unittest.mock import Mock

from custom_components.supernotify import METHOD_ALEXA
from custom_components.supernotify.configuration import SupernotificationConfiguration
from custom_components.supernotify.methods.alexa_media_player import AlexaMediaPlayerDeliveryMethod
from homeassistant.const import CONF_DEFAULT, CONF_ENTITIES, CONF_METHOD, CONF_SERVICE
from custom_components.supernotify.notification import Notification

DELIVERY = {
    "alexa": {CONF_METHOD: METHOD_ALEXA, CONF_SERVICE: "notify.alexa"},
}


async def test_notify_alexa(mock_hass) -> None:
    """Test on_notify_alexa."""
    context = SupernotificationConfiguration()

    uut = AlexaMediaPlayerDeliveryMethod(mock_hass, context,
                                         {"default": {CONF_METHOD: METHOD_ALEXA,
                                                      CONF_DEFAULT: True,
                                                      CONF_SERVICE: "notify.alexa",
                                                      CONF_ENTITIES: ["media_player.hall",
                                                                      "media_player.toilet"]}})
    await uut.initialize()
    await uut.deliver(Notification(context, message="hello there"))
    mock_hass.services.async_call.assert_called_with("notify", "alexa",
                                                service_data={"message": "hello there",
                                                              "data": {"type": "announce"},
                                                              "target": ["media_player.hall",
                                                                         "media_player.toilet"]})


async def test_notify_alexa_with_method_default(mock_hass) -> None:
    """Test on_notify_alexa."""
    context = SupernotificationConfiguration(method_defaults={METHOD_ALEXA: {
        CONF_SERVICE: "notify.alexa",
        CONF_ENTITIES: ["media_player.hall_1",
                        "media_player.toilet"]
    }})

    uut = AlexaMediaPlayerDeliveryMethod(mock_hass, context,
                                         {"announce": {CONF_METHOD: METHOD_ALEXA}})
    await uut.initialize()
    await uut.deliver(Notification(context, message="hello there", title="hey there"))
    mock_hass.services.async_call.assert_called_with("notify", "alexa",
                                                service_data={"message": "hey there",
                                                              "data": {"type": "announce"},
                                                              "target": ["media_player.hall_1",
                                                                         "media_player.toilet"]})
