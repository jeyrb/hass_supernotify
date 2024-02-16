from unittest.mock import Mock, AsyncMock


from custom_components.supernotify import CONF_DATA, METHOD_CHIME
from custom_components.supernotify.configuration import SupernotificationConfiguration
from custom_components.supernotify.methods.chime import ChimeDeliveryMethod
from homeassistant.const import CONF_DEFAULT, CONF_ENTITIES, CONF_METHOD, CONF_TARGET, ATTR_ENTITY_ID
from custom_components.supernotify.notification import Notification


async def test_deliver() -> None:
    """Test on_notify_chime"""
    hass = Mock()
    context = SupernotificationConfiguration()
    uut = ChimeDeliveryMethod(
        hass, context, {"chimes": {CONF_METHOD: METHOD_CHIME,
                                   CONF_DEFAULT: True,
                                   CONF_ENTITIES: ["switch.bell_1", "script.siren_2"]}})
    await uut.initialize()
    await uut.deliver(Notification(context))
    hass.services.async_call.assert_any_call(
        "script", "siren_2", service_data={"variables": {}})
    hass.services.async_call.assert_any_call("switch", "turn_on", service_data={
        "entity_id": "switch.bell_1"})


async def test_deliver_alias() -> None:
    """Test on_notify_chime"""
    hass = Mock()
    hass.services.async_call = AsyncMock()
    context = SupernotificationConfiguration(method_defaults={"chime": {
                                                              "target": ["media_player.kitchen_alexa", "media_player.hall_echo"],
                                                              "options":
                                                              {"chime_aliases": {
                                                                  "doorbell": {
                                                                      "media_player": "home/amzn_sfx_doorbell_chime_02",
                                                                      "switch": {
                                                                          "entity_id": "switch.chime_ding_dong"
                                                                      }
                                                                  }
                                                              }}}})
    uut = ChimeDeliveryMethod(
        hass, context, {"chimes": {CONF_METHOD: METHOD_CHIME,
                                   CONF_DEFAULT: True,
                                   CONF_DATA: {"chime_tune": "doorbell"}
                                   }
                        })
    await uut.initialize()
    await uut.deliver(Notification(context))
    hass.services.async_call.assert_any_call(
        "switch", "turn_on", service_data={"entity_id": "switch.chime_ding_dong"})
    hass.services.async_call.assert_any_call("media_player", "play_media", service_data={
        "entity_id": 'media_player.kitchen_alexa',
        "media_content_type": "sound",
        "media_content_id": "home/amzn_sfx_doorbell_chime_02"})


class MockGroup:
    def __init__(self, entities):
        self.attributes = {ATTR_ENTITY_ID: entities}


async def test_deliver_to_group() -> None:
    """Test on_notify_chime"""
    GROUPS = {"group.alexa": MockGroup(["media_player.alexa_1", "media_player.alexa_2"]),
              "group.chime": MockGroup(["switch.bell_1"])}
    hass = Mock()
    hass.states.get.side_effect = lambda v: GROUPS.get(v)
    context = SupernotificationConfiguration()
    uut = ChimeDeliveryMethod(
        hass, context, {"chimes": {CONF_METHOD: METHOD_CHIME,
                                   CONF_DEFAULT: True,
                                   CONF_TARGET: ["group.alexa", "group.chime", "script.siren_2"],
                                   CONF_DATA: {"chime_tune": "dive_dive_dive"}
                                   }})
    await uut.initialize()
    await uut.deliver(Notification(context))
    hass.services.async_call.assert_any_call(
        "script", "siren_2", service_data={"variables": {}})
    hass.services.async_call.assert_any_call("switch", "turn_on", service_data={
        "entity_id": "switch.bell_1"})
    hass.services.async_call.assert_any_call("media_player", "play_media",
                                             service_data={'entity_id': 'media_player.alexa_1',
                                                           'media_content_type': 'sound',
                                                           'media_content_id': "dive_dive_dive"}
                                             )
