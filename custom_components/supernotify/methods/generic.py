import logging

from custom_components.supernotify import CONF_DATA, CONF_MESSAGE, CONF_NOTIFY, CONF_TITLE, METHOD_GENERIC, CONF_TARGET
from custom_components.supernotify.common import DeliveryMethod
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

        try:
            domain, service = config.get(
                CONF_SERVICE).split(".", 1)
            if domain == CONF_NOTIFY:
                service_data = {}
                if title is not None:
                    service_data[CONF_TITLE] = title
                if message is not None:
                    service_data[CONF_MESSAGE] = message
                if targets is not None:
                    service_data[CONF_TARGET] = targets
                if data is not None:
                    service_data[CONF_DATA] = data
            else:
                service_data = data
            await self.hass.services.async_call(
                domain, service, service_data=service_data)
        except Exception as e:
            _LOGGER.error(
                "Failed to notify via generic %s.%s (m=%s): %s", domain, service, message, e)
