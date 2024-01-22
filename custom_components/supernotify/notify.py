import logging

from homeassistant.components.notify import (
    BaseNotificationService,
)
from homeassistant.const import (
    CONF_CONDITION,
    CONF_NAME,
)
import inspect
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import condition
from homeassistant.helpers.reload import async_setup_reload_service
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from custom_components.supernotify.delivery_method import DeliveryMethod

from . import (
    ATTR_DELIVERY_PRIORITY,
    ATTR_DELIVERY_SCENARIOS,
    CONF_ACTIONS,
    CONF_DELIVERY,
    CONF_LINKS,
    CONF_METHOD,
    CONF_METHODS,
    CONF_OVERRIDES,
    CONF_RECIPIENTS,
    CONF_SCENARIOS,
    CONF_TEMPLATE_PATH,
    DOMAIN,
    PLATFORM_SCHEMA,
    PLATFORMS,
    RESERVED_DELIVERY_NAMES,
)
from .configuration import SupernotificationConfiguration
from .notification import Notification
from .methods.alexa_media_player import AlexaMediaPlayerDeliveryMethod
from .methods.chime import ChimeDeliveryMethod
from .methods.email import EmailDeliveryMethod
from .methods.generic import GenericDeliveryMethod
from .methods.media_player_image import MediaPlayerImageDeliveryMethod
from .methods.mobile_push import MobilePushDeliveryMethod
from .methods.persistent import PersistentDeliveryMethod
from .methods.sms import SMSDeliveryMethod

_LOGGER = logging.getLogger(__name__)

METHODS = {
    EmailDeliveryMethod,
    SMSDeliveryMethod,
    AlexaMediaPlayerDeliveryMethod,
    MobilePushDeliveryMethod,
    MediaPlayerImageDeliveryMethod,
    ChimeDeliveryMethod,
    PersistentDeliveryMethod,
    GenericDeliveryMethod
}


async def async_get_service(
    hass: HomeAssistant,
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None = None,
):
    _ = PLATFORM_SCHEMA  # schema must be imported even if not used for HA platform detection
    for delivery in config.get(CONF_DELIVERY, {}).values():
        if CONF_CONDITION in delivery:
            await condition.async_validate_condition_config(
                hass, delivery[CONF_CONDITION]
            )

    hass.states.async_set(
        "%s.configured" % DOMAIN,
        True,
        {
            CONF_DELIVERY: config.get(CONF_DELIVERY, {}),
            CONF_LINKS: config.get(CONF_LINKS, ()),
            CONF_TEMPLATE_PATH: config.get(CONF_TEMPLATE_PATH),
            CONF_RECIPIENTS: config.get(CONF_RECIPIENTS, ()),
            CONF_ACTIONS: config.get(CONF_ACTIONS, {}),
            CONF_SCENARIOS: config.get(CONF_SCENARIOS, {}),
            CONF_OVERRIDES: config.get(CONF_OVERRIDES, {}),
            CONF_METHODS: config.get(CONF_METHODS, {})
        },
    )
    hass.states.async_set(".".join((DOMAIN, ATTR_DELIVERY_PRIORITY)), "", {})
    hass.states.async_set(".".join((DOMAIN, ATTR_DELIVERY_SCENARIOS)), [], {})

    await async_setup_reload_service(hass, DOMAIN, PLATFORMS)
    service = SuperNotificationService(
        hass,
        deliveries=config[CONF_DELIVERY],
        template_path=config[CONF_TEMPLATE_PATH],
        recipients=config[CONF_RECIPIENTS],
        mobile_actions=config[CONF_ACTIONS],
        scenarios=config[CONF_SCENARIOS],
        links=config[CONF_LINKS],
        overrides=config[CONF_OVERRIDES],
        method_defaults=config[CONF_METHODS]
    )
    await service.initialize()

    def supplemental_service_enquire_deliveries_by_scenario(call: ServiceCall) -> [str]:
        return service.enquire_deliveries_by_scenario()

    hass.services.async_register(
        DOMAIN,
        "enquire_deliveries_by_scenario",
        supplemental_service_enquire_deliveries_by_scenario,
        supports_response=SupportsResponse.ONLY,
    )

    return service


class SuperNotificationService(BaseNotificationService):
    """Implement SuperNotification service."""

    def __init__(
        self,
        hass,
        deliveries=None,
        template_path=None,
        recipients=(),
        mobile_actions=None,
        scenarios=None,
        links=(),
        overrides=None,
        method_defaults={},
    ):
        """Initialize the service."""
        self.hass = hass
        self.context = SupernotificationConfiguration(
            hass,
            hass.config.external_url or self.hass.config.internal_url,
            hass.config.location_name,
            deliveries, links,
            recipients, mobile_actions, template_path,
            overrides, scenarios, method_defaults)
        self.methods = {}
        self.valid_deliveries = {}

    async def initialize(self):
        await self.context.initialize()

        for method in METHODS:
            await self.register_delivery_method(method)

        for d, dc in self.context.deliveries.items():
            if dc.get(CONF_METHOD) not in METHODS:
                _LOGGER.info(
                    "SUPERNOTIFY Ignoring delivery %s without known method %s", d, dc.get(CONF_METHOD))

        _LOGGER.info("SUPERNOTIFY configured deliveries %s",
                     "; ".join(self.valid_deliveries.keys()))

    async def register_delivery_method(self, delivery_method: DeliveryMethod):
        """available directly for test fixtures supplying class or instance"""
        if inspect.isclass(delivery_method):
            self.methods[delivery_method.method] = delivery_method(
                self.hass, self.context, self.context.deliveries
            )
        else:
            self.methods[delivery_method.method] = delivery_method
        await self.methods[delivery_method.method].initialize()
        self.valid_deliveries.update(
            self.methods[delivery_method.method].valid_deliveries)

    async def async_send_message(self, message="", title=None, target=None, **kwargs):
        """Send a message via chosen method."""
        _LOGGER.debug("Message: %s, kwargs: %s", message, kwargs)

        notification = Notification(
            self.context, message, title, target, kwargs)
        await notification.intialize()
        self.setup_condition_inputs(
            ATTR_DELIVERY_PRIORITY, notification.priority)
        self.setup_condition_inputs(
            ATTR_DELIVERY_SCENARIOS, notification.requested_scenarios
        )

        stats_delivieries = stats_errors = 0

        for delivery, delivery_config in self.valid_deliveries.items():
            if delivery in notification.selected_delivery_names:
                delivered, errored = await self.call_method(
                    notification, delivery, delivery_config
                )
                stats_delivieries += delivered
                stats_errors += errored

        if stats_delivieries == 0 and stats_errors == 0:
            for delivery, delivery_config in self.context.fallback_by_default.items():
                delivered, errored = await self.call_method(
                    notification, delivery, delivery_config
                )
                stats_delivieries += delivered
                stats_errors += errored

        if stats_delivieries == 0 and stats_errors > 0:
            for delivery, delivery_config in self.context.fallback_on_error.items():
                delivered, errored = await self.call_method(
                    notification, delivery, delivery_config
                )
                stats_delivieries += delivered
                stats_errors += errored

        _LOGGER.debug(
            "SUPERNOTIFY %s deliveries, %s errors", stats_delivieries, stats_errors
        )

    async def call_method(self, notification, delivery, delivery_config):
        method = delivery_config[CONF_METHOD]
        # TODO consider changing delivery config to list
        delivery_config[CONF_NAME] = delivery

        try:
            await self.methods[method].deliver(notification, delivery_config)
            return (1, 0)
        except Exception as e:
            _LOGGER.warning(
                "SUPERNOTIFY Failed to %s notify using %s: %s", method, delivery, e
            )
            _LOGGER.debug(
                "SUPERNOTIFY %s %s delivery failure", method, delivery, exc_info=True
            )
            return (0, 1)

    def setup_condition_inputs(self, field, value):
        self.hass.states.async_set("%s.%s" % (DOMAIN, field), value)

    def enquire_deliveries_by_scenario(self):
        return self.context.delivery_by_scenario
