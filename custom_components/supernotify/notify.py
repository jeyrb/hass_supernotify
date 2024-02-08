import logging

from cachetools import TTLCache
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
    ATTR_DUPE_POLICY_MTSLP,
    ATTR_DUPE_POLICY_NONE,
    CONF_ACTIONS,
    CONF_CAMERAS,
    CONF_DELIVERY,
    CONF_DUPE_CHECK,
    CONF_DUPE_POLICY,
    CONF_LINKS,
    CONF_MEDIA_PATH,
    CONF_METHODS,
    CONF_RECIPIENTS,
    CONF_SCENARIOS,
    CONF_SIZE,
    CONF_TEMPLATE_PATH,
    CONF_TTL,
    DOMAIN,
    PLATFORM_SCHEMA,
    PLATFORMS,
    PRIORITY_VALUES,
)
from .configuration import SupernotificationConfiguration
from .methods.alexa_media_player import AlexaMediaPlayerDeliveryMethod
from .methods.chime import ChimeDeliveryMethod
from .methods.email import EmailDeliveryMethod
from .methods.generic import GenericDeliveryMethod
from .methods.media_player_image import MediaPlayerImageDeliveryMethod
from .methods.mobile_push import MobilePushDeliveryMethod
from .methods.persistent import PersistentDeliveryMethod
from .methods.sms import SMSDeliveryMethod
from .notification import Notification

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
            CONF_METHODS: config.get(CONF_METHODS, {}),
            CONF_CAMERAS: config.get(CONF_CAMERAS, {}),
            CONF_DUPE_CHECK: config.get(CONF_DUPE_CHECK, {}),

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
        method_defaults=config[CONF_METHODS],
        cameras=config[CONF_CAMERAS],
        dupe_check=config[CONF_DUPE_CHECK]
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
        method_defaults={},
        cameras=None,
        dupe_check={}
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
            scenarios,
            method_defaults,
            cameras)
        self.dupe_check_config = dupe_check
        self.notification_cache = TTLCache(
            maxsize=dupe_check.get(CONF_SIZE, 100),
            ttl=dupe_check.get(CONF_TTL, 120))

    async def initialize(self):
        await self.context.initialize()
        await self.context.register_delivery_methods(METHODS)

    def dupe_check(self, notification):
        policy = self.dupe_check_config.get(CONF_DUPE_POLICY, ATTR_DUPE_POLICY_MTSLP)
        if policy == ATTR_DUPE_POLICY_NONE:
            return False
        notification_hash = hash((notification.message, notification.title))
        if notification.priority in PRIORITY_VALUES:
            same_or_lesser_priority = PRIORITY_VALUES[PRIORITY_VALUES.index(
                notification.priority)-1]
        else:
            same_or_lesser_priority = [notification.priority]
        dupe = False
        if any((notification_hash, p) in self.notification_cache for p in same_or_lesser_priority):
            _LOGGER.debug("SUPERNOTIFY Detected dupe notification")
            dupe = True
        self.notification_cache[(notification_hash, notification.priority)] = notification.id
        return dupe

    async def async_send_message(self, message="", title=None, target=None, **kwargs):
        """Send a message via chosen method."""
        data = kwargs.get(ATTR_DATA, {})
        _LOGGER.debug("Message: %s, target: %s, data: %s",
                      message, target, data)

        notification = Notification(
            self.context, message, title, target, data)
        await notification.initialize()
        if self.dupe_check(notification):
            _LOGGER.info("SUPERNOTIFY Suppressing dupe notification (%s)", notification.id)
            return
        self.setup_condition_inputs(
            ATTR_DELIVERY_PRIORITY, notification.priority)
        self.setup_condition_inputs(
            ATTR_DELIVERY_SCENARIOS, notification.requested_scenarios
        )

        for delivery in notification.selected_delivery_names:
            await self.call_method(notification, delivery)

        if notification.delivered == 0 and notification.errored == 0:
            for delivery in self.context.fallback_by_default:
                if delivery not in notification.selected_delivery_names:
                    await self.call_method(notification, delivery)

        if notification.delivered == 0 and notification.errored > 0:
            for delivery in self.context.fallback_on_error:
                if delivery not in notification.selected_delivery_names:
                    await self.call_method(notification, delivery)

        self.last_notification = notification

        _LOGGER.debug(
            "SUPERNOTIFY %s deliveries, %s errors, %s skipped", notification.delivered,
            notification.errored,
            notification.skipped
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
