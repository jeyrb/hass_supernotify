import logging

from homeassistant.const import CONF_ACTION, CONF_TARGET  # ATTR_VARIABLES from script.const has import issues

from custom_components.supernotify import CONF_DATA, METHOD_GENERIC
from custom_components.supernotify.delivery_method import DeliveryMethod
from custom_components.supernotify.envelope import Envelope

_LOGGER = logging.getLogger(__name__)


class GenericDeliveryMethod(DeliveryMethod):
    """Call any service, including non-notify ones, like switch.turn_on or mqtt.publish"""

    method = METHOD_GENERIC

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def validate_action(self, action: str | None) -> bool:
        if action is not None and "." in action:
            return True
        _LOGGER.warning("SUPERNOTIFY generic method must have a qualified action name, e.g. notify.foo")
        return False

    async def deliver(self, envelope: Envelope) -> bool:
        data = envelope.data or {}
        targets = envelope.targets or []
        config = self.delivery_config(envelope.delivery_name)

        qualified_action = config.get(CONF_ACTION)
        if qualified_action and qualified_action.startswith("notify."):
            action_data = envelope.core_action_data()
            if targets is not None:
                action_data[CONF_TARGET] = targets
            if data is not None:
                action_data[CONF_DATA] = data
        else:
            action_data = data

        return await self.call_action(envelope, qualified_action, action_data=action_data)
