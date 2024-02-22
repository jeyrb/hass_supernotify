from unittest.mock import Mock, AsyncMock


from custom_components.supernotify import CONF_DATA, METHOD_CHIME
from custom_components.supernotify.configuration import SupernotificationConfiguration
from custom_components.supernotify.methods.chime import ChimeDeliveryMethod
from homeassistant.const import CONF_DEFAULT, CONF_ENTITIES, CONF_METHOD, CONF_TARGET, ATTR_ENTITY_ID
from custom_components.supernotify.notification import Notification


async def test_deliver(mock_hass) -> None:
    """Test on_notify_chime"""
    context = SupernotificationConfiguration()
    uut = ChimeDeliveryMethod(
        mock_hass,
        context,
        {"chimes": {CONF_METHOD: METHOD_CHIME, CONF_DEFAULT: True, CONF_ENTITIES: ["switch.bell_1", "script.siren_2"]}},
    )
    await uut.initialize()
    delivered_envelopes, undelivered_envelopes = await uut.deliver(Notification(context))
    assert not undelivered_envelopes
    assert len(delivered_envelopes) == 1
    assert len(delivered_envelopes[0].calls) == 2
    mock_hass.services.async_call.assert_any_call("script", "siren_2", service_data={"variables": {}})
    mock_hass.services.async_call.assert_any_call("switch", "turn_on", service_data={"entity_id": "switch.bell_1"})


async def test_deliver_alias(mock_hass) -> None:
    """Test on_notify_chime"""
    mock_hass.services.async_call = AsyncMock()
    context = SupernotificationConfiguration(
        method_defaults={
            "chime": {
                "target": ["media_player.kitchen_alexa", "media_player.hall_echo"],
                "options": {
                    "chime_aliases": {
                        "doorbell": {
                            "media_player": "home/amzn_sfx_doorbell_chime_02",
                            "switch": {"entity_id": "switch.chime_ding_dong"},
                        }
                    }
                },
            }
        }
    )
    uut = ChimeDeliveryMethod(
        mock_hass, context, {"chimes": {CONF_METHOD: METHOD_CHIME, CONF_DEFAULT: True, CONF_DATA: {"chime_tune": "doorbell"}}}
    )
    await uut.initialize()
    delivered_envelopes, undelivered_envelopes = await uut.deliver(Notification(context))
    assert not undelivered_envelopes
    assert len(delivered_envelopes) == 1
    assert len(delivered_envelopes[0].calls) == 3
    mock_hass.services.async_call.assert_any_call("switch", "turn_on", service_data={"entity_id": "switch.chime_ding_dong"})
    mock_hass.services.async_call.assert_any_call(
        "media_player",
        "play_media",
        service_data={
            "entity_id": "media_player.kitchen_alexa",
            "media_content_type": "sound",
            "media_content_id": "home/amzn_sfx_doorbell_chime_02",
        },
    )
    mock_hass.services.async_call.assert_any_call(
        "media_player",
        "play_media",
        service_data={
            "entity_id": "media_player.hall_echo",
            "media_content_type": "sound",
            "media_content_id": "home/amzn_sfx_doorbell_chime_02",
        },
    )


class MockGroup:
    def __init__(self, entities):
        self.attributes = {ATTR_ENTITY_ID: entities}


async def test_deliver_to_group(mock_hass) -> None:
    """Test on_notify_chime"""
    GROUPS = {
        "group.alexa": MockGroup(["media_player.alexa_1", "media_player.alexa_2"]),
        "group.chime": MockGroup(["switch.bell_1"]),
    }

    mock_hass.states.get.side_effect = lambda v: GROUPS.get(v)
    context = SupernotificationConfiguration()
    uut = ChimeDeliveryMethod(
        mock_hass,
        context,
        {
            "chimes": {
                CONF_METHOD: METHOD_CHIME,
                CONF_DEFAULT: True,
                CONF_TARGET: ["group.alexa", "group.chime", "script.siren_2"],
                CONF_DATA: {"chime_tune": "dive_dive_dive"},
            }
        },
    )
    await uut.initialize()
    await uut.deliver(Notification(context))
    mock_hass.services.async_call.assert_any_call("script", "siren_2", service_data={"variables": {}})
    mock_hass.services.async_call.assert_any_call("switch", "turn_on", service_data={"entity_id": "switch.bell_1"})
    mock_hass.services.async_call.assert_any_call(
        "media_player",
        "play_media",
        service_data={"entity_id": "media_player.alexa_1", "media_content_type": "sound", "media_content_id": "dive_dive_dive"},
    )
