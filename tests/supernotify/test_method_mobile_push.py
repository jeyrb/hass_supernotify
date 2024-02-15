from unittest.mock import Mock
from custom_components.supernotify import CONF_PRIORITY, PRIORITY_CRITICAL

from custom_components.supernotify.configuration import SupernotificationConfiguration
from custom_components.supernotify.methods.mobile_push import (
    MobilePushDeliveryMethod,
)
from custom_components.supernotify.notification import Notification


async def test_on_notify_mobile_push_with_explicit_target() -> None:
    """Test on_notify_mobile_push."""
    hass = Mock()
    context = SupernotificationConfiguration()

    uut = MobilePushDeliveryMethod(hass, context, {})
    await uut.deliver(Notification(context, message="hello there",
                                   title="testing",
                                   target=["mobile_app_new_iphone"]
                                   ))
    hass.services.async_call.assert_called_with("notify", "mobile_app_new_iphone",
                                                service_data={"title": "testing",
                                                              "message": "hello there",
                                                              "data": {"actions": [],
                                                                       "push": {"interruption-level": "active"},
                                                                       "group": "general"}})


async def test_on_notify_mobile_push_with_person_derived_targets() -> None:
    """Test on_notify_mobile_push."""
    hass = Mock()
    context = SupernotificationConfiguration(recipients=[{"person": "person.test_user",
                                                          "mobile_devices": [
                                                              {"notify_service": "mobile_app_test_user_iphone"}
                                                          ]
                                                          }])
    await context.initialize()
    uut = MobilePushDeliveryMethod(hass, context, {})
    await uut.deliver(Notification(context, message="hello there", title="testing"))
    hass.services.async_call.assert_called_with("notify", "mobile_app_test_user_iphone",
                                                service_data={"title": "testing",
                                                              "message": "hello there",
                                                              "data": {"actions": [],
                                                                       "push": {"interruption-level": "active"},
                                                                       "group": "general"}})


async def test_on_notify_mobile_push_with_critical_priority() -> None:
    """Test on_notify_mobile_push."""
    hass = Mock()
    context = SupernotificationConfiguration(recipients=[{"person": "person.test_user",
                                                          "mobile_devices": [
                                                              {"notify_service": "mobile_app_test_user_iphone"}
                                                          ]
                                                          }])
    await context.initialize()
    uut = MobilePushDeliveryMethod(hass, context, {})
    await uut.initialize()
    await uut.deliver(Notification(context, message="hello there", title="testing", service_data={CONF_PRIORITY: PRIORITY_CRITICAL}))
    hass.services.async_call.assert_called_with("notify", "mobile_app_test_user_iphone",
                                                service_data={"title": "testing",
                                                              "message": "hello there",
                                                              "data": {"actions": [],
                                                                       "push": {"interruption-level": "critical",
                                                                                "sound": {
                                                                                    "name": "default",
                                                                                    "critical": 1,
                                                                                    "volume": 1.0}
                                                                                }
                                                                       }})
