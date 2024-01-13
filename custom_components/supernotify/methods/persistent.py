import logging

from homeassistant.const import CONF_SERVICE

from custom_components.supernotify import ATTR_NOTIFICATION_ID, METHOD_PERSISTENT
from custom_components.supernotify.common import DeliveryMethod

_LOGGER = logging.getLogger(__name__)


class PersistentDeliveryMethod(DeliveryMethod):
    def __init__(self, *args, **kwargs):
        super().__init__(METHOD_PERSISTENT, False, *args, **kwargs)

    async def _delivery_impl(self,
                             title=None,
                             message=None,
                             config=None,
                             data=None,
                             **kwargs):
        config = config or {}
        data = data or {}

        notification_id = data.get(
            ATTR_NOTIFICATION_ID, config.get(ATTR_NOTIFICATION_ID))
        service_data = {
            "title": title,
            "message": message,
            "notification_id": notification_id
        }
        try:
            domain, service = config.get(
                CONF_SERVICE, "notify.persistent_notification").split(".", 1)
            await self.hass.services.async_call(
                domain, service, service_data=service_data)
        except Exception as e:
            _LOGGER.error(
                "Failed to notify via persistent notification (m=%s): %s", message, e)
