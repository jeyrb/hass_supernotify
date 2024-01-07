from unittest.mock import Mock
from homeassistant.components.notify.const import ATTR_MESSAGE, ATTR_TITLE

from homeassistant.components.supernotify import ATTR_NOTIFICATION_ID, CONF_MOBILE, CONF_PERSON, CONF_PHONE_NUMBER, METHOD_SMS
from homeassistant.components.supernotify.common import SuperNotificationContext
from homeassistant.components.supernotify.methods.persistent import PersistentDeliveryMethod
from homeassistant.const import CONF_DEFAULT, CONF_METHOD, CONF_SERVICE


async def test_deliver() -> None:
    """Test on_notify_persistent"""
    hass = Mock()
    context = SuperNotificationContext()
    uut = PersistentDeliveryMethod(
        hass, context, {})

    await uut.deliver("hello there", title="testing")
    hass.services.call.assert_called_with("notify", "persistent_notification",
                                          service_data={
                                              ATTR_TITLE: "testing",
                                              ATTR_MESSAGE: "hello there",
                                              ATTR_NOTIFICATION_ID: None})