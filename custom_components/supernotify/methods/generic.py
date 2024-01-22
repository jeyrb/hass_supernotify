import logging

from custom_components.supernotify import CONF_DATA, CONF_MESSAGE, CONF_NOTIFY, CONF_TITLE, METHOD_GENERIC, CONF_TARGET
from custom_components.supernotify.delivery_method import DeliveryMethod
from homeassistant.const import CONF_SERVICE

_LOGGER = logging.getLogger(__name__)


class GenericDeliveryMethod(DeliveryMethod):
    method = METHOD_GENERIC

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate_service(self, service):
        return service is not None and "." in service

    async def _delivery_impl(self,
                             notification,
                             delivery,
                             data=None,
                             targets=None,
                             **kwargs) -> bool:
        config = notification.delivery_config.get(
            delivery) or self.default_delivery or {}
        data = data or {}
        targets = targets or []

        qualified_service = config.get(CONF_SERVICE)
        if qualified_service.startswith("notify."):
            service_data = {}
            if notification.title is not None:
                service_data[CONF_TITLE] = notification.title
            if notification.message is not None:
                service_data[CONF_MESSAGE] = notification.message
            if targets is not None:
                service_data[CONF_TARGET] = targets
            if data is not None:
                service_data[CONF_DATA] = data
        else:
            service_data = data

        return await self.call_service(qualified_service, service_data)
