import logging

from homeassistant.const import CONF_SERVICE

from custom_components.supernotify import ATTR_NOTIFICATION_ID, METHOD_PERSISTENT
from custom_components.supernotify.delivery_method import DeliveryMethod
from custom_components.supernotify.notification import Envelope

_LOGGER = logging.getLogger(__name__)


class PersistentDeliveryMethod(DeliveryMethod):
    method = METHOD_PERSISTENT
    default_service = "notify.persistent_notification"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate_service(self, service):
        return service is None

    async def deliver(self, envelope: Envelope) -> bool:
        data = envelope.data or {}
        config = self.delivery_config(envelope.delivery_name)

        notification_id = data.get(ATTR_NOTIFICATION_ID, config.get(ATTR_NOTIFICATION_ID))
        service_data = envelope.core_service_data()
        service_data["notification_id"] = notification_id

        return await self.call_service(envelope, service_data=service_data)
