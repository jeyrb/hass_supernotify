from custom_components.supernotify import CONF_METHOD, CONF_PERSON
from custom_components.supernotify.delivery_method import DeliveryMethod


class DummyDeliveryMethod(DeliveryMethod):
    method = "dummy"

    def __init__(self, hass, context, deliveries=None):
        deliveries = deliveries or {"dummy":{CONF_METHOD:"dummy"}}
        super().__init__( hass, context, deliveries)
        self.test_calls = []

    def validate_service(self, service):
        return service is None

    def recipient_target(self, recipient):
        return [recipient.get(CONF_PERSON).replace('person.', 'dummy.')] if recipient else []

    async def _delivery_impl(self, message, title, targets, priority,
                             scenarios, data, config) -> bool:
        self.test_calls.append([message, title, targets, priority,
                                scenarios, data, config])
        return True
