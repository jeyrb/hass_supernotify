from unittest.mock import Mock

from custom_components.supernotify import CONF_PERSON, CONF_PHONE_NUMBER, METHOD_SMS
from custom_components.supernotify.configuration import SupernotificationConfiguration
from custom_components.supernotify.methods.sms import SMSDeliveryMethod
from homeassistant.const import CONF_DEFAULT, CONF_METHOD, CONF_SERVICE

from custom_components.supernotify.notification import Notification


async def test_deliver() -> None:
    """Test on_notify_email."""
    hass = Mock()
    context = SupernotificationConfiguration(recipients=[
        {CONF_PERSON: "person.tester1", CONF_PHONE_NUMBER: "+447979123456"}])

    uut = SMSDeliveryMethod(
        hass, context, {"default": {CONF_METHOD: METHOD_SMS, CONF_SERVICE: "notify.smsify", CONF_DEFAULT: True}})
    await uut.initialize()
    await uut.deliver(Notification(context,message="hello there", 
                                   title="testing"))
    hass.services.async_call.assert_called_with("notify", "smsify",
                                                service_data={
                                                    "target": ["+447979123456"],
                                                    "message": "testing hello there"})
    hass.reset_mock()
    await uut.deliver(Notification(context,message="explicit target", 
                                   title="testing",
                                   target=["+19876123456"]))
    hass.services.async_call.assert_called_with("notify", "smsify",
                                                service_data={
                                                    "target": ["+19876123456"],
                                                    "message": "testing explicit target"})
