import logging
import re

from homeassistant.components.notify.const import ATTR_DATA, ATTR_TARGET
from custom_components.supernotify import CONF_PHONE_NUMBER, METHOD_SMS
from custom_components.supernotify.delivery_method import DeliveryMethod
from homeassistant.const import CONF_SERVICE

RE_VALID_PHONE = r"^(\+\d{1,3})?\s?\(?\d{1,4}\)?[\s.-]?\d{3}[\s.-]?\d{4}$"

_LOGGER = logging.getLogger(__name__)


class SMSDeliveryMethod(DeliveryMethod):
    method = METHOD_SMS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def select_target(self, target):
        return re.fullmatch(RE_VALID_PHONE, target)

    def recipient_target(self, recipient):
        phone = recipient.get(CONF_PHONE_NUMBER)
        return [phone] if phone else []

    async def _delivery_impl(self,
                             notification,
                             delivery,
                             targets=None,
                             data=None,
                             **kwargs) -> bool:
        _LOGGER.info("SUPERNOTIFY notify_sms: %s", notification.title)
        config = notification.delivery_config.get(
            delivery) or self.default_delivery or {}
        data = data or {}
        mobile_numbers = targets or []

        combined = f"{notification.title} {notification.message}"
        service_data = {
            "message": combined[:158],
            ATTR_TARGET: mobile_numbers
        }
        if data and data.get("data"):
            service_data[ATTR_DATA] = data.get("data")
            
        return await self.call_service(config.get(CONF_SERVICE),service_data)
