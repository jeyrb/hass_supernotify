from unittest.mock import Mock

from homeassistant.components.supernotify import CONF_MOBILE, CONF_PERSON, CONF_PHONE_NUMBER, METHOD_SMS
from homeassistant.components.supernotify.common import SuperNotificationContext
from homeassistant.components.supernotify.methods.sms import SMSDeliveryMethod
from homeassistant.const import CONF_DEFAULT, CONF_METHOD, CONF_SERVICE


async def test_deliver() -> None:
    """Test on_notify_email."""
    hass = Mock()
    context = SuperNotificationContext(recipients=[
        {CONF_PERSON: "person.tester1", CONF_PHONE_NUMBER:"+447979123456"}])

    uut = SMSDeliveryMethod(
        hass, context, {"default": {CONF_METHOD: METHOD_SMS, CONF_SERVICE: "notify.smsify", CONF_DEFAULT: True }})

    uut.deliver("hello there", title="testing")
    hass.services.call.assert_called_with("notify", "smsify",
                                          service_data={
                                              "target": ["+447979123456"],
                                              "message": "testing hello there"})
    hass.reset_mock()
    uut.deliver("explicit target", title="testing", target=["+19876123456"])
    hass.services.call.assert_called_with("notify", "smsify",
                                          service_data={
                                              "target": ["+19876123456"],
                                              "message": "testing explicit target"})
    
    