from unittest.mock import Mock

from homeassistant.components.notify.const import ATTR_DATA, ATTR_MESSAGE, ATTR_TARGET, ATTR_TITLE
from custom_components.supernotify import CONF_DATA, CONF_DELIVERY, METHOD_GENERIC
from custom_components.supernotify.configuration import SupernotificationConfiguration
from custom_components.supernotify.methods.generic import GenericDeliveryMethod
from homeassistant.const import CONF_DEFAULT, CONF_METHOD, CONF_SERVICE, CONF_NAME
from custom_components.supernotify.notification import Notification
from custom_components.supernotify.envelope import Envelope


async def test_deliver(mock_hass) -> None:
    context = SupernotificationConfiguration()
    uut = GenericDeliveryMethod(
        mock_hass, context, {"teleport": {CONF_METHOD: METHOD_GENERIC,
                                     CONF_NAME: "teleport",
                                     CONF_SERVICE: "notify.teleportation",
                                     CONF_DEFAULT: True}})
    await uut.initialize()
    await uut.deliver(Envelope("teleport",Notification(context, message="hello there",
                                   title="testing",
                                   service_data={
                                       CONF_DELIVERY: {
                                           "teleport": {
                                               CONF_DATA: {"cuteness": "very"}
                                           }
                                       }
                                   }),targets=["weird_generic_1",
                                           "weird_generic_2"]))
    mock_hass.services.async_call.assert_called_with("notify", "teleportation",
                                                service_data={
                                                    ATTR_TITLE:   "testing",
                                                    ATTR_MESSAGE: "hello there",
                                                    ATTR_DATA:    {"cuteness": "very"},
                                                    ATTR_TARGET:  [
                                                        "weird_generic_1", "weird_generic_2"]
                                                })


async def test_not_notify_deliver(mock_hass) -> None:
    context = SupernotificationConfiguration()
    uut = GenericDeliveryMethod(
        mock_hass, context, {"broker": {CONF_METHOD: METHOD_GENERIC,
                                   CONF_NAME: "broker",
                                   CONF_SERVICE: "mqtt.publish",
                                   CONF_DEFAULT: True}})
    await uut.initialize()
    await uut.deliver(Envelope("broker",Notification(context, message="hello there",
                                   title="testing",
                                   service_data={
                                       CONF_DELIVERY: {
                                           "broker": {
                                               CONF_DATA: {
                                                   "topic": "testing/123", "payload": "boo"}
                                           }
                                       }
                                   }),targets=["weird_generic_1",
                                           "weird_generic_2"]))
    mock_hass.services.async_call.assert_called_with("mqtt", "publish",
                                                service_data={
                                                    "topic": "testing/123",
                                                    "payload": "boo"}
                                                )
