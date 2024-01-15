"""The SuperNotification integration"""

from homeassistant.const import Platform

import voluptuous as vol
from homeassistant.components.notify import (
    PLATFORM_SCHEMA,
)
from homeassistant.const import (
    CONF_ALIAS,
    CONF_CONDITION,
    CONF_DEFAULT,
    CONF_DESCRIPTION,
    CONF_EMAIL,
    CONF_ENABLED,
    CONF_ENTITIES,
    CONF_ICON,
    CONF_NAME,
    CONF_PLATFORM,
    CONF_SERVICE,
    CONF_TARGET,
    CONF_URL
)
from homeassistant.helpers import config_validation as cv

DOMAIN = "supernotify"

PLATFORMS = [Platform.NOTIFY]
TEMPLATE_DIR = "/config/templates/supernotify"


CONF_ACTIONS = "actions"
CONF_ACTION = "action"
CONF_TITLE = "title"
CONF_URI = "uri"
CONF_RECIPIENTS = "recipients"
CONF_TEMPLATE_PATH = "template_path"
CONF_TEMPLATE = "template"
CONF_LINKS = "links"
CONF_PERSON = "person"
CONF_METHOD = "method"
CONF_METHODS = "methods"
CONF_DELIVERY = "delivery"
CONF_OVERRIDES = "overrides"
CONF_OVERRIDE_BASE = "base"
CONF_OVERRIDE_REPLACE = "replace"
CONF_FALLBACK = "fallback"

CONF_DATA = "data"
CONF_OPTIONS = "options"
CONF_MOBILE = "mobile"
CONF_NOTIFY = "notify"
CONF_NOTIFY_SERVICE = "notify_service"
CONF_PHONE_NUMBER = "phone_number"
CONF_PRIORITY = "priority"
CONF_OCCUPANCY = "occupancy"
CONF_SCENARIOS = "scenarios"
CONF_MANUFACTURER = "manufacturer"
CONF_DEVICE_TRACKER = "device_tracker"
CONF_MODEL = "model"
CONF_MESSAGE = "message"
CONF_TITLE = "title"
CONF_MOBILE_DEVICES = "mobile_devices"
CONF_MOBILE_DISCOVERY = "mobile_discovery"
CONF_ACTION_TEMPLATE = "action_template"
CONF_TITLE_TEMPLATE = "title_template"
CONF_DELIVERY_SELECTION = "delivery_selection"

OCCUPANCY_ANY_IN = "any_in"
OCCUPANCY_ANY_OUT = "any_out"
OCCUPANCY_ALL_IN = "all_in"
OCCUPANCY_ALL = "all"
OCCUPANCY_NONE = "none"
OCCUPANCY_ALL_OUT = "all_out"
OCCUPANCY_ONLY_IN = "only_in"
OCCUPANCY_ONLY_OUT = "only_out"

FALLBACK_DISABLED = "disabled"
FALLBACK_ON_ERROR = "on_error"
FALLBACK_ENABLED = "enabled"

ATTR_PRIORITY = "priority"
ATTR_SCENARIOS = "scenarios"
ATTR_DELIVERY = "delivery"
ATTR_DEFAULT = "default"
ATTR_NOTIFICATION_ID = "notification_id"
ATTR_DELIVERY_SELECTION = "delivery_selection"
ATTR_SCENARIOS_BY_DELIVERY = "delivery_scenarios"
ATTR_CONFIGURED_DELIVERIES = "configured_deliveries"
ATTR_SKIPPED_DELIVERIES = "skipped_deliveries"

DELIVERY_SELECTION_IMPLICIT = "implicit"
DELIVERY_SELECTION_EXPLICIT = "explicit"

ATTR_DELIVERY_PRIORITY = "delivery_priority"
ATTR_DELIVERY_SCENARIOS = "delivery_scenarios"

FALLBACK_VALUES = [FALLBACK_ON_ERROR, FALLBACK_DISABLED, FALLBACK_ENABLED]
OCCUPANCY_VALUES = [OCCUPANCY_ALL_IN, OCCUPANCY_ALL_OUT,
                    OCCUPANCY_ANY_IN, OCCUPANCY_ANY_OUT,
                    OCCUPANCY_ONLY_IN, OCCUPANCY_ONLY_OUT,
                    OCCUPANCY_ALL, OCCUPANCY_NONE]

PRIORITY_CRITICAL = "critical"
PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"

PRIORITY_VALUES = [PRIORITY_CRITICAL, PRIORITY_HIGH,
                   PRIORITY_LOW, PRIORITY_MEDIUM]
METHOD_SMS = "sms"
METHOD_EMAIL = "email"
METHOD_ALEXA = "alexa"
METHOD_MOBILE_PUSH = "mobile_push"
METHOD_MEDIA = "media"
METHOD_CHIME = "chime"
METHOD_GENERIC = "generic"
METHOD_PERSISTENT = "persistent"
METHOD_VALUES = [METHOD_SMS, METHOD_ALEXA, METHOD_MOBILE_PUSH,
                 METHOD_CHIME, METHOD_EMAIL, METHOD_MEDIA,
                 METHOD_PERSISTENT, METHOD_GENERIC]

SCENARIO_DEFAULT = "DEFAULT"

RESERVED_DELIVERY_NAMES = ["ALL"]
RESERVED_SCENARIO_NAMES = [SCENARIO_DEFAULT]

MOBILE_DEVICE_SCHEMA = vol.Schema({
    vol.Optional(CONF_MANUFACTURER): cv.string,
    vol.Optional(CONF_MODEL): cv.string,
    vol.Optional(CONF_NOTIFY_SERVICE): cv.string,
    vol.Required(CONF_DEVICE_TRACKER): cv.entity_id
})
RECIPIENT_DELIVERY_CUSTOMIZE_SCHEMA = vol.Schema({
    vol.Optional(CONF_TARGET): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_ENTITIES): vol.All(cv.ensure_list, [cv.entity_id]),
    vol.Optional(CONF_DATA): dict
})
LINK_SCHEMA = vol.Schema({
    vol.Required(CONF_URL): cv.url,
    vol.Optional(CONF_ICON): cv.icon,
    vol.Required(CONF_DESCRIPTION): cv.string,
    vol.Optional(CONF_NAME): cv.string
})
METHOD_DEFAULTS_SCHEMA = vol.Schema({
    vol.Optional(CONF_TARGET): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_ENTITIES): vol.All(cv.ensure_list, [cv.entity_id]),
    vol.Optional(CONF_SERVICE): cv.service
})
RECIPIENT_SCHEMA = vol.Schema({
    vol.Required(CONF_PERSON): cv.entity_id,
    vol.Optional(CONF_ALIAS): cv.string,
    vol.Optional(CONF_EMAIL): cv.string,
    vol.Optional(CONF_TARGET): cv.string,
    vol.Optional(CONF_PHONE_NUMBER): cv.string,
    vol.Optional(CONF_MOBILE_DISCOVERY, default=True): cv.boolean,
    vol.Optional(CONF_MOBILE_DEVICES, default=[]): vol.All(cv.ensure_list, [MOBILE_DEVICE_SCHEMA]),
    vol.Optional(CONF_DELIVERY, default={}): {cv.string: RECIPIENT_DELIVERY_CUSTOMIZE_SCHEMA}
})
DELIVERY_SCHEMA = vol.Schema({
    vol.Optional(CONF_ALIAS): cv.string,
    vol.Required(CONF_METHOD): vol.In(METHOD_VALUES),
    vol.Optional(CONF_SERVICE): cv.service,
    vol.Optional(CONF_PLATFORM): cv.string,
    vol.Optional(CONF_TEMPLATE): cv.string,
    vol.Optional(CONF_DEFAULT, default=False): cv.boolean,
    vol.Optional(CONF_FALLBACK, default=FALLBACK_DISABLED): vol.In(FALLBACK_VALUES),
    vol.Optional(CONF_TARGET): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_ENTITIES): vol.All(cv.ensure_list, [cv.entity_id]),
    vol.Optional(CONF_MESSAGE): cv.string,
    vol.Optional(CONF_TITLE): cv.string,
    vol.Optional(CONF_DATA): dict,
    vol.Optional(CONF_ENABLED, default=True): cv.boolean,
    vol.Optional(CONF_PRIORITY, default=PRIORITY_VALUES):
        vol.All(cv.ensure_list, [vol.In(PRIORITY_VALUES)]),
    vol.Optional(CONF_OCCUPANCY, default=OCCUPANCY_ALL):
        vol.In(OCCUPANCY_VALUES),
    vol.Optional(CONF_CONDITION): cv.CONDITION_SCHEMA
})
SCENARIO_SCHEMA = vol.Schema({
    vol.Optional(CONF_ALIAS): cv.string,
    vol.Optional(CONF_CONDITION): cv.CONDITION_SCHEMA,
    vol.Optional(CONF_DELIVERY_SELECTION, default=DELIVERY_SELECTION_EXPLICIT): vol.Any(DELIVERY_SELECTION_EXPLICIT, DELIVERY_SELECTION_IMPLICIT),
    vol.Optional(CONF_DELIVERY, default={}): {cv.string: vol.Any(None, DELIVERY_SCHEMA)}
})
OVERRIDE_SCHEMA = vol.Schema({
    vol.Required(CONF_OVERRIDE_BASE): cv.string,
    vol.Required(CONF_OVERRIDE_REPLACE): cv.string
})
PUSH_ACTION_SCHEMA = vol.Schema({
    vol.Exclusive(CONF_ACTION, CONF_ACTION_TEMPLATE): cv.string,
    vol.Exclusive(CONF_TITLE, CONF_TITLE_TEMPLATE): cv.string,
    vol.Optional(CONF_URI): cv.url,
    vol.Optional(CONF_ICON): cv.string
}, extra=vol.ALLOW_EXTRA)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_TEMPLATE_PATH, default=TEMPLATE_DIR):
            cv.path,
        vol.Optional(CONF_DELIVERY, default={}): {cv.string: DELIVERY_SCHEMA},
        vol.Optional(CONF_ACTIONS, default={}): {cv.string: [PUSH_ACTION_SCHEMA]},
        vol.Optional(CONF_RECIPIENTS, default=[]):
            vol.All(cv.ensure_list, [RECIPIENT_SCHEMA]),
        vol.Optional(CONF_LINKS, default=[]):
            vol.All(cv.ensure_list, [LINK_SCHEMA]),
        vol.Optional(CONF_SCENARIOS, default={}): {cv.string: SCENARIO_SCHEMA},
        vol.Optional(CONF_OVERRIDES, default={}): {cv.string: OVERRIDE_SCHEMA},
        vol.Optional(CONF_METHODS, default={}): {cv.string: METHOD_DEFAULTS_SCHEMA}
    }
)
