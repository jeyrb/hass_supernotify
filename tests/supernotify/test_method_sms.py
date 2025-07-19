from homeassistant.const import CONF_DEFAULT, CONF_METHOD

from custom_components.supernotify import CONF_ACTION, CONF_PERSON, CONF_PHONE_NUMBER, METHOD_SMS
from custom_components.supernotify.configuration import Context
from custom_components.supernotify.envelope import Envelope
from custom_components.supernotify.methods.sms import SMSDeliveryMethod
from custom_components.supernotify.notification import Notification


async def test_deliver(mock_hass) -> None:
    """Test on_notify_email."""
    context = Context(recipients=[{CONF_PERSON: "person.tester1", CONF_PHONE_NUMBER: "+447979123456"}])
    await context.initialize()
    uut = SMSDeliveryMethod(
        mock_hass, context, {"default": {CONF_METHOD: METHOD_SMS, CONF_ACTION: "notify.smsify", CONF_DEFAULT: True}}
    )
    await uut.initialize()
    await uut.deliver(
        Envelope("smsify", Notification(context, message="hello there", title="testing"), targets=["+447979123456"])
    )
    mock_hass.services.async_call.assert_called_with(
        "notify", "smsify", service_data={"target": ["+447979123456"], "message": "testing hello there"}
    )
    mock_hass.reset_mock()
    await uut.deliver(
        Envelope("smsify", Notification(context, message="explicit target", title="testing"), targets=["+19876123456"])
    )
    mock_hass.services.async_call.assert_called_with(
        "notify", "smsify", service_data={"target": ["+19876123456"], "message": "testing explicit target"}
    )
