
from unittest.mock import Mock

from homeassistant.const import (
    CONF_SERVICE, CONF_NAME
)
from homeassistant.core import HomeAssistant

from custom_components.supernotify import (
    CONF_METHOD,
    CONF_SELECTION,
    CONF_TARGET,
    METHOD_ALEXA,
    METHOD_CHIME,
    METHOD_EMAIL,
    METHOD_GENERIC,
    METHOD_PERSISTENT,
    METHOD_SMS,
    SELECTION_BY_SCENARIO,
)
from custom_components.supernotify.methods.generic import GenericDeliveryMethod

DELIVERY = {
    "email": {CONF_METHOD: METHOD_EMAIL, CONF_SERVICE: "notify.smtp"},
    "text": {CONF_METHOD: METHOD_SMS, CONF_SERVICE: "notify.sms"},
    "chime": {CONF_METHOD: METHOD_CHIME, "entities": ["switch.bell_1", "script.siren_2"]},
    "alexa": {CONF_METHOD: METHOD_ALEXA, CONF_SERVICE: "notify.alexa"},
    "chat": {CONF_METHOD: METHOD_GENERIC, CONF_SERVICE: "notify.my_chat_server"},
    "persistent": {CONF_METHOD: METHOD_PERSISTENT, CONF_SELECTION: SELECTION_BY_SCENARIO}
}


async def test_simple_create(hass: HomeAssistant) -> None:
    context = Mock()
    context.method_defaults = {}
    uut = GenericDeliveryMethod(hass, context, DELIVERY)
    valid_deliveries = await uut.initialize()
    assert valid_deliveries == {
        d: dc for d, dc in DELIVERY.items() if dc[CONF_METHOD] == METHOD_GENERIC}
    assert uut.default_delivery is None


async def test_method_default_used_for_default_delivery(hass: HomeAssistant) -> None:
    context = Mock()
    context.method_defaults = {
        METHOD_GENERIC: {CONF_SERVICE: "notify.slackity"}}
    uut = GenericDeliveryMethod(hass, context, DELIVERY)
    valid_deliveries = await uut.initialize()
    assert valid_deliveries == {
        d: dc for d, dc in DELIVERY.items() if dc[CONF_METHOD] == METHOD_GENERIC}
    assert uut.default_delivery == {CONF_SERVICE: "notify.slackity"}


async def test_method_defaults_used_for_missing_service(hass: HomeAssistant) -> None:
    context = Mock()
    context.method_defaults = {
        METHOD_GENERIC: {CONF_SERVICE: "notify.slackity"}}
    delivery = {"chatty": {CONF_METHOD: METHOD_GENERIC,
                           CONF_TARGET: ["chan1,chan2"]}}
    uut = GenericDeliveryMethod(hass, context, delivery)
    valid_deliveries = await uut.initialize()
    assert valid_deliveries == {"chatty": {CONF_METHOD: METHOD_GENERIC,
                                           CONF_NAME: "chatty",
                                           CONF_SERVICE: "notify.slackity",
                                           CONF_TARGET: ["chan1,chan2"]}}
