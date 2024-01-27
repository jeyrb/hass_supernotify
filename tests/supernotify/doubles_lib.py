import homeassistant
from homeassistant.core import callback

from custom_components.supernotify import CONF_METHOD, CONF_PERSON
from custom_components.supernotify.delivery_method import DeliveryMethod


class DummyDeliveryMethod(DeliveryMethod):
    method = "dummy"

    def __init__(self, hass, context, deliveries=None):
        deliveries = deliveries or {"dummy": {CONF_METHOD: "dummy"}}
        super().__init__(hass, context, deliveries)
        self.test_calls = []

    def validate_service(self, service):
        return service is None

    def recipient_target(self, recipient):
        return [recipient.get(CONF_PERSON).replace('person.', 'dummy.')] if recipient else []

    async def _delivery_impl(self, notification, delivery, targets, data) -> bool:
        self.test_calls.append(
            [notification.message(delivery), notification.title(delivery),
             delivery, targets, data])
        return True


class MockService(homeassistant.components.notify.BaseNotificationService):
    """A test class for notification services."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls = []

    @callback
    async def async_send_message(self, message="", title=None, target=None, **kwargs):
        self.calls.append([message, title, target, kwargs])
