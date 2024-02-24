from custom_components.supernotify import (
    ATTR_PRIORITY,
    CONF_PRIORITY,
    PRIORITY_CRITICAL,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
    PRIORITY_VALUES,
)

from custom_components.supernotify.configuration import SupernotificationConfiguration
from custom_components.supernotify.methods.mobile_push import (
    MobilePushDeliveryMethod,
)
from custom_components.supernotify.notification import Notification
import pytest


async def test_on_notify_mobile_push_with_media(mock_hass) -> None:
    """Test on_notify_mobile_push."""
    context = SupernotificationConfiguration()

    uut = MobilePushDeliveryMethod(mock_hass, context, {})
    await uut.deliver(
        Notification(
            context,
            message="hello there",
            target=["mobile_app_new_iphone"],
            service_data={
                "media": {
                    "camera_entity_id": "camera.porch",
                    "camera_ptz_preset": "front-door",
                    "clip_url": "http://my.home/clip.mp4",
                },
                "actions": {"action_url": "http://my.home/app1", "action_url_title": "My Camera App"},
            },
        ),
        "media_test",
    )
    mock_hass.services.async_call.assert_called_with(
        "notify",
        "mobile_app_new_iphone",
        service_data={
            "message": "hello there",
            "data": {
                "actions": [
                    {"action": "URI", "title": "My Camera App", "uri": "http://my.home/app1"},
                    {
                        "action": "silence-camera.porch",
                        "title": "Stop camera notifications for camera.porch",
                        "destructive": "true",
                    },
                ],
                "push": {"interruption-level": "active"},
                "group": "general",
                "entity_id": "camera.porch",
                "video": "http://my.home/clip.mp4",
                "url": "http://my.home/app1",
            },
        },
    )


async def test_on_notify_mobile_push_with_explicit_target(mock_hass) -> None:
    """Test on_notify_mobile_push."""
    context = SupernotificationConfiguration()

    uut = MobilePushDeliveryMethod(mock_hass, context, {})
    await uut.deliver(Notification(context, message="hello there", title="testing", target=["mobile_app_new_iphone"]))
    mock_hass.services.async_call.assert_called_with(
        "notify",
        "mobile_app_new_iphone",
        service_data={
            "title": "testing",
            "message": "hello there",
            "data": {"actions": [], "push": {"interruption-level": "active"}, "group": "general"},
        },
    )


async def test_on_notify_mobile_push_with_person_derived_targets(mock_hass) -> None:
    """Test on_notify_mobile_push."""
    context = SupernotificationConfiguration(
        recipients=[{"person": "person.test_user", "mobile_devices": [{"notify_service": "mobile_app_test_user_iphone"}]}]
    )
    await context.initialize()
    uut = MobilePushDeliveryMethod(mock_hass, context, {})
    await uut.deliver(Notification(context, message="hello there", title="testing"))
    mock_hass.services.async_call.assert_called_with(
        "notify",
        "mobile_app_test_user_iphone",
        service_data={
            "title": "testing",
            "message": "hello there",
            "data": {"actions": [], "push": {"interruption-level": "active"}, "group": "general"},
        },
    )


async def test_on_notify_mobile_push_with_critical_priority(mock_hass) -> None:
    """Test on_notify_mobile_push."""
    context = SupernotificationConfiguration(
        recipients=[{"person": "person.test_user", "mobile_devices": [{"notify_service": "mobile_app_test_user_iphone"}]}]
    )
    await context.initialize()
    uut = MobilePushDeliveryMethod(mock_hass, context, {})
    await uut.initialize()
    await uut.deliver(
        Notification(context, message="hello there", title="testing", service_data={CONF_PRIORITY: PRIORITY_CRITICAL})
    )
    mock_hass.services.async_call.assert_called_with(
        "notify",
        "mobile_app_test_user_iphone",
        service_data={
            "title": "testing",
            "message": "hello there",
            "data": {
                "actions": [],
                "push": {"interruption-level": "critical", "sound": {"name": "default", "critical": 1, "volume": 1.0}},
            },
        },
    )


@pytest.mark.parametrize("priority", PRIORITY_VALUES)
async def test_priority_interpretation(mock_hass, priority):
    priority_map = {
        PRIORITY_CRITICAL: "critical",
        PRIORITY_HIGH: "time-sensitive",
        PRIORITY_LOW: "passive",
        PRIORITY_MEDIUM: "active",
    }
    context = SupernotificationConfiguration(
        recipients=[{"person": "person.test_user", "mobile_devices": [{"notify_service": "mobile_app_test_user_iphone"}]}]
    )
    await context.initialize()
    uut = MobilePushDeliveryMethod(mock_hass, context, {})
    n = Notification(context, message="hello there", title="testing", service_data={ATTR_PRIORITY: priority})
    await uut.deliver(n)
    assert n.delivered_envelopes[0].calls[0][2]["data"]["push"]["interruption-level"] == priority_map.get(priority,"active")
