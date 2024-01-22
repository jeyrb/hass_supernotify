from unittest.mock import Mock
from homeassistant.components.notify.const import ATTR_MESSAGE, ATTR_TITLE

from custom_components.supernotify import ATTR_NOTIFICATION_ID
from custom_components.supernotify.configuration import SupernotificationConfiguration
from custom_components.supernotify.methods.persistent import PersistentDeliveryMethod
from custom_components.supernotify.notification import Notification

async def test_deliver() -> None:
    """Test on_notify_persistent"""
    hass = Mock()
    context = SupernotificationConfiguration()
    uut = PersistentDeliveryMethod(
        hass, context, {})
    await uut.initialize()
    await uut.deliver(Notification(context,"hello there", title="testing"))
    hass.services.async_call.assert_called_with("notify", "persistent_notification",
                                                service_data={
                                                    ATTR_TITLE: "testing",
                                                    ATTR_MESSAGE: "hello there",
                                                    ATTR_NOTIFICATION_ID: None})
