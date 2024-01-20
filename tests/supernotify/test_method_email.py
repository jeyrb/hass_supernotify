from unittest.mock import Mock

from custom_components.supernotify import CONF_PERSON, CONF_TEMPLATE, METHOD_EMAIL
from custom_components.supernotify.common import SuperNotificationContext
from custom_components.supernotify.methods.email import EmailDeliveryMethod
from homeassistant.const import CONF_DEFAULT, CONF_EMAIL, CONF_METHOD, CONF_SERVICE
from custom_components.supernotify.notification import Notification


async def test_deliver() -> None:
    """Test on_notify_email."""
    hass = Mock()
    context = SuperNotificationContext(recipients=[
        {CONF_PERSON: "person.tester1", CONF_EMAIL: "tester1@assert.com"}])

    uut = EmailDeliveryMethod(
        hass, context, {"default": {CONF_METHOD: METHOD_EMAIL, CONF_SERVICE: "notify.smtp", CONF_DEFAULT: True}})
    await uut.initialize()
    await uut.deliver(Notification(context, message="hello there", title="testing"))
    hass.services.async_call.assert_called_with("notify", "smtp",
                                                service_data={
                                                    "target": ["tester1@assert.com"],
                                                    "title": "testing",
                                                    "message": "hello there"})
    hass.reset_mock()
    await uut.deliver(Notification(context, message="hello there", title="testing",
                                   target=['tester9@assert.com']))
    hass.services.async_call.assert_called_with("notify", "smtp",
                                                service_data={
                                                    "target": ["tester9@assert.com"],
                                                    "title": "testing", "message": "hello there"})


async def test_deliver_with_template() -> None:
    hass = Mock()
    context = SuperNotificationContext(recipients=[
        {CONF_PERSON: "person.tester1", CONF_EMAIL: "tester1@assert.com"}],
        template_path="tests/supernotify/fixtures/templates")

    uut = EmailDeliveryMethod(
        hass, context, {"default": {CONF_METHOD: METHOD_EMAIL,
                                    CONF_SERVICE: "notify.smtp",
                                    CONF_TEMPLATE: "minimal_test.html.j2",
                                    CONF_DEFAULT: True}})
    await uut.initialize()
    await uut.deliver(Notification(context,
                                   message="hello there",
                                   title="testing",
                                   target=['tester9@assert.com']))
    hass.services.async_call.assert_called_with("notify", "smtp",
                                                service_data={
                                                    "target": ["tester9@assert.com"],
                                                    "title": "testing",
                                                    "message": "hello there",
                                                    'data': {'html': '<H1>testing</H1>'}})
