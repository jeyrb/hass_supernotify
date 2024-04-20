"""The SuperNotification integration"""

import time
from enum import StrEnum

import voluptuous as vol
from homeassistant.components.notify import PLATFORM_SCHEMA
from homeassistant.const import (
    ATTR_DOMAIN,
    ATTR_SERVICE,
    CONF_ALIAS,
    CONF_CONDITION,
    CONF_DEFAULT,
    CONF_DESCRIPTION,
    CONF_EMAIL,
    CONF_ENABLED,
    CONF_ENTITIES,
    CONF_ICON,
    CONF_ID,
    CONF_NAME,
    CONF_PLATFORM,
    CONF_SERVICE,
    CONF_TARGET,
    CONF_URL,
    Platform,
)
from homeassistant.helpers import config_validation as cv

from custom_components.supernotify.common import format_timestamp

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
CONF_HOUSEKEEPING = "housekeeping"
CONF_HOUSEKEEPING_TIME = "housekeeping_time"
CONF_ARCHIVE_PATH = "archive_path"
CONF_ARCHIVE = "archive"
CONF_ARCHIVE_DAYS = "archive_days"
CONF_TEMPLATE = "template"
CONF_LINKS = "links"
CONF_PERSON = "person"
CONF_METHOD = "method"
CONF_METHODS = "methods"
CONF_DELIVERY = "delivery"
CONF_SELECTION = "selection"

CONF_DATA: str = "data"
CONF_OPTIONS: str = "options"
CONF_MOBILE: str = "mobile"
CONF_NOTIFY: str = "notify"
CONF_NOTIFY_SERVICE: str = "notify_service"
CONF_PHONE_NUMBER: str = "phone_number"
CONF_PRIORITY: str = "priority"
CONF_OCCUPANCY: str = "occupancy"
CONF_SCENARIOS: str = "scenarios"
CONF_MANUFACTURER: str = "manufacturer"
CONF_DEVICE_TRACKER: str = "device_tracker"
CONF_MODEL: str = "model"
CONF_MESSAGE: str = "message"
CONF_TARGETS_REQUIRED: str = "targets_required"
CONF_MOBILE_DEVICES: str = "mobile_devices"
CONF_MOBILE_DISCOVERY: str = "mobile_discovery"
CONF_ACTION_TEMPLATE: str = "action_template"
CONF_TITLE_TEMPLATE: str = "title_template"
CONF_DELIVERY_SELECTION: str = "delivery_selection"
CONF_MEDIA: str = "media"
CONF_CAMERA: str = "camera"
CONF_CLIP_URL: str = "clip_url"
CONF_SNAPSHOT_URL: str = "snapshot_url"
CONF_PTZ_DELAY: str = "ptz_delay"
CONF_PTZ_METHOD: str = "ptz_method"
CONF_PTZ_PRESET_DEFAULT: str = "ptz_default_preset"
CONF_ALT_CAMERA: str = "alt_camera"
CONF_CAMERAS: str = "cameras"


OCCUPANCY_ANY_IN = "any_in"
OCCUPANCY_ANY_OUT = "any_out"
OCCUPANCY_ALL_IN = "all_in"
OCCUPANCY_ALL = "all"
OCCUPANCY_NONE = "none"
OCCUPANCY_ALL_OUT = "all_out"
OCCUPANCY_ONLY_IN = "only_in"
OCCUPANCY_ONLY_OUT = "only_out"

ATTR_PRIORITY = "priority"
ATTR_ACTION = "action"
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
ATTR_JPEG_FLAGS = "jpeg_flags"
ATTR_TIMESTAMP = "timestamp"
ATTR_DEBUG = "debug"
ATTR_ACTIONS = "actions"
ATTR_USER_ID = "user_id"

DELIVERY_SELECTION_IMPLICIT = "implicit"
DELIVERY_SELECTION_EXPLICIT = "explicit"
DELIVERY_SELECTION_FIXED = "fixed"

DELIVERY_SELECTION_VALUES = [DELIVERY_SELECTION_EXPLICIT, DELIVERY_SELECTION_FIXED, DELIVERY_SELECTION_IMPLICIT]
PTZ_METHOD_ONVIF = "onvif"
PTZ_METHOD_FRIGATE = "frigate"
PTZ_METHOD_VALUES = [PTZ_METHOD_ONVIF, PTZ_METHOD_FRIGATE]

ATTR_DELIVERY_PRIORITY = "delivery_priority"
ATTR_DELIVERY_SCENARIOS = "delivery_scenarios"


SELECTION_FALLBACK_ON_ERROR = "fallback_on_error"
SELECTION_FALLBACK = "fallback"
SELECTION_BY_SCENARIO = "scenario"
SELECTION_DEFAULT = "default"
SELECTION_VALUES = [SELECTION_FALLBACK_ON_ERROR, SELECTION_BY_SCENARIO, SELECTION_DEFAULT, SELECTION_FALLBACK]

OCCUPANCY_VALUES = [
    OCCUPANCY_ALL_IN,
    OCCUPANCY_ALL_OUT,
    OCCUPANCY_ANY_IN,
    OCCUPANCY_ANY_OUT,
    OCCUPANCY_ONLY_IN,
    OCCUPANCY_ONLY_OUT,
    OCCUPANCY_ALL,
    OCCUPANCY_NONE,
]

PRIORITY_CRITICAL = "critical"
PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"

PRIORITY_VALUES = [PRIORITY_LOW, PRIORITY_MEDIUM, PRIORITY_HIGH, PRIORITY_CRITICAL]
METHOD_SMS = "sms"
METHOD_EMAIL = "email"
METHOD_ALEXA = "alexa"
METHOD_MOBILE_PUSH = "mobile_push"
METHOD_MEDIA = "media"
METHOD_CHIME = "chime"
METHOD_GENERIC = "generic"
METHOD_PERSISTENT = "persistent"
METHOD_VALUES = [
    METHOD_SMS,
    METHOD_ALEXA,
    METHOD_MOBILE_PUSH,
    METHOD_CHIME,
    METHOD_EMAIL,
    METHOD_MEDIA,
    METHOD_PERSISTENT,
    METHOD_GENERIC,
]

SCENARIO_DEFAULT = "DEFAULT"
SCENARIO_NULL = "NULL"

RESERVED_DELIVERY_NAMES = ["ALL"]
RESERVED_SCENARIO_NAMES = [SCENARIO_DEFAULT, SCENARIO_NULL]
RESERVED_DATA_KEYS = [ATTR_DOMAIN, ATTR_SERVICE]

CONF_DUPE_CHECK = "dupe_check"
CONF_DUPE_POLICY = "dupe_policy"
CONF_TTL = "ttl"
CONF_SIZE = "size"
ATTR_DUPE_POLICY_MTSLP = "dupe_policy_message_title_same_or_lower_priority"
ATTR_DUPE_POLICY_NONE = "dupe_policy_none"

DATA_SCHEMA = vol.Schema({vol.NotIn(RESERVED_DATA_KEYS): vol.Any(str, int, bool, float, dict, list)})
MOBILE_DEVICE_SCHEMA = vol.Schema({
    vol.Optional(CONF_MANUFACTURER): cv.string,
    vol.Optional(CONF_MODEL): cv.string,
    vol.Optional(CONF_NOTIFY_SERVICE): cv.string,
    vol.Required(CONF_DEVICE_TRACKER): cv.entity_id,
})
NOTIFICATION_DUPE_SCHEMA = vol.Schema({
    vol.Optional(CONF_TTL): cv.positive_int,
    vol.Optional(CONF_SIZE, default=100): cv.positive_int,  # type: ignore
    vol.Optional(CONF_DUPE_POLICY, default=ATTR_DUPE_POLICY_MTSLP): vol.In(  # type: ignore
        [ATTR_DUPE_POLICY_MTSLP, ATTR_DUPE_POLICY_NONE]
    ),  # type: ignore
})
DELIVERY_CUSTOMIZE_SCHEMA = vol.Schema({
    vol.Optional(CONF_TARGET): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_ENTITIES): vol.All(cv.ensure_list, [cv.entity_id]),
    vol.Optional(CONF_ENABLED, default=True): cv.boolean,  # type: ignore
    vol.Optional(CONF_DATA): DATA_SCHEMA,
})
LINK_SCHEMA = vol.Schema({
    vol.Optional(CONF_ID): cv.string,
    vol.Required(CONF_URL): cv.url,
    vol.Optional(CONF_ICON): cv.icon,
    vol.Required(CONF_DESCRIPTION): cv.string,
    vol.Optional(CONF_NAME): cv.string,
})
METHOD_DEFAULTS_SCHEMA = vol.Schema({
    vol.Optional(CONF_TARGET): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_ENTITIES): vol.All(cv.ensure_list, [cv.entity_id]),
    vol.Optional(CONF_SERVICE): cv.service,
    vol.Optional(CONF_TARGETS_REQUIRED, default=False): cv.boolean,  # type: ignore
    vol.Optional(CONF_OPTIONS, default=dict): dict,  # type: ignore
    vol.Optional(CONF_DATA): DATA_SCHEMA,
})
RECIPIENT_SCHEMA = vol.Schema({
    vol.Required(CONF_PERSON): cv.entity_id,
    vol.Optional(CONF_ALIAS): cv.string,
    vol.Optional(CONF_EMAIL): cv.string,
    vol.Optional(CONF_TARGET): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_PHONE_NUMBER): cv.string,
    vol.Optional(CONF_MOBILE_DISCOVERY, default=True): cv.boolean,  # type: ignore
    vol.Optional(CONF_MOBILE_DEVICES, default=list): vol.All(cv.ensure_list, [MOBILE_DEVICE_SCHEMA]),  # type: ignore
    vol.Optional(CONF_DELIVERY, default=dict): {cv.string: DELIVERY_CUSTOMIZE_SCHEMA},  # type: ignore
})
CAMERA_SCHEMA = vol.Schema({
    vol.Required(CONF_CAMERA): cv.entity_id,
    vol.Optional(CONF_ALT_CAMERA): vol.All(cv.ensure_list, [cv.entity_id]),
    vol.Optional(CONF_ALIAS): cv.string,
    vol.Optional(CONF_URL): cv.url,
    vol.Optional(CONF_DEVICE_TRACKER): cv.entity_id,
    vol.Optional(CONF_PTZ_PRESET_DEFAULT, default=1): vol.Any(cv.positive_int, cv.string),  # type: ignore
    vol.Optional(CONF_PTZ_DELAY, default=0): int,  # type: ignore
    vol.Optional(CONF_PTZ_METHOD, default=PTZ_METHOD_ONVIF): vol.In(PTZ_METHOD_VALUES),  # type: ignore
})
MEDIA_SCHEMA = vol.Schema({
    vol.Optional(ATTR_MEDIA_CAMERA_ENTITY_ID): cv.entity_id,
    vol.Optional(ATTR_MEDIA_CAMERA_DELAY, default=0): int,  # type: ignore
    vol.Optional(ATTR_MEDIA_CAMERA_PTZ_PRESET): vol.Any(cv.positive_int, cv.string),
    # URL fragments allowed
    vol.Optional(ATTR_MEDIA_CLIP_URL): vol.Any(cv.url, cv.string),
    vol.Optional(ATTR_MEDIA_SNAPSHOT_URL): vol.Any(cv.url, cv.string),
    vol.Optional(ATTR_JPEG_FLAGS): dict,
})
DELIVERY_SCHEMA = vol.Schema({
    vol.Optional(CONF_ALIAS): cv.string,
    vol.Required(CONF_METHOD): vol.In(METHOD_VALUES),
    vol.Optional(CONF_SERVICE): cv.service,
    vol.Optional(CONF_PLATFORM): cv.string,
    vol.Optional(CONF_TEMPLATE): cv.string,
    vol.Optional(CONF_DEFAULT, default=False): cv.boolean,  # type: ignore
    vol.Optional(CONF_SELECTION, default=[SELECTION_DEFAULT]): vol.All(  # type: ignore
        cv.ensure_list, [vol.In(SELECTION_VALUES)]
    ),
    vol.Optional(CONF_TARGET): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_ENTITIES): vol.All(cv.ensure_list, [cv.entity_id]),
    vol.Optional(CONF_MESSAGE): vol.Any(None, cv.string),
    vol.Optional(CONF_TITLE): vol.Any(None, cv.string),
    vol.Optional(CONF_DATA): DATA_SCHEMA,
    vol.Optional(CONF_ENABLED, default=True): cv.boolean,  # type: ignore # type: ignore
    vol.Optional(CONF_OPTIONS, default=dict): dict,  # type: ignore
    vol.Optional(CONF_PRIORITY, default=PRIORITY_VALUES): vol.All(  # type: ignore
        cv.ensure_list, [vol.In(PRIORITY_VALUES)]
    ),
    vol.Optional(CONF_OCCUPANCY, default=OCCUPANCY_ALL): vol.In(OCCUPANCY_VALUES),  # type: ignore
    vol.Optional(CONF_CONDITION): cv.CONDITION_SCHEMA,
})

SCENARIO_SCHEMA = vol.Schema({
    vol.Optional(CONF_ALIAS): cv.string,
    vol.Optional(CONF_CONDITION): cv.CONDITION_SCHEMA,
    vol.Optional(CONF_MEDIA): MEDIA_SCHEMA,
    vol.Optional(CONF_DELIVERY_SELECTION): vol.In(DELIVERY_SELECTION_VALUES),
    vol.Optional(CONF_DELIVERY, default=dict): {cv.string: vol.Any(None, DELIVERY_CUSTOMIZE_SCHEMA)},  # type: ignore
})

PUSH_ACTION_SCHEMA = vol.Schema(
    {
        vol.Exclusive(CONF_ACTION, CONF_ACTION_TEMPLATE): cv.string,
        vol.Exclusive(CONF_TITLE, CONF_TITLE_TEMPLATE): cv.string,
        vol.Optional(CONF_URI): cv.url,
        vol.Optional(CONF_ICON): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)


ARCHIVE_SCHEMA = vol.Schema({
    vol.Optional(CONF_ARCHIVE_PATH): cv.path,
    vol.Optional(CONF_ENABLED, default=False): cv.boolean,  # type: ignore
    vol.Optional(CONF_ARCHIVE_DAYS, default=3): cv.positive_int,  # type: ignore
})

HOUSEKEEPING_SCHEMA = vol.Schema({
    vol.Optional(CONF_HOUSEKEEPING_TIME, default="00:00:01"): cv.time,  # type: ignore
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_TEMPLATE_PATH, default=TEMPLATE_DIR): cv.path,  # type: ignore
    vol.Optional(CONF_MEDIA_PATH, default=MEDIA_DIR): cv.path,  # type: ignore
    vol.Optional(CONF_ARCHIVE, default={CONF_ENABLED: False}): ARCHIVE_SCHEMA,  # type: ignore
    vol.Optional(CONF_HOUSEKEEPING, default=dict): HOUSEKEEPING_SCHEMA,  # type: ignore
    vol.Optional(CONF_DUPE_CHECK, default=dict): NOTIFICATION_DUPE_SCHEMA,  # type: ignore
    vol.Optional(CONF_DELIVERY, default=dict): {cv.string: DELIVERY_SCHEMA},  # type: ignore
    vol.Optional(CONF_ACTIONS, default=dict): {cv.string: [PUSH_ACTION_SCHEMA]},  # type: ignore
    vol.Optional(CONF_RECIPIENTS, default=list): vol.All(cv.ensure_list, [RECIPIENT_SCHEMA]),  # type: ignore # type: ignore
    vol.Optional(CONF_LINKS, default=list): vol.All(cv.ensure_list, [LINK_SCHEMA]),  # type: ignore
    vol.Optional(CONF_SCENARIOS, default=dict): {cv.string: SCENARIO_SCHEMA},  # type: ignore
    vol.Optional(CONF_METHODS, default=dict): {cv.string: METHOD_DEFAULTS_SCHEMA},  # type: ignore
    vol.Optional(CONF_CAMERAS, default=list): vol.All(cv.ensure_list, [CAMERA_SCHEMA]),  # type: ignore
})

ACTION_SCHEMA = vol.Schema({
    vol.Optional(ATTR_ACTION_GROUPS): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(ATTR_ACTION_CATEGORY): cv.string,
    vol.Optional(ATTR_ACTION_URL): cv.url,
    vol.Optional(ATTR_ACTION_URL_TITLE): cv.string,
})
SERVICE_DATA_SCHEMA = vol.Schema({
    vol.Optional(ATTR_DELIVERY): vol.Any(cv.string, [cv.string], {cv.string: vol.Any(None, DELIVERY_CUSTOMIZE_SCHEMA)}),
    vol.Optional(ATTR_PRIORITY): vol.In(PRIORITY_VALUES),
    vol.Optional(ATTR_SCENARIOS): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(ATTR_DELIVERY_SELECTION): vol.In(DELIVERY_SELECTION_VALUES),
    vol.Optional(ATTR_RECIPIENTS): vol.All(cv.ensure_list, [cv.entity_id]),
    vol.Optional(ATTR_MEDIA): MEDIA_SCHEMA,
    vol.Optional(ATTR_MESSAGE_HTML): cv.string,
    vol.Optional(ATTR_ACTIONS): ACTION_SCHEMA,
    vol.Optional(ATTR_DEBUG, default=False): cv.boolean,  # type: ignore
    vol.Optional(ATTR_DATA): vol.Any(None, DATA_SCHEMA),
})


class TargetType(StrEnum):
    pass


class GlobalTargetType(TargetType):
    NONCRITICAL = "NONCRITICAL"
    EVERYTHING = "EVERYTHING"


class QualifiedTargetType(TargetType):
    METHOD = "METHOD"
    DELIVERY = "DELIVERY"
    CAMERA = "CAMERA"
    LABEL = "LABEL"
    PRIORITY = "PRIORITY"


class RecipientType(StrEnum):
    EVERYONE = "EVERYONE"
    USER = "USER"


class Snooze:
    target: str
    target_type: TargetType
    snoozed_at: float
    recipient_type: RecipientType
    recipient: str | None = None
    snooze_until: float | None = None

    def __init__(
        self,
        target_type: TargetType,
        target: str,
        recipient_type: RecipientType,
        recipient: str | None = None,
        snooze_for: int | None = None,
    ) -> None:
        self.snoozed_at = time.time()
        self.target = target
        self.target_type = target_type
        self.recipient = recipient
        self.recipient_type = recipient_type
        if snooze_for:
            self.snooze_until = self.snoozed_at + snooze_for

    def short_key(self) -> str:
        if self.recipient_type == RecipientType.EVERYONE:
            recipient = f"{RecipientType.EVERYONE}"
        elif self.recipient is not None:
            recipient = f"{self.recipient_type}_{self.recipient}"
        else:
            recipient = "UNKNOWN"
        if self.target_type in QualifiedTargetType:
            target = f"{self.target_type}_{self.target}"
        else:
            target = "GLOBAL"  # can only be one of these active at a time
        return f"{recipient}_{target}"

    def __eq__(self, other: object) -> bool:
        """Check if two snoozes for the same thing"""
        if not isinstance(other, Snooze):
            return False
        return self.short_key() == other.short_key()

    def __repr__(self) -> str:
        """Return a string representation of the object."""
        return f"Snooze({self.target_type}, {self.target}, {self.snoozed_at})"

    def active(self) -> bool:
        if self.snooze_until is not None and self.snooze_until < time.time():
            return False
        return True

    def export(self) -> dict:
        return {
            "target_type": self.target_type,
            "target": self.target,
            "snoozed_at": format_timestamp(self.snoozed_at),
            "snooze_until": format_timestamp(self.snooze_until),
        }
