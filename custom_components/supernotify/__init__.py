"""The SuperNotification integration"""

from homeassistant.const import Platform

import voluptuous as vol
from homeassistant.components.notify import (
    PLATFORM_SCHEMA,
)
from homeassistant.const import (
    CONF_ALIAS,
    CONF_CONDITION,
    ATTR_DOMAIN,
    ATTR_SERVICE,
    CONF_DEFAULT,
    CONF_DESCRIPTION,
    CONF_EMAIL,
    CONF_ENABLED,
    CONF_ENTITIES,
    CONF_ICON,
    CONF_NAME,
    CONF_ID,
    CONF_PLATFORM,
    CONF_SERVICE,
    CONF_TARGET,
    CONF_URL
)
from homeassistant.helpers import config_validation as cv

DOMAIN = "supernotify"

PLATFORMS = [Platform.NOTIFY]
TEMPLATE_DIR = "/config/templates/supernotify"
MEDIA_DIR = "supernotify/media"

CONF_ACTIONS = "actions"
CONF_ACTION = "action"
CONF_TITLE = "title"
CONF_URI = "uri"
CONF_RECIPIENTS = "recipients"
CONF_TEMPLATE_PATH = "template_path"
CONF_MEDIA_PATH = "media_path"
CONF_TEMPLATE = "template"
CONF_LINKS = "links"
CONF_PERSON = "person"
CONF_METHOD = "method"
CONF_METHODS = "methods"
CONF_DELIVERY = "delivery"
CONF_OVERRIDES = "overrides"
CONF_OVERRIDE_BASE = "base"
CONF_OVERRIDE_REPLACE = "replace"
CONF_SELECTION = "selection"

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
CONF_MEDIA = "media"
CONF_CAMERA = "camera"
CONF_MQTT_TOPIC = "mqtt_topic"
CONF_CLIP_URL = "clip_url"
CONF_SNAPSHOT_URL = "snapshot_url"
CONF_PTZ_DELAY = "ptz_delay"
CONF_PTZ_PRESET_DEFAULT = "ptz_default_preset"
CONF_ALT_CAMERA = "alt_camera"
CONF_CAMERAS = "cameras"

OCCUPANCY_ANY_IN = "any_in"
OCCUPANCY_ANY_OUT = "any_out"
OCCUPANCY_ALL_IN = "all_in"
OCCUPANCY_ALL = "all"
OCCUPANCY_NONE = "none"
OCCUPANCY_ALL_OUT = "all_out"
OCCUPANCY_ONLY_IN = "only_in"
OCCUPANCY_ONLY_OUT = "only_out"

ATTR_PRIORITY = "priority"
ATTR_SCENARIOS = "scenarios"
ATTR_DELIVERY = "delivery"
ATTR_DEFAULT = "default"
ATTR_NOTIFICATION_ID = "notification_id"
ATTR_DELIVERY_SELECTION = "delivery_selection"
ATTR_RECIPIENTS = "recipients"
ATTR_DATA = "data"
ATTR_MEDIA = "media"
ATTR_MEDIA_SNAPSHOT_URL = "snapshot_url"
ATTR_MEDIA_CAMERA_ENTITY_ID = "camera_entity_id"
ATTR_MEDIA_CAMERA_DELAY = "camera_delay"
ATTR_MEDIA_CAMERA_PTZ_PRESET = "camera_ptz_preset"
ATTR_MEDIA_CLIP_URL = "clip_url"
ATTR_ACTION_GROUPS = "action_groups"
ATTR_ACTION_CATEGORY = "action_category"
ATTR_ACTION_URL = "action_url"
ATTR_ACTION_URL_TITLE = "action_url_title"
ATTR_MESSAGE_HTML = "message_html"

DELIVERY_SELECTION_IMPLICIT = "implicit"
DELIVERY_SELECTION_EXPLICIT = "explicit"
DELIVERY_SELECTION_FIXED = "fixed"

DELIVERY_SELECTION_VALUES = [DELIVERY_SELECTION_EXPLICIT,
                             DELIVERY_SELECTION_FIXED, DELIVERY_SELECTION_IMPLICIT]

ATTR_DELIVERY_PRIORITY = "delivery_priority"
ATTR_DELIVERY_SCENARIOS = "delivery_scenarios"


SELECTION_FALLBACK_ON_ERROR = "fallback_on_error"
SELECTION_FALLBACK = "fallback"
SELECTION_BY_SCENARIO = "scenario"
SELECTION_DEFAULT = "default"
SELECTION_VALUES = [SELECTION_FALLBACK_ON_ERROR,
                    SELECTION_BY_SCENARIO, SELECTION_DEFAULT, SELECTION_FALLBACK]

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
SCENARIO_NULL = "NULL"

RESERVED_DELIVERY_NAMES = ["ALL"]
RESERVED_SCENARIO_NAMES = [SCENARIO_DEFAULT, SCENARIO_NULL]
RESERVED_DATA_KEYS = [ATTR_DOMAIN, ATTR_SERVICE]

DATA_SCHEMA = vol.Schema({
    vol.NotIn(RESERVED_DATA_KEYS): vol.Any(str, int, bool, float, dict, list)
})
MOBILE_DEVICE_SCHEMA = vol.Schema({
    vol.Optional(CONF_MANUFACTURER): cv.string,
    vol.Optional(CONF_MODEL): cv.string,
    vol.Optional(CONF_NOTIFY_SERVICE): cv.string,
    vol.Required(CONF_DEVICE_TRACKER): cv.entity_id
})
DELIVERY_CUSTOMIZE_SCHEMA = vol.Schema({
    vol.Optional(CONF_TARGET): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_ENTITIES): vol.All(cv.ensure_list, [cv.entity_id]),
    vol.Optional(CONF_ENABLED, default=True): cv.boolean,
    vol.Optional(CONF_DATA): DATA_SCHEMA
})
LINK_SCHEMA = vol.Schema({
    vol.Optional(CONF_ID): cv.string,
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
    vol.Optional(CONF_EMAIL): vol.Email(),
    vol.Optional(CONF_TARGET): cv.string,
    vol.Optional(CONF_PHONE_NUMBER): cv.string,
    vol.Optional(CONF_MOBILE_DISCOVERY, default=True): cv.boolean,
    vol.Optional(CONF_MOBILE_DEVICES, default=[]): vol.All(cv.ensure_list, [MOBILE_DEVICE_SCHEMA]),
    vol.Optional(CONF_DELIVERY, default={}): {cv.string: DELIVERY_CUSTOMIZE_SCHEMA}
})
CAMERA_SCHEMA = vol.Schema({
    vol.Required(CONF_CAMERA): cv.entity_id,
    vol.Optional(CONF_ALT_CAMERA): vol.All(cv.ensure_list, [cv.entity_id]),
    vol.Optional(CONF_ALIAS): cv.string,
    vol.Optional(CONF_URL): cv.url,
    vol.Optional(CONF_DEVICE_TRACKER): cv.entity_id,
    vol.Optional(CONF_PTZ_PRESET_DEFAULT, default=1): vol.Any(cv.positive_int, cv.string),
    vol.Optional(CONF_PTZ_DELAY, default=0): int
})
MEDIA_SCHEMA = vol.Schema({
    vol.Optional(ATTR_MEDIA_CAMERA_ENTITY_ID): cv.entity_id,
    vol.Optional(ATTR_MEDIA_CAMERA_DELAY, default=0): int,
    vol.Optional(ATTR_MEDIA_CAMERA_PTZ_PRESET): vol.Any(cv.positive_int, cv.string),
    vol.Optional(CONF_MQTT_TOPIC): cv.string,
    # URL fragments allowed
    vol.Optional(ATTR_MEDIA_CLIP_URL): vol.Any(cv.url, cv.string),
    vol.Optional(ATTR_MEDIA_SNAPSHOT_URL): vol.Any(cv.url, cv.string)
})
DELIVERY_SCHEMA = vol.Schema({
    vol.Optional(CONF_ALIAS): cv.string,
    vol.Required(CONF_METHOD): vol.In(METHOD_VALUES),
    vol.Optional(CONF_SERVICE): cv.service,
    vol.Optional(CONF_PLATFORM): cv.string,
    vol.Optional(CONF_TEMPLATE): cv.string,
    vol.Optional(CONF_DEFAULT, default=False): cv.boolean,
    vol.Optional(CONF_SELECTION, default=[SELECTION_DEFAULT]): vol.All(cv.ensure_list, [vol.In(SELECTION_VALUES)]),
    vol.Optional(CONF_TARGET): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_ENTITIES): vol.All(cv.ensure_list, [cv.entity_id]),
    vol.Optional(CONF_MESSAGE): vol.Any(None, cv.string),
    vol.Optional(CONF_TITLE): vol.Any(None, cv.string),
    vol.Optional(CONF_DATA): DATA_SCHEMA,
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
    vol.Optional(CONF_MEDIA): MEDIA_SCHEMA,
    vol.Optional(CONF_DELIVERY_SELECTION): vol.In(DELIVERY_SELECTION_VALUES),
    vol.Optional(CONF_DELIVERY, default={}): {cv.string: vol.Any(None, DELIVERY_CUSTOMIZE_SCHEMA)}
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
        vol.Optional(CONF_MEDIA_PATH, default=MEDIA_DIR): cv.path,
        vol.Optional(CONF_DELIVERY, default={}): {cv.string: DELIVERY_SCHEMA},
        vol.Optional(CONF_ACTIONS, default={}): {cv.string: [PUSH_ACTION_SCHEMA]},
        vol.Optional(CONF_RECIPIENTS, default=[]):
            vol.All(cv.ensure_list, [RECIPIENT_SCHEMA]),
        vol.Optional(CONF_LINKS, default=[]):
            vol.All(cv.ensure_list, [LINK_SCHEMA]),
        vol.Optional(CONF_SCENARIOS, default={}): {cv.string: SCENARIO_SCHEMA},
        vol.Optional(CONF_OVERRIDES, default={}): {cv.string: OVERRIDE_SCHEMA},
        vol.Optional(CONF_METHODS, default={}): {cv.string: METHOD_DEFAULTS_SCHEMA},
        vol.Optional(CONF_CAMERAS, default=[]): vol.All(cv.ensure_list, [CAMERA_SCHEMA])
    }
)

SERVICE_DATA_SCHEMA = vol.Schema({
    vol.Optional(ATTR_DELIVERY): vol.Any(cv.string, [cv.string], {cv.string: DELIVERY_CUSTOMIZE_SCHEMA}),
    vol.Optional(ATTR_PRIORITY): vol.In(PRIORITY_VALUES),
    vol.Optional(ATTR_SCENARIOS): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(ATTR_DELIVERY_SELECTION): vol.In(DELIVERY_SELECTION_VALUES),
    vol.Optional(ATTR_RECIPIENTS): vol.All(cv.ensure_list, [cv.entity_id]),
    vol.Optional(ATTR_MEDIA): MEDIA_SCHEMA,
    vol.Optional(ATTR_MESSAGE_HTML): cv.string,
    vol.Optional(ATTR_ACTION_GROUPS): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(ATTR_ACTION_CATEGORY): cv.string,
    vol.Optional(ATTR_ACTION_URL): cv.url,
    vol.Optional(ATTR_ACTION_URL_TITLE): cv.string,
    vol.Optional(ATTR_DATA): vol.Any(None, DATA_SCHEMA)
})
