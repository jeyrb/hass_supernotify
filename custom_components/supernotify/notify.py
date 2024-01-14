import logging
import os.path

from homeassistant.components.notify import (
    ATTR_DATA,
    ATTR_TARGET,
    ATTR_TITLE,
    BaseNotificationService,
)
from homeassistant.const import (
    CONF_CONDITION,
    CONF_ENABLED,
    CONF_NAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import condition, device_registry, entity_registry
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.reload import async_setup_reload_service
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import slugify

from . import (
    ATTR_DELIVERY,
    ATTR_DELIVERY_PRIORITY,
    ATTR_DELIVERY_SCENARIOS,
    ATTR_DELIVERY_SELECTION,
    ATTR_PRIORITY,
    ATTR_SCENARIOS,
    CONF_ACTIONS,
    CONF_DATA,
    CONF_DELIVERY,
    CONF_DEVICE_TRACKER,
    CONF_LINKS,
    CONF_MANUFACTURER,
    CONF_METHOD,
    CONF_MOBILE_DEVICES,
    CONF_MOBILE_DISCOVERY,
    CONF_MODEL,
    CONF_FALLBACK,
    CONF_NOTIFY_SERVICE,
    CONF_OVERRIDES,
    CONF_PERSON,
    CONF_RECIPIENTS,
    CONF_SCENARIOS,
    CONF_TEMPLATES,
    DELIVERY_SELECTION_IMPLICIT,
    DOMAIN,
    METHOD_ALEXA,
    METHOD_CHIME,
    METHOD_EMAIL,
    METHOD_GENERIC,
    METHOD_MEDIA,
    METHOD_MOBILE_PUSH,
    METHOD_PERSISTENT,
    METHOD_SMS,
    PRIORITY_MEDIUM,
    FALLBACK_DISABLED,
    FALLBACK_ON_ERROR,
    FALLBACK_ENABLED,
    PLATFORMS,
    PLATFORM_SCHEMA
)
from .common import SuperNotificationContext
from .methods.alexa_media_player import AlexaMediaPlayerDeliveryMethod
from .methods.chime import ChimeDeliveryMethod
from .methods.email import EmailDeliveryMethod
from .methods.generic import GenericDeliveryMethod
from .methods.media_player import MediaPlayerImageDeliveryMethod
from .methods.mobile_push import MobilePushDeliveryMethod
from .methods.persistent import PersistentDeliveryMethod
from .methods.sms import SMSDeliveryMethod

_LOGGER = logging.getLogger(__name__)

METHODS = {
    METHOD_EMAIL:       EmailDeliveryMethod,
    METHOD_SMS:         SMSDeliveryMethod,
    METHOD_ALEXA:       AlexaMediaPlayerDeliveryMethod,
    METHOD_MOBILE_PUSH: MobilePushDeliveryMethod,
    METHOD_MEDIA:       MediaPlayerImageDeliveryMethod,
    METHOD_CHIME:       ChimeDeliveryMethod,
    METHOD_PERSISTENT:  PersistentDeliveryMethod,
    METHOD_GENERIC:     GenericDeliveryMethod
}

async def async_get_service(hass: HomeAssistant,
                            config: ConfigType,
                            discovery_info: DiscoveryInfoType | None = None
                            ):
    
    _ = PLATFORM_SCHEMA  # schema must be imported even if not used for HA platform detection
    for delivery in config.get(CONF_DELIVERY, {}).values():
        if CONF_CONDITION in delivery:
            await condition.async_validate_condition_config(hass, delivery[CONF_CONDITION])

    hass.states.async_set(
        "%s.configured" % DOMAIN,
        True,
        {
            CONF_DELIVERY: config.get(CONF_DELIVERY, {}),
            CONF_LINKS: config.get(CONF_LINKS, ()),
            CONF_TEMPLATES: config.get(CONF_TEMPLATES),
            CONF_RECIPIENTS: config.get(CONF_RECIPIENTS, ()),
            CONF_ACTIONS: config.get(CONF_ACTIONS, {}),
            CONF_SCENARIOS: config.get(CONF_SCENARIOS, {}),
            CONF_OVERRIDES: config.get(CONF_OVERRIDES, {})
        },
    )
    hass.states.async_set(".".join((DOMAIN, ATTR_DELIVERY_PRIORITY)), "", {})
    hass.states.async_set(".".join((DOMAIN, ATTR_DELIVERY_SCENARIOS)), [], {})

    await async_setup_reload_service(hass, DOMAIN, PLATFORMS)
    return SuperNotificationService(hass,
                                    deliveries=config[CONF_DELIVERY],
                                    templates=config[CONF_TEMPLATES],
                                    recipients=config[CONF_RECIPIENTS],
                                    mobile_actions=config[CONF_ACTIONS],
                                    scenarios=config[CONF_SCENARIOS],
                                    links=config[CONF_LINKS],
                                    overrides=config[CONF_OVERRIDES]
                                    )


class SuperNotificationService(BaseNotificationService):
    """Implement SuperNotification service."""

    def __init__(self, hass,
                 deliveries=None,
                 templates=None,
                 recipients=(),
                 mobile_actions=None,
                 scenarios=None,
                 links=(),
                 overrides=None):
        """Initialize the service."""
        self.hass = hass

        hass_url = hass.config.external_url or self.hass.config.internal_url
        context = SuperNotificationContext(
            hass_url, hass.config.location_name, links, recipients, mobile_actions, templates)

        self.recipients = recipients
        self.templates = templates
        self.actions = mobile_actions or {}
        self.links = links
        scenarios = scenarios or {}
        self.overrides = overrides or {}
        deliveries = deliveries or {}

        self.people = {}
        for r in recipients:
            if r[CONF_MOBILE_DISCOVERY]:
                r[CONF_MOBILE_DEVICES].extend(
                    self.mobile_devices_for_person(r[CONF_PERSON]))
                if r[CONF_MOBILE_DEVICES]:
                    _LOGGER.info("SUPERNOTIFY Auto configured %s for mobile devices %s",
                                 r[CONF_PERSON], r[CONF_MOBILE_DEVICES])
                else:
                    _LOGGER.warning(
                        "SUPERNOTIFY Unable to find mobile devices for %s", r[CONF_PERSON])
            self.people[r[CONF_PERSON]] = r
        if templates and not os.path.exists(templates):
            _LOGGER.warning("SUPERNOTIFY template directory not found at %s",
                            templates)
            self.templates = None

        self.scenarios = {}
        for scenario, scenario_definition in scenarios.items():
            if CONF_CONDITION in scenario_definition:
                if condition.async_validate_condition_config(self.hass, scenario_definition[CONF_CONDITION]):
                    self.scenarios[scenario] = scenario_definition
            else:
                _LOGGER.warning(
                    "SUPERNOTIFY Disabling scenario %s with failed condition %s", scenario, scenario_definition)

        self.methods = {}
        self.deliveries = {}
        self.fallback_on_error = {d: dc for d, dc in deliveries.items() if dc.get(
            CONF_FALLBACK, FALLBACK_DISABLED) == FALLBACK_ON_ERROR}
        self.fallback_by_default = {d: dc for d, dc in deliveries.items() if dc.get(
            CONF_FALLBACK, FALLBACK_DISABLED) == FALLBACK_ENABLED}
        deliveries = {d: dc for d, dc in deliveries.items() if dc.get(
            CONF_FALLBACK, FALLBACK_DISABLED) == FALLBACK_DISABLED}

        for method in METHODS:
            self.methods[method] = METHODS[method](hass, context, deliveries)
            self.deliveries.update(self.methods[method].valid_deliveries)
            if self.methods[method].invalid_deliveries:
                _LOGGER.warning("SUPERNOTIFY Invalid deliveries for method %s: %s",
                                method,
                                self.methods[method].invalid_deliveries)
            if self.methods[method].disabled_deliveries:
                _LOGGER.warning("SUPERNOTIFY Disabled deliveries for method %s: %s",
                                method,
                                self.methods[method].disabled_deliveries)
        unknown_deliveries = {
            d: dc for d, dc in deliveries.items() if dc.get(CONF_METHOD) not in METHODS}
        if unknown_deliveries:
            _LOGGER.info(
                "SUPERNOTIFY Ignoring deliveries without known methods: %s", unknown_deliveries)
        _LOGGER.info("SUPERNOTIFY configured deliveries %s",
                     ";".join(self.deliveries.keys()))

    async def async_send_message(self, message="", **kwargs):
        """Send a message via chosen method."""
        _LOGGER.debug("Message: %s, kwargs: %s", message, kwargs)
        target = kwargs.get(ATTR_TARGET) or []
        if isinstance(target, str):
            target = [target]
        data = kwargs.get(ATTR_DATA) or {}
        title = kwargs.get(ATTR_TITLE)

        priority = data.get(ATTR_PRIORITY, PRIORITY_MEDIUM)
        self.setup_condition_inputs(ATTR_DELIVERY_PRIORITY, priority)
        scenarios = data.get(ATTR_SCENARIOS) or []
        scenarios.extend(await self.select_scenarios())
        self.setup_condition_inputs(ATTR_DELIVERY_SCENARIOS, scenarios)

        delivery_selection = data.get(
            ATTR_DELIVERY_SELECTION, DELIVERY_SELECTION_IMPLICIT)
        delivery_overrides = data.get(ATTR_DELIVERY, {})
        if delivery_selection == DELIVERY_SELECTION_IMPLICIT:
            deliveries = self.deliveries
        else:
            deliveries = {}
        if isinstance(delivery_overrides, list):
            delivery_overrides = {k: {} for k in delivery_selection}
        for delivery, delivery_override in delivery_overrides.items():
            if delivery_override.get(CONF_ENABLED, True) and delivery in self.deliveries:
                deliveries[delivery] = self.deliveries[delivery]

        stats_delivieries = stats_errors = 0

        for delivery, delivery_config in deliveries.items():
            delivered, errored = await self.call_method(delivery, delivery_config, message,
                                                        title, target, scenarios,
                                                        priority,
                                                        delivery_overrides.get(delivery, {}))
            stats_delivieries += delivered
            stats_errors += errored

        if stats_delivieries == 0 and stats_errors == 0:
            for delivery, delivery_config in self.fallback_by_default.items():
                delivered, errored = await self.call_method(delivery, delivery_config, message,
                                                            title, target, scenarios,
                                                            priority,
                                                            delivery_overrides.get(delivery, {}))
                stats_delivieries += delivered
                stats_errors += errored

        if stats_delivieries == 0 and stats_errors > 0:
            for delivery, delivery_config in self.fallback_on_error.items():
                delivered, errored = await self.call_method(delivery, delivery_config, message,
                                                            title, target, scenarios,
                                                            priority,
                                                            delivery_overrides.get(delivery, {}))
                stats_delivieries += delivered
                stats_errors += errored
        _LOGGER.debug("SUPERNOTIFY %s deliveries, %s errors",
                      stats_delivieries, stats_errors)

    async def call_method(self, delivery, delivery_config, message,
                          title, target, scenarios, priority, delivery_override):
        method = delivery_config[CONF_METHOD]
        # TODO consider changing delivery config to list
        delivery_config[CONF_NAME] = delivery

        try:
            await self.methods[method].deliver(message=message,
                                               title=title,
                                               target=target,
                                               scenarios=scenarios,
                                               priority=priority,
                                               data=delivery_override.get(
                                                   CONF_DATA, {}),
                                               config=delivery_config)
            return (1, 0)
        except Exception as e:
            _LOGGER.warning(
                "SUPERNOTIFY Failed to %s %s: %s", method, delivery, e)
            return (0, 1)

    def setup_condition_inputs(self, field, value):
        self.hass.states.async_set("%s.%s" % (DOMAIN, field), value)

    async def select_scenarios(self):
        scenarios = []
        for key, scenario in self.scenarios.items():
            if CONF_CONDITION in scenario:
                try:
                    conditions = cv.CONDITION_SCHEMA(
                        scenario.get(CONF_CONDITION))
                    test = await condition.async_from_config(
                        self.hass, conditions)
                    if test(self.hass):
                        scenarios.append(key)
                except Exception as e:
                    _LOGGER.error(
                        "SUPERNOTIFY Scenario condition eval failed: %s", e)
        return scenarios

    def mobile_devices_for_person(self, person_entity_id):

        dev_reg = device_registry.async_get(self.hass)
        ent_reg = entity_registry.async_get(self.hass)

        mobile_devices = []
        person_state = self.hass.states.get(person_entity_id)
        if not person_state:
            _LOGGER.warning("SUPERNOTIFY Unable to resolve %s", person_entity_id)
        else:
            for d_t in person_state.attributes.get('device_trackers', ()):
                entity = ent_reg.async_get(d_t)
                if entity and entity.platform == 'mobile_app':
                    device = dev_reg.async_get(entity.device_id)
                    if device:
                        mobile_devices.append({
                            CONF_MANUFACTURER: device.manufacturer,
                            CONF_MODEL: device.model,
                            CONF_NOTIFY_SERVICE: 'mobile_app_%s' % slugify(device.name),
                            CONF_DEVICE_TRACKER: d_t
                        })
        return mobile_devices
