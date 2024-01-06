from homeassistant.components.supernotify.methods.alexa_media_player import AlexaMediaPlayerDeliveryMethod
from homeassistant.components.supernotify.methods.apple_push import ApplePushDeliveryMethod
from homeassistant.components.supernotify.methods.sms import SMSDeliveryMethod
from homeassistant.components.supernotify.methods.email import EmailDeliveryMethod
from homeassistant.components.supernotify.methods.chime import ChimeDeliveryMethod
from homeassistant.components.supernotify.methods.persistent import PersistentDeliveryMethod
from homeassistant.components.supernotify.methods.media_player import MediaPlayerImageDeliveryMethod
from . import (
    ATTR_NOTIFICATION_ID,
    ATTR_PRIORITY,
    ATTR_DELIVERY,
    ATTR_SCENARIOS,
    CONF_ACTIONS,
    CONF_DELIVERY,
    CONF_LINKS,
    CONF_METHOD,
    CONF_OCCUPANCY,
    CONF_OVERRIDE_BASE,
    CONF_OVERRIDE_REPLACE,
    CONF_OVERRIDES,
    CONF_PERSON,
    CONF_PRIORITY,
    CONF_RECIPIENTS,
    CONF_TEMPLATE,
    CONF_TEMPLATES,
    CONF_PHONE_NUMBER,
    ATTR_DELIVERY_PRIORITY,
    ATTR_DELIVERY_SCENARIOS,
    DOMAIN,
    METHOD_ALEXA,
    METHOD_APPLE_PUSH,
    METHOD_CHIME,
    METHOD_EMAIL,
    METHOD_MEDIA,
    METHOD_PERSISTENT,
    METHOD_SMS,
    METHOD_VALUES,
    OCCUPANCY_ALL,
    OCCUPANCY_VALUES,
    PRIORITY_MEDIUM,
    PRIORITY_VALUES,
)
from homeassistant.helpers.reload import async_setup_reload_service
from homeassistant.helpers import condition, config_validation as cv
from homeassistant.const import (
    CONF_CONDITION,
    CONF_DEFAULT,
    CONF_DESCRIPTION,
    CONF_EMAIL,
    CONF_ENTITIES,
    CONF_ICON,
    CONF_NAME,
    CONF_PLATFORM,
    CONF_SERVICE,
    CONF_TARGET,
    CONF_URL,
    Platform,
)
from homeassistant.components.notify import (
    ATTR_DATA,
    ATTR_TARGET,
    ATTR_TITLE,
    PLATFORM_SCHEMA,
    BaseNotificationService,
)
from .common import SuperNotificationContext
from .methods.email import EmailDeliveryMethod
from homeassistant.components.ios import PUSH_ACTION_SCHEMA
import asyncio
import logging
import os.path
import re

from jinja2 import Environment, FileSystemLoader
import voluptuous as vol

RE_VALID_PHONE = r"^(\+\d{1,3})?\s?\(?\d{1,4}\)?[\s.-]?\d{3}[\s.-]?\d{4}$"


_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.NOTIFY]
TEMPLATE_DIR = "/config/templates/supernotify"

METHOD_CUSTOMIZE_SCHEMA = {
    vol.Optional(CONF_ENTITIES): vol.All(cv.ensure_list, [cv.entity_id]),
}
LINK_SCHEMA = {
    vol.Required(CONF_URL): cv.url,
    vol.Optional(CONF_ICON): cv.icon,
    vol.Required(CONF_DESCRIPTION): cv.string,
    vol.Optional(CONF_NAME): cv.string
}
RECIPIENT_SCHEMA = {
    vol.Required(CONF_PERSON): cv.entity_id,
    vol.Optional(CONF_EMAIL): cv.string,
    vol.Optional(CONF_TARGET): cv.string,
    vol.Optional(CONF_PHONE_NUMBER): cv.string,
    vol.Optional(CONF_METHOD, default={}):  {cv.string: METHOD_CUSTOMIZE_SCHEMA}
}
DELIVERY_SCHEMA = {
    vol.Required(CONF_METHOD): vol.In(METHOD_VALUES),
    vol.Optional(CONF_SERVICE): cv.service,
    vol.Optional(CONF_PLATFORM): cv.string,
    vol.Optional(CONF_TEMPLATE): cv.string,
    vol.Optional(CONF_DEFAULT, default=False): cv.boolean,
    vol.Optional(CONF_ENTITIES): vol.All(cv.ensure_list,
                                         [cv.entity_id]),
    vol.Optional(CONF_PRIORITY, default=PRIORITY_VALUES):
        vol.All(cv.ensure_list, [vol.In(PRIORITY_VALUES)]),
    vol.Optional(CONF_OCCUPANCY, default=OCCUPANCY_ALL):
        vol.In(OCCUPANCY_VALUES),
    vol.Optional(CONF_CONDITION): cv.CONDITION_SCHEMA,
}
OVERRIDE_SCHEMA = {
    vol.Required(CONF_OVERRIDE_BASE): cv.string,
    vol.Required(CONF_OVERRIDE_REPLACE): cv.string
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_TEMPLATES, default=TEMPLATE_DIR):
            cv.path,
        vol.Optional(CONF_DELIVERY, default={}): {cv.string: DELIVERY_SCHEMA},
        vol.Optional(CONF_ACTIONS, default=[]):
            vol.All(cv.ensure_list, [PUSH_ACTION_SCHEMA]),
        vol.Optional(CONF_RECIPIENTS, default=[]):
            vol.All(cv.ensure_list, [RECIPIENT_SCHEMA]),
        vol.Optional(CONF_LINKS, default=[]):
            vol.All(cv.ensure_list, [LINK_SCHEMA]),
        vol.Optional(CONF_OVERRIDES, default={}): {cv.string: OVERRIDE_SCHEMA}
    }
)

METHODS = {
    METHOD_EMAIL:       EmailDeliveryMethod,
    METHOD_SMS:         SMSDeliveryMethod,
    METHOD_ALEXA:       AlexaMediaPlayerDeliveryMethod,
    METHOD_APPLE_PUSH:  ApplePushDeliveryMethod,
    METHOD_MEDIA:       MediaPlayerImageDeliveryMethod,
    METHOD_CHIME:       ChimeDeliveryMethod,
    METHOD_PERSISTENT:  PersistentDeliveryMethod
}


async def async_get_service(hass, config, discovery_info=None):
    for delivery in config.get(CONF_DELIVERY, ()).values():
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
            CONF_ACTIONS: config.get(CONF_ACTIONS, ()),
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
                                    links=config[CONF_LINKS],
                                    overrides=config[CONF_OVERRIDES]
                                    )


class SuperNotificationService(BaseNotificationService):
    """Implement SuperNotification service."""

    def __init__(self, hass,
                 deliveries=None,
                 templates=None,
                 recipients=(),
                 mobile_actions=(),
                 links=(),
                 overrides=None):
        """Initialize the service."""
        self.hass = hass

        hass_url = hass.config.external_url or self.hass.config.internal_url
        context = SuperNotificationContext(
            hass_url, hass.config.location_name, links, recipients, mobile_actions, templates)

        self.recipients = recipients
        self.templates = templates
        self.actions = mobile_actions
        self.links = links
        self.overrides = overrides or {}
        deliveries = deliveries or {}

        self.people = {r["person"]: r for r in recipients}
        if templates and not os.path.exists(templates):
            _LOGGER.warning("SUPERNOTIFY template directory not found at %s",
                            templates)
            self.templates = None

        self.methods = {}
        self.deliveries = {k: d for k, d in deliveries.items(
        ) if CONF_METHOD in d and d[CONF_METHOD] not in METHODS}
        for method in METHODS:
            self.methods[method] = METHODS[method](hass, context, deliveries)
            self.deliveries.update(self.methods[method].valid_deliveries)
            if self.methods[method].invalid_deliveries:
                _LOGGER.warning("SUPERNOTIFY Invalid deliveries with no service defined: %s",
                                self.methods[method].invalid_deliveries)
        _LOGGER.info("SUPERNOTIFY configured deliveries %s",
                     ";".join(self.deliveries.keys()))

    def send_message(self, message="", **kwargs):
        """Send a message via chosen method."""
        _LOGGER.debug("Message: %s, kwargs: %s", message, kwargs)
        target = kwargs.get(ATTR_TARGET) or []
        if isinstance(target, str):
            target = [target]
        data = kwargs.get(ATTR_DATA) or {}
        title = kwargs.get(ATTR_TITLE)
        priority = data.get(ATTR_PRIORITY, PRIORITY_MEDIUM)
        scenarios = data.get(ATTR_SCENARIOS) or []

        snapshot_url = data.get("snapshot_url")
        override_delivery = data.get(ATTR_DELIVERY)
        if not override_delivery:
            deliveries = self.deliveries.keys()
        else:
            deliveries = [
                d for d in override_delivery if d in self.deliveries]
            if override_delivery != deliveries:
                _LOGGER.info("SUPERNOTIFY overriding delivery %s->%s",
                             override_delivery, deliveries)

        stats_delivieries = stats_errors = 0
        self.setup_condition_inputs(ATTR_DELIVERY_PRIORITY, priority)
        self.setup_condition_inputs(ATTR_DELIVERY_SCENARIOS, scenarios)

        for delivery in deliveries:
            delivery_config = self.deliveries.get(delivery, {})
            if CONF_PRIORITY in delivery_config and priority not in delivery_config[CONF_PRIORITY]:
                _LOGGER.debug(
                    "SUPERNOTIFY Skipping delivery %s based on priority (%s)", delivery, priority)
                continue
            if not self.evaluate_delivery_conditions(delivery_config):
                _LOGGER.debug(
                    "SUPERNOTIFY Skipping delivery %s based on conditions", delivery)
                continue
            delivery_scenarios = delivery_config.get(ATTR_SCENARIOS)
            if delivery_scenarios and not any(s in delivery_scenarios for s in scenarios):
                _LOGGER.debug(
                    "Skipping delivery without matched scenario (%s) vs (%s)", scenarios, delivery_scenarios)
                continue
            method = delivery_config["method"]

            try:
                self.methods[method].deliver(message=message,
                                             title=title,
                                             target=target,
                                             scenarios=scenarios,
                                             data=data.get(
                                                delivery, {}),
                                             config=delivery_config)
                stats_delivieries += 1
            except Exception as e:
                stats_errors += 1
                _LOGGER.warning(
                    "SUPERNOTIFY Failed to %s %s: %s", method, delivery, e)

        return stats_delivieries, stats_errors

  
    def on_notify_media_player(self, message, config=None, target=None, snapshot_url=None, data=None):
        _LOGGER.info("SUPERNOTIFY notify media player: %s", message)
        config = config or {}
        if target is None:
            target = config.get(CONF_ENTITIES, [])
        if target is None:
            _LOGGER.debug("SUPERNOTIFY skipping media player, no targets")
            return

    def evaluate_delivery_conditions(self, delivery_config):
        if CONF_CONDITION not in delivery_config:
            return True
        else:
            try:
                conditions = cv.CONDITION_SCHEMA(
                    delivery_config.get(CONF_CONDITION))
                test = asyncio.run_coroutine_threadsafe(
                    condition.async_from_config(
                        self.hass, conditions), self.hass.loop
                ).result()
                return test(self.hass)
            except Exception as e:
                _LOGGER.error("SUPERNOTIFY Condition eval failed: %s", e)
                raise

    def setup_condition_inputs(self, field, value):
        self.hass.states.set("%s.%s" % (DOMAIN, field), value)
