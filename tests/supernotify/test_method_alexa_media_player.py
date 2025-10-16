from homeassistant.const import CONF_DEFAULT, CONF_METHOD

from custom_components.supernotify import CONF_ACTION, METHOD_ALEXA_MEDIA_PLAYER
from custom_components.supernotify.configuration import Context
from custom_components.supernotify.envelope import Envelope
from custom_components.supernotify.methods.alexa_media_player import AlexaMediaPlayerDeliveryMethod
from custom_components.supernotify.notification import Notification

DELIVERY = {
    "alexa_media_player": {CONF_METHOD: METHOD_ALEXA_MEDIA_PLAYER, CONF_ACTION: "notify.alexa_media_player"},
}


async def test_notify_alexa(mock_hass) -> None:
    """Test on_notify_alexa."""
    context = Context()

    uut = AlexaMediaPlayerDeliveryMethod(
        mock_hass,
        context,
        {"default": {CONF_METHOD: METHOD_ALEXA_MEDIA_PLAYER, CONF_DEFAULT: True, CONF_ACTION: "notify.alexa_media_player"}},
    )
    await uut.initialize()
    await uut.deliver(
        Envelope("", Notification(context, message="hello there"), targets=["media_player.hall", "media_player.toilet"])
    )
    mock_hass.services.async_call.assert_called_with(
        "notify",
        "alexa_media_player",
        service_data={
            "message": "hello there",
            "data": {"type": "announce"},
            "target": ["media_player.hall", "media_player.toilet"],
        },
    )


async def test_alexa_method_selects_targets(mock_hass, superconfig) -> None:
    """Test on_notify_alexa."""
    uut = AlexaMediaPlayerDeliveryMethod(mock_hass, superconfig, {"announce": {CONF_METHOD: METHOD_ALEXA_MEDIA_PLAYER}})
    assert uut.select_target("switch.alexa_1") is False
    assert uut.select_target("media_player.hall_1") is True
