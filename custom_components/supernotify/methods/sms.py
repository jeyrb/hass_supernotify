import logging
import re

from homeassistant.components.notify.const import ATTR_DATA, ATTR_TARGET
from homeassistant.components.supernotify import CONF_PHONE_NUMBER, METHOD_SMS
from homeassistant.components.supernotify.common import DeliveryMethod
from homeassistant.const import CONF_SERVICE

RE_VALID_PHONE = r"^(\+\d{1,3})?\s?\(?\d{1,4}\)?[\s.-]?\d{3}[\s.-]?\d{4}$"

_LOGGER = logging.getLogger(__name__)

class SMSDeliveryMethod(DeliveryMethod):
    def __init__(self, *args, **kwargs):
        super().__init__( METHOD_SMS, True, *args, **kwargs)

    def _delivery_impl(self, message=None,
                       title=None,
                       config=None,
                       recipients=None,
                       data=None,
                       **kwargs):
        _LOGGER.info("SUPERNOTIFY notify_sms: %s", title)
        config = config or self.default_delivery
        data = data or {}
        recipients = recipients or []
        mobile_numbers = []
        for recipient in recipients:
            if CONF_PHONE_NUMBER in recipient:
                mobile_numbers.append(recipient.get(CONF_PHONE_NUMBER))
            elif ATTR_TARGET in recipient:
                target = recipient.get(ATTR_TARGET)
                if re.fullmatch(RE_VALID_PHONE, target):
                    mobile_numbers.append(target)

        combined = f"{title} {message}"
        service_data = {
            "message": combined[:158],
            ATTR_TARGET: mobile_numbers
        }
        if data and data.get("data"):
            service_data[ATTR_DATA] = data.get("data")
        try:
            domain, service = config.get(CONF_SERVICE).split(".", 1)
            self.hass.services.call(
                domain, service,
                service_data=service_data
            )
        except Exception as e:
            _LOGGER.error(
                "SUPERNOTIFY Failed to notify via SMS (m=%s): %s", message, e)


