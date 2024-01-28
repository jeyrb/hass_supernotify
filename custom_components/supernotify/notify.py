import logging

from homeassistant.components.notify import (
    BaseNotificationService,
)
from homeassistant.const import (
    CONF_CONDITION,
)
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import condition
from homeassistant.helpers.reload import async_setup_reload_service
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType


from . import (
    ATTR_DATA,
    ATTR_DELIVERY_PRIORITY,
    ATTR_DELIVERY_SCENARIOS,
    CONF_ACTIONS,
    CONF_CAMERAS,
    CONF_DELIVERY,
    CONF_LINKS,
    CONF_MEDIA_PATH,
    CONF_METHODS,
    CONF_OVERRIDES,
    CONF_RECIPIENTS,
    CONF_SCENARIOS,
    CONF_TEMPLATE_PATH,
    DOMAIN,
    PLATFORM_SCHEMA,
    PLATFORMS,
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
            CONF_MEDIA_PATH: config.get(CONF_MEDIA_PATH),
            CONF_RECIPIENTS: config.get(CONF_RECIPIENTS, ()),
            CONF_ACTIONS: config.get(CONF_ACTIONS, {}),
            CONF_SCENARIOS: config.get(CONF_SCENARIOS, {}),
            CONF_OVERRIDES: config.get(CONF_OVERRIDES, {}),
            CONF_METHODS: config.get(CONF_METHODS, {}),
            CONF_CAMERAS: config.get(CONF_CAMERAS, {})
        },
    )
    hass.states.async_set(".".join((DOMAIN, ATTR_DELIVERY_PRIORITY)), "", {})
    hass.states.async_set(".".join((DOMAIN, ATTR_DELIVERY_SCENARIOS)), [], {})

    await async_setup_reload_service(hass, DOMAIN, PLATFORMS)
    service = SuperNotificationService(
        hass,
        deliveries=config[CONF_DELIVERY],
        template_path=config[CONF_TEMPLATE_PATH],
        media_path=config[CONF_MEDIA_PATH],
        recipients=config[CONF_RECIPIENTS],
        mobile_actions=config[CONF_ACTIONS],
        scenarios=config[CONF_SCENARIOS],
        links=config[CONF_LINKS],
        overrides=config[CONF_OVERRIDES],
        method_defaults=config[CONF_METHODS],
        cameras=config[CONF_CAMERAS]
    )
    await service.initialize()

    def supplemental_service_enquire_deliveries_by_scenario(call: ServiceCall) -> [str]:
        return service.enquire_deliveries_by_scenario()
    
    def supplemental_service_enquire_last_notification(call: ServiceCall) -> dict:
        return service.last_notification.__dict__ if service.last_notification else None
    
    async def supplemental_service_enquire_active_scenarios(call: ServiceCall) -> dict:
        return service.enquire_active_scenarios()
    
    hass.services.async_register(
        DOMAIN,
        "enquire_deliveries_by_scenario",
        supplemental_service_enquire_deliveries_by_scenario,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        "enquire_last_notification",
        supplemental_service_enquire_last_notification,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        "enquire_active_scenarios",
        supplemental_service_enquire_active_scenarios,
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
        media_path=None,
        recipients=(),
        mobile_actions=None,
        scenarios=None,
        links=(),
        overrides=None,
        method_defaults={},
        cameras=None
    ):
        """Initialize the service."""
        self.hass = hass
        self.last_notification = None
        self.context = SupernotificationConfiguration(
            hass,
            deliveries,
            links,
            recipients,
            mobile_actions,
            template_path,
            media_path,
            overrides,
            scenarios,
            method_defaults,
            cameras)

    async def initialize(self):
        await self.context.initialize()
        await self.context.register_delivery_methods(METHODS)

    async def async_send_message(self, message="", title=None, target=None, **kwargs):
        """Send a message via chosen method."""
        data = kwargs.get(ATTR_DATA, {})
        _LOGGER.debug("Message: %s, target: %s, data: %s",
                      message, target, data)

        notification = Notification(
            self.context, message, title, target, data)
        await notification.initialize()
        self.setup_condition_inputs(
            ATTR_DELIVERY_PRIORITY, notification.priority)
        self.setup_condition_inputs(
            ATTR_DELIVERY_SCENARIOS, notification.requested_scenarios
        )

        stats_delivieries = stats_errors = 0

        for delivery in notification.selected_delivery_names:
            delivered, errored = await self.call_method(notification, delivery)
            stats_delivieries += delivered
            stats_errors += errored

        if stats_delivieries == 0 and stats_errors == 0:
            for delivery in self.context.fallback_by_default:
                if delivery not in notification.selected_delivery_names:
                    delivered, errored = await self.call_method(
                        notification, delivery
                    )
                    stats_delivieries += delivered
                    stats_errors += errored

        if stats_delivieries == 0 and stats_errors > 0:
            for delivery in self.context.fallback_on_error:
                if delivery not in notification.selected_delivery_names:
                    delivered, errored = await self.call_method(
                        notification, delivery
                    )
                    stats_delivieries += delivered
                    stats_errors += errored
                
        self.last_notification = notification

        _LOGGER.debug(
            "SUPERNOTIFY %s deliveries, %s errors", stats_delivieries, stats_errors
        )

    async def call_method(self, notification, delivery):
        try:
            delivered = await self.context.delivery_method(delivery).deliver(notification, delivery=delivery)
            return (1 if delivered else 0, 0)
        except Exception as e:
            _LOGGER.warning(
                "SUPERNOTIFY Failed to notify using %s: %s", delivery, e
            )
            _LOGGER.debug(
                "SUPERNOTIFY %s delivery failure", delivery, exc_info=True
            )
            return (0, 1)

    def setup_condition_inputs(self, field, value):
        self.hass.states.async_set("%s.%s" % (DOMAIN, field), value)

    def enquire_deliveries_by_scenario(self):
        return self.context.delivery_by_scenario
    
    async def enquire_active_scenarios(self):
        scenarios = []
        for scenario in self.context.scenarios.values():
            if await scenario.evaluate():
                scenarios.append(scenario.name)
        return scenarios
