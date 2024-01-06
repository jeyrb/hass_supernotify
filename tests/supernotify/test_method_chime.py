from unittest.mock import Mock

from homeassistant.components.supernotify import CONF_MOBILE, CONF_PERSON, CONF_PHONE_NUMBER, METHOD_CHIME, METHOD_SMS
from homeassistant.components.supernotify.common import SuperNotificationContext
from homeassistant.components.supernotify.methods.chime import ChimeDeliveryMethod
from homeassistant.const import CONF_DEFAULT, CONF_ENTITIES, CONF_METHOD, CONF_SERVICE


async def test_deliver() -> None:
    """Test on_notify_persistent"""
    hass = Mock()
    context = SuperNotificationContext()
    uut = ChimeDeliveryMethod(
        hass, context, {"chimes":{CONF_METHOD: METHOD_CHIME, 
                                  CONF_DEFAULT: True,
                                  CONF_ENTITIES: ["switch.bell_1", "script.siren_2"]}})

    uut.deliver()
    hass.services.call.assert_any_call("script", "turn_on", service_data={
                                       "entity_id": "script.siren_2"})
    hass.services.call.assert_any_call("switch", "turn_on", service_data={
                                       "entity_id": "switch.bell_1"})
