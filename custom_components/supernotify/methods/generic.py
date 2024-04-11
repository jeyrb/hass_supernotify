import logging

from homeassistant.const import CONF_SERVICE

from custom_components.supernotify import CONF_DATA, CONF_TARGET, METHOD_GENERIC
from custom_components.supernotify.delivery_method import DeliveryMethod
from custom_components.supernotify.envelope import Envelope

_LOGGER = logging.getLogger(__name__)


class GenericDeliveryMethod(DeliveryMethod):
    """Call any service, including non-notify ones, like switch.turn_on or mqtt.publish"""

    method = METHOD_GENERIC

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate_service(self, service) -> bool:
        if service is not None and "." in service:
            return True
        _LOGGER.warning("SUPERNOTIFY generic method must have a qualified service name, e.g. notify.foo")
        return False

    async def deliver(self, envelope: Envelope) -> bool:

        data = envelope.data or {}
        targets = envelope.targets or []
        config = self.delivery_config(envelope.delivery_name)

        qualified_service = config.get(CONF_SERVICE)
        if qualified_service and qualified_service.startswith("notify."):
            service_data = envelope.core_service_data()
            if targets is not None:
                service_data[CONF_TARGET] = targets
            if data is not None:
                service_data[CONF_DATA] = data
        else:
            service_data = data

        return await self.call_service(envelope, qualified_service, service_data)
