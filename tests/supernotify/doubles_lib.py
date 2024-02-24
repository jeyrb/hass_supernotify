import homeassistant
from homeassistant.core import callback

from custom_components.supernotify import CONF_METHOD, CONF_PERSON
from custom_components.supernotify.delivery_method import DeliveryMethod
from custom_components.supernotify.notification import Envelope
from homeassistant.components import image
from homeassistant.util import dt as dt_util


class DummyDeliveryMethod(DeliveryMethod):
    method = "dummy"

    def __init__(self, hass, context, deliveries=None):
        deliveries = deliveries or {"dummy": {CONF_METHOD: "dummy"}}
        super().__init__(hass, context, deliveries)
        self.test_calls = []

    def validate_service(self, service):
        return service is None

    def recipient_target(self, recipient):
        return [recipient.get(CONF_PERSON).replace("person.", "dummy.")] if recipient else []

    async def _delivery_impl(self, envelope: Envelope) -> None:
        self.test_calls.append(envelope)


class BrokenDeliveryMethod(DeliveryMethod):
    method = "broken"

    def validate_service(self, service):
        return True

    async def _delivery_impl(self, envelope: Envelope) -> None:
        raise EnvironmentError("a self-inflicted error has occurred")


class MockService(homeassistant.components.notify.BaseNotificationService):
    """A test class for notification services."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls = []

    @callback
    async def async_send_message(self, message="", title=None, target=None, **kwargs):
        self.calls.append([message, title, target, kwargs])


class MockImageEntity(image.ImageEntity):

    _attr_name = "Test"

    def __init__(self, filename):
        self.bytes = open(filename, "rb").read()

    async def async_added_to_hass(self):
        self._attr_image_last_updated = dt_util.utcnow()

    async def async_image(self) -> bytes | None:
        return self.bytes
