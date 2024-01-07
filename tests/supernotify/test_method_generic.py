from unittest.mock import Mock

from homeassistant.components.notify.const import ATTR_DATA, ATTR_MESSAGE, ATTR_TARGET, ATTR_TITLE
from homeassistant.components.supernotify import METHOD_GENERIC
from homeassistant.components.supernotify.common import SuperNotificationContext
from homeassistant.components.supernotify.methods.generic import GenericDeliveryMethod
from homeassistant.const import CONF_DEFAULT, CONF_METHOD, CONF_SERVICE


async def test_deliver() -> None:
    """Test generic notifications"""
    hass = Mock()
    context = SuperNotificationContext()
    uut = GenericDeliveryMethod(
        hass, context, {"default": {CONF_METHOD: METHOD_GENERIC, CONF_SERVICE: "notify.teleportation", CONF_DEFAULT: True}})

    await uut.deliver("hello there", title="testing",
                target=["weird_generic_1", "weird_generic_2"],
                data={"cuteness": "very"})
    hass.services.call.assert_called_with("notify", "teleportation",
                                          service_data={
                                              ATTR_TITLE:   "testing",
                                              ATTR_MESSAGE: "hello there",
                                              ATTR_DATA:    {"cuteness": "very"},
                                              ATTR_TARGET:  [
                                                  "weird_generic_1", "weird_generic_2"]
                                          })
