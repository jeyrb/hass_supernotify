import logging

from homeassistant.const import CONF_SERVICE

from custom_components.supernotify import ATTR_NOTIFICATION_ID, METHOD_PERSISTENT
from custom_components.supernotify.delivery_method import DeliveryMethod

_LOGGER = logging.getLogger(__name__)


class PersistentDeliveryMethod(DeliveryMethod):
    method = METHOD_PERSISTENT

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate_service(self, service):
        return service is None

    async def _delivery_impl(self,
                             notification,
                             delivery,
                             data=None,
                             **kwargs) -> bool:
        config = self.context.deliveries.get(
            delivery) or self.default_delivery or {}
        data = data or {}

        notification_id = data.get(
            ATTR_NOTIFICATION_ID, config.get(ATTR_NOTIFICATION_ID))
        service_data = notification.core_service_data(delivery)
        service_data["notification_id"]=notification_id
        
        return await self.call_service(config.get(CONF_SERVICE, "notify.persistent_notification"), service_data)
