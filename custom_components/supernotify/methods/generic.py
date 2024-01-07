import logging

from homeassistant.components.notify.const import ATTR_TARGET
from homeassistant.components.supernotify import METHOD_GENERIC
from homeassistant.components.supernotify.common import DeliveryMethod
from homeassistant.const import CONF_SERVICE

_LOGGER = logging.getLogger(__name__)


class GenericDeliveryMethod(DeliveryMethod):
    def __init__(self, *args, **kwargs):
        super().__init__(METHOD_GENERIC, True, *args, **kwargs)

    async def _delivery_impl(self,
                       title=None,
                       message=None,
                       config=None,
                       data=None,
                       targets=None,
                       **kwargs):
        config = config or {}
        data = data or {}
        targets = targets or []

        service_data = {
            "title":    title,
            "message":  message,
            "target":   targets,
            "data":     data
        }

        try:
            domain, service = config.get(
                CONF_SERVICE).split(".", 1)
            self.hass.services.call(
                domain, service, service_data=service_data)
        except Exception as e:
            _LOGGER.error(
                "Failed to notify via generic notification (m=%s): %s", message, e)
