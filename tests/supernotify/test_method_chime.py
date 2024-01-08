from unittest.mock import Mock

from custom_components.supernotify import METHOD_CHIME
from custom_components.supernotify.common import SuperNotificationContext
from custom_components.supernotify.methods.chime import ChimeDeliveryMethod
from homeassistant.const import CONF_DEFAULT, CONF_ENTITIES, CONF_METHOD


async def test_deliver() -> None:
    """Test on_notify_persistent"""
    hass = Mock()
    context = SuperNotificationContext()
    uut = ChimeDeliveryMethod(
        hass, context, {"chimes":{CONF_METHOD: METHOD_CHIME,
                                  CONF_DEFAULT: True,
                                  CONF_ENTITIES: ["switch.bell_1", "script.siren_2"]}})

    await uut.deliver()
    hass.services.async_call.assert_any_call("script", "turn_on", service_data={
                                       "target":{"entity_id": "script.siren_2"}})
    hass.services.async_call.assert_any_call("switch", "turn_on", service_data={
                                       "target":{"entity_id": "switch.bell_1"}})
