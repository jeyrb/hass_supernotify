from unittest.mock import Mock

from custom_components.supernotify.common import SuperNotificationContext
from custom_components.supernotify.methods.mobile_push import (
    MobilePushDeliveryMethod,
)


async def test_on_notify_mobile_push_with_explicit_target() -> None:
    """Test on_notify_mobile_push."""
    hass = Mock()
    context = SuperNotificationContext()

    uut = MobilePushDeliveryMethod(hass, context, {})
    await uut.deliver(title="testing", message="hello there", target=["mobile_app_new_iphone"])
    hass.services.async_call.assert_called_with("notify", "mobile_app_new_iphone",
                                                service_data={"title": "testing",
                                                              "message": "hello there",
                                                              "data": {"actions": [],
                                                                       "push": {"interruption-level": "active"},
                                                                       "group": "general-appd"}})


async def test_on_notify_mobile_push_with_person_derived_targets() -> None:
    """Test on_notify_mobile_push."""
    hass = Mock()
    context = SuperNotificationContext(recipients=[{"person": "person.test_user",
                                                    "mobile_devices": [
                                                        {"notify_service": "mobile_app_test_user_iphone"}
                                                    ]
                                                    }])

    uut = MobilePushDeliveryMethod(hass, context, {})
    await uut.deliver(title="testing", message="hello there")
    hass.services.async_call.assert_called_with("notify", "mobile_app_test_user_iphone",
                                                service_data={"title": "testing",
                                                              "message": "hello there",
                                                              "data": {"actions": [],
                                                                       "push": {"interruption-level": "active"},
                                                                       "group": "general-appd"}})