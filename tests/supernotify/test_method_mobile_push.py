from typing import cast

import pytest
from homeassistant.components.notify.const import DOMAIN as NOTIFY_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from conftest import MockService
from custom_components.supernotify import (
    ATTR_PRIORITY,
    CONF_METHOD,
    CONF_PRIORITY,
    DOMAIN,
    METHOD_MOBILE_PUSH,
    PRIORITY_CRITICAL,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
    PRIORITY_VALUES,
)
from custom_components.supernotify.configuration import SupernotificationConfiguration
from custom_components.supernotify.envelope import Envelope
from custom_components.supernotify.methods.mobile_push import MobilePushDeliveryMethod
from custom_components.supernotify.notification import Notification


async def test_on_notify_mobile_push_with_media(mock_hass: HomeAssistant) -> None:
    """Test on_notify_mobile_push."""
    context = SupernotificationConfiguration()

    uut = MobilePushDeliveryMethod(mock_hass, context, {})
    await uut.deliver(
        Envelope(
            "media_test",
            Notification(
                context,
                message="hello there",
                service_data={
                    "media": {
                        "camera_entity_id": "camera.porch",
                        "camera_ptz_preset": "front-door",
                        "clip_url": "http://my.home/clip.mp4",
                    },
                    "actions": [{"action": "URI", "title": "My Camera App", "url": "http://my.home/app1"}],
                },
            ),
            targets=["mobile_app_new_iphone"],
        ),
    )
    mock_hass.services.async_call.assert_called_with(  # type: ignore
        "notify",
        "mobile_app_new_iphone",
        service_data={
            "message": "hello there",
            "data": {
                "actions": [
                    {"action": "URI", "title": "My Camera App", "url": "http://my.home/app1"},
                    {
                        "action": "SUPERNOTIFY_SNOOZE_EVERYONE_CAMERA_camera.porch",
                        "title": "Snooze camera notifications for camera.porch",
                        "behavior": "textInput",
                        "textInputButtonTitle": "Minutes to snooze",
                        "textInputPlaceholder": "60",
                    },
                ],
                "push": {"interruption-level": "active"},
                "group": "general",
                "entity_id": "camera.porch",
                "video": "http://my.home/clip.mp4",
            },
        },
    )


async def test_on_notify_mobile_push_with_explicit_target(mock_hass: HomeAssistant) -> None:
    """Test on_notify_mobile_push."""
    context = SupernotificationConfiguration()

    uut = MobilePushDeliveryMethod(mock_hass, context, {})
    await uut.deliver(
        Envelope("", Notification(context, message="hello there", title="testing"), targets=["mobile_app_new_iphone"])
    )
    mock_hass.services.async_call.assert_called_with(  # type: ignore
        "notify",
        "mobile_app_new_iphone",
        service_data={
            "title": "testing",
            "message": "hello there",
            "data": {"push": {"interruption-level": "active"}, "group": "general"},
        },
    )


async def test_on_notify_mobile_push_with_person_derived_targets(mock_hass: HomeAssistant) -> None:
    """Test on_notify_mobile_push."""
    context = SupernotificationConfiguration(
        recipients=[{"person": "person.test_user", "mobile_devices": [{"notify_service": "mobile_app_test_user_iphone"}]}]
    )
    await context.initialize()
    n = Notification(context, message="hello there", title="testing")
    uut = MobilePushDeliveryMethod(mock_hass, context, {})
    recipients = n.generate_recipients("dummy", uut)
    assert len(recipients) == 1
    assert recipients[0]["person"] == "person.test_user"
    assert recipients[0]["mobile_devices"][0]["notify_service"] == "mobile_app_test_user_iphone"


async def test_on_notify_mobile_push_with_critical_priority(mock_hass: HomeAssistant) -> None:
    """Test on_notify_mobile_push."""
    context = SupernotificationConfiguration(
        recipients=[{"person": "person.test_user", "mobile_devices": [{"notify_service": "mobile_app_test_user_iphone"}]}]
    )
    await context.initialize()
    uut = MobilePushDeliveryMethod(mock_hass, context, {})
    await uut.initialize()
    await uut.deliver(
        Envelope(
            "",
            Notification(context, message="hello there", title="testing", service_data={CONF_PRIORITY: PRIORITY_CRITICAL}),
            targets=["mobile_app_test_user_iphone"],
        )
    )
    mock_hass.services.async_call.assert_called_with(  # type: ignore
        "notify",
        "mobile_app_test_user_iphone",
        service_data={
            "title": "testing",
            "message": "hello there",
            "data": {
                "push": {"interruption-level": "critical", "sound": {"name": "default", "critical": 1, "volume": 1.0}},
            },
        },
    )


@pytest.mark.parametrize("priority", PRIORITY_VALUES)
async def test_priority_interpretation(mock_hass: HomeAssistant, superconfig, priority):
    priority_map = {
        PRIORITY_CRITICAL: "critical",
        PRIORITY_HIGH: "time-sensitive",
        PRIORITY_LOW: "passive",
        PRIORITY_MEDIUM: "active",
    }
    uut = MobilePushDeliveryMethod(mock_hass, superconfig, {})
    e = Envelope(
        "",
        Notification(superconfig, message="hello there", title="testing", service_data={ATTR_PRIORITY: priority}),
        targets=["mobile_app_test_user_iphone"],
    )
    await uut.deliver(e)
    assert e.calls[0][2]["data"]["push"]["interruption-level"] == priority_map.get(priority, "active")


INTEGRATION_CONFIG = {
    "name": DOMAIN,
    "platform": DOMAIN,
    "delivery": {
        "push": {CONF_METHOD: METHOD_MOBILE_PUSH},
    },
    "recipients": [{"person": "person.house_owner", "mobile_devices": {"notify_service": "notify.mobile_app_new_iphone"}}],
}


async def test_top_level_data_used(hass: HomeAssistant, mock_notify: MockService) -> None:
    assert await async_setup_component(hass, NOTIFY_DOMAIN, config={NOTIFY_DOMAIN: [INTEGRATION_CONFIG]})
    await hass.async_block_till_done()

    await hass.services.async_call(
        NOTIFY_DOMAIN,
        DOMAIN,
        {
            "title": "my title",
            "message": "integration ttldu",
            "data": {"priority": "low", "clickAction": "android_something", "transparency": 50},
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    notification: dict = cast(
        dict,
        await hass.services.async_call("supernotify", "enquire_last_notification", None, blocking=True, return_response=True),
    )
    assert notification is not None
    assert notification["delivered_envelopes"][0]["data"]["clickAction"] == "android_something"
