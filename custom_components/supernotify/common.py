from abc import abstractmethod
import logging

from homeassistant.components.notify import ATTR_TARGET
from homeassistant.const import CONF_DEFAULT, CONF_METHOD
from homeassistant.core import HomeAssistant

from . import CONF_OCCUPANCY, OCCUPANCY_ALL, OCCUPANCY_ALL_IN, OCCUPANCY_ALL_OUT, OCCUPANCY_ANY_IN, OCCUPANCY_ANY_OUT, OCCUPANCY_NONE, OCCUPANCY_ONLY_IN, OCCUPANCY_ONLY_OUT

_LOGGER = logging.getLogger(__name__)


class SuperNotificationContext:
    def __init__(self, hass_url, hass_name, links, recipients, mobile_actions, templates):
        self.hass_url = hass_url
        self.hass_name = hass_name
        self.links = links
        self.recipients = recipients
        self.mobile_actions = mobile_actions
        self.templates = templates


class DeliveryMethod:
    @abstractmethod
    def __init__(self,
                 method: str,
                 service_required: bool,
                 hass: HomeAssistant,
                 context: SuperNotificationContext,
                 deliveries: dict):
        self.hass = hass
        self.context = context
        self.method = method
        self.service_required = service_required
        self.default_delivery = None
        if deliveries:
            for d in deliveries.values():
                if d.get(CONF_METHOD) == method and d.get(CONF_DEFAULT):
                    self.default_delivery = d
                    break

    def deliver(self, message=None, title=None, config=None,
                target=None, data=None):
        config = config or self.default_delivery

        self._delivery_impl(message=message,
                            title=title,
                            recipients=self.select_recipients(config, target),
                            config=config)

    @abstractmethod
    def _delivery_impl(message=None, title=None, config=None):
        pass

    def select_recipients(self, delivery_config, target):
        recipients = []
        if target:
            for t in target:
                if t in self.context.recipients:
                    recipients.append(self.context.recipients[t])
                else:
                    recipients.append({ATTR_TARGET: t})
        elif delivery_config:
            recipients = self.filter_recipients(
                delivery_config.get(CONF_OCCUPANCY, OCCUPANCY_ALL))
        else:
            _LOGGER.debug("SUPERNOTIFY Neither target not recipients defined")

        return recipients

    def filter_recipients(self, occupancy):
        at_home = []
        away = []
        try:
            for r in self.context.recipients:
                tracker = self.hass.states.get(r["person"])
                if tracker is not None and tracker.state == "home":
                    at_home.append(r)
                else:
                    away.append(r)
        except Exception as e:
            _LOGGER.warning(
                "Unable to determine occupied status for %s: %s", r["person"], e)
        if occupancy == OCCUPANCY_ALL_IN:
            return self.context.recipients if len(away) == 0 else []
        elif occupancy == OCCUPANCY_ALL_OUT:
            return self.context.recipients if len(at_home) == 0 else []
        elif occupancy == OCCUPANCY_ANY_IN:
            return self.context.recipients if len(at_home) > 0 else []
        elif occupancy == OCCUPANCY_ANY_OUT:
            return self.context.recipients if len(away) > 0 else []
        elif occupancy == OCCUPANCY_ONLY_IN:
            return at_home
        elif occupancy == OCCUPANCY_ONLY_OUT:
            return away
        elif occupancy == OCCUPANCY_ALL:
            return self.context.recipients
        elif occupancy == OCCUPANCY_NONE:
            return []
        else:
            _LOGGER.warning(
                "SUPERNOTIFY Unknown occupancy tested: %s" % occupancy)
            return []
