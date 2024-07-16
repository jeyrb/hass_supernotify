from pathlib import Path
from typing import Any

from homeassistant.components import image
from homeassistant.util import dt as dt_util

from custom_components.supernotify import CONF_METHOD, CONF_PERSON
from custom_components.supernotify.delivery_method import DeliveryMethod
from custom_components.supernotify.envelope import Envelope


class DummyDeliveryMethod(DeliveryMethod):
    method = "dummy"

    def __init__(self, hass, context, deliveries=None):
        deliveries = deliveries or {"dummy": {CONF_METHOD: "dummy"}}
        super().__init__(hass, context, deliveries)
        self.test_calls = []

    def validate_service(self, service):
        return service is None

    def recipient_target(self, recipient: dict[str, Any]) -> list[str]:
        if recipient:
            person: str | None = recipient.get(CONF_PERSON)
            if person:
                return [person.replace("person.", "dummy.")]
        return []

    async def deliver(self, envelope: Envelope) -> bool:
        self.test_calls.append(envelope)
        envelope.delivered = True
        return True


class BrokenDeliveryMethod(DeliveryMethod):
    method = "broken"

    def validate_service(self, service) -> bool:
        return True

    async def deliver(self, envelope: Envelope) -> bool:
        raise OSError("a self-inflicted error has occurred")


class MockImageEntity(image.ImageEntity):
    _attr_name = "Test"

    def __init__(self, filename):
        self.bytes = Path(filename).open("rb").read()

    async def async_added_to_hass(self):
        self._attr_image_last_updated = dt_util.utcnow()

    async def async_image(self) -> bytes | None:
        return self.bytes
