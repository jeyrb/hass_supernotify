from unittest.mock import Mock

from homeassistant.components.supernotify.common import SuperNotificationContext
from homeassistant.components.supernotify.methods.apple_push import (
    ApplePushDeliveryMethod,
)


async def test_on_notify_apple_push() -> None:
    """Test on_notify_apple_push."""
    hass = Mock()
    context = SuperNotificationContext()

    uut = ApplePushDeliveryMethod(hass,context,{})
    await uut.deliver(title="testing", message="hello there",target=["mobile_app.new_iphone"])
    hass.services.call.assert_called_with("notify", "mobile_app.new_iphone",
                                          service_data={"title": "testing",
                                                        "message": "hello there",
                                                        "data": {"actions": [], "push": {"interruption-level": "active"}, "group": "general-appd"}})

