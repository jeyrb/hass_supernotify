from homeassistant.const import ATTR_ENTITY_ID, CONF_DEFAULT, CONF_METHOD

from custom_components.supernotify import CONF_DATA, METHOD_CHIME
from custom_components.supernotify.configuration import SupernotificationConfiguration
from custom_components.supernotify.envelope import Envelope
from custom_components.supernotify.methods.chime import ChimeDeliveryMethod
from custom_components.supernotify.notification import Notification


async def test_deliver(mock_hass) -> None:
    """Test on_notify_chime"""
    context = SupernotificationConfiguration()
    uut = ChimeDeliveryMethod(
        mock_hass,
        context,
        {"chimes": {CONF_METHOD: METHOD_CHIME, CONF_DEFAULT: True}},
    )
    await uut.initialize()
    envelope = Envelope(
        "", Notification(context, message="for script only"), targets=["switch.bell_1", "script.alarm_2", "siren.lobby"]
    )
    await uut.deliver(envelope)
    assert envelope.skipped == 0
    assert envelope.delivered == 1
    assert len(envelope.calls) == 3

    mock_hass.services.async_call.assert_any_call(
        "script", "alarm_2", service_data={"variables": {"message": "for script only"}}
    )
    mock_hass.services.async_call.assert_any_call("switch", "turn_on", service_data={"entity_id": "switch.bell_1"})
    mock_hass.services.async_call.assert_any_call(
        "siren", "turn_on", service_data={"entity_id": "siren.lobby", "data": {"duration": 10, "volume_level": 1}}
    )


async def test_deliver_alias(mock_hass) -> None:
    """Test on_notify_chime"""
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
    envelope = Envelope(
        "", Notification(context, message="for script only"), targets=["switch.bell_1", "script.alarm_2", "siren.lobby"]
    )
    await uut.deliver(envelope)
    assert envelope.skipped == 0
    assert envelope.errored == 0
    assert envelope.delivered == 1
    assert len(envelope.calls) == 6

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


async def test_deliver_to_group(mock_hass, superconfig) -> None:
    """Test on_notify_chime"""
    groups = {
        "group.alexa": MockGroup(["media_player.alexa_1", "media_player.alexa_2"]),
        "group.chime": MockGroup(["switch.bell_1"]),
    }

    mock_hass.states.get.side_effect = lambda v: groups.get(v)
    uut = ChimeDeliveryMethod(
        mock_hass,
        superconfig,
        {
            "chimes": {
                CONF_METHOD: METHOD_CHIME,
                CONF_DEFAULT: True,
                CONF_DATA: {"chime_tune": "dive_dive_dive"},
            }
        },
    )
    await uut.initialize()
    await uut.deliver(Envelope("chimes", Notification(superconfig), targets=["group.alexa", "group.chime", "script.siren_2"]))
    mock_hass.services.async_call.assert_any_call(
        "script", "siren_2", service_data={"variables": {"chime_tune": "dive_dive_dive"}}
    )
    mock_hass.services.async_call.assert_any_call("switch", "turn_on", service_data={"entity_id": "switch.bell_1"})
    mock_hass.services.async_call.assert_any_call(
        "media_player",
        "play_media",
        service_data={"entity_id": "media_player.alexa_1", "media_content_type": "sound", "media_content_id": "dive_dive_dive"},
    )
