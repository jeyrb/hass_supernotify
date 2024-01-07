from unittest.mock import Mock

from homeassistant.components.supernotify import CONF_PERSON, METHOD_EMAIL
from homeassistant.components.supernotify.common import SuperNotificationContext
from homeassistant.components.supernotify.methods.email import EmailDeliveryMethod
from homeassistant.const import CONF_DEFAULT, CONF_EMAIL, CONF_METHOD, CONF_SERVICE


async def test_deliver() -> None:
    """Test on_notify_email."""
    hass = Mock()
    context = SuperNotificationContext(recipients=[
        {CONF_PERSON: "person.tester1", CONF_EMAIL: "tester1@assert.com"}])

    uut = EmailDeliveryMethod(
        hass, context, {"default": {CONF_METHOD: METHOD_EMAIL, CONF_SERVICE: "notify.smtp", CONF_DEFAULT: True }})

    await uut.deliver("hello there", title="testing")
    hass.services.call.assert_called_with("notify", "smtp",
                                          service_data={
                                              "target": ["tester1@assert.com"],
                                              "title": "testing", "message": "hello there"})
    hass.reset_mock()
    await uut.deliver("hello there", title="testing",target=['tester9@assert.com'])
    hass.services.call.assert_called_with("notify", "smtp",
                                          service_data={
                                              "target": ["tester9@assert.com"],
                                              "title": "testing", "message": "hello there"})