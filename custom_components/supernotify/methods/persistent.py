import logging

from homeassistant.const import CONF_SERVICE

from custom_components.supernotify import ATTR_NOTIFICATION_ID, METHOD_PERSISTENT
from custom_components.supernotify.delivery_method import DeliveryMethod
from custom_components.supernotify.notification import Envelope

_LOGGER = logging.getLogger(__name__)


class PersistentDeliveryMethod(DeliveryMethod):
    method = METHOD_PERSISTENT

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate_service(self, service):
        return service is None

    async def _delivery_impl(self, envelope: Envelope) -> None:
        config = self.context.deliveries.get(
            envelope.delivery_name) or self.default_delivery or {}
        data = envelope.data or {}

        notification_id = data.get(
            ATTR_NOTIFICATION_ID, config.get(ATTR_NOTIFICATION_ID))
        service_data = envelope.core_service_data()
        service_data["notification_id"]=notification_id
        
        if await self.call_service(config.get(CONF_SERVICE, "notify.persistent_notification"), service_data):
            envelope.delivered = 1
