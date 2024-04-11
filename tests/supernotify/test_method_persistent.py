from homeassistant.components.notify.const import ATTR_MESSAGE, ATTR_TITLE

from custom_components.supernotify import ATTR_NOTIFICATION_ID
from custom_components.supernotify.configuration import SupernotificationConfiguration
from custom_components.supernotify.envelope import Envelope
from custom_components.supernotify.methods.persistent import PersistentDeliveryMethod
from custom_components.supernotify.notification import Notification


async def test_deliver(mock_hass) -> None:
    """Test on_notify_persistent"""
    context = SupernotificationConfiguration()
    uut = PersistentDeliveryMethod(mock_hass, context, {})
    await uut.initialize()
    await uut.deliver(Envelope("persistent_notification", Notification(context, "hello there", title="testing")))
    mock_hass.services.async_call.assert_called_with(
        "notify",
        "persistent_notification",
        service_data={ATTR_TITLE: "testing", ATTR_MESSAGE: "hello there", ATTR_NOTIFICATION_ID: None},
    )
