import logging

from homeassistant.const import CONF_SERVICE

from custom_components.supernotify import (
    CONF_DATA,
    CONF_TARGET,
    METHOD_GENERIC,
)
from custom_components.supernotify.delivery_method import DeliveryMethod
from custom_components.supernotify.notification import Envelope

_LOGGER = logging.getLogger(__name__)


class GenericDeliveryMethod(DeliveryMethod):
    method = METHOD_GENERIC

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate_service(self, service):
        return service is not None and "." in service

    async def _delivery_impl(self, envelope: Envelope) -> None:

        data = envelope.data or {}
        targets = envelope.targets or []

        qualified_service = envelope.config.get(CONF_SERVICE)
        if qualified_service.startswith("notify."):
            service_data = envelope.core_service_data()
            if targets is not None:
                service_data[CONF_TARGET] = targets
            if data is not None:
                service_data[CONF_DATA] = data
        else:
            service_data = data

        await self.call_service(envelope, qualified_service, service_data)
