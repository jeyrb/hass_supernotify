"""The SuperNotification integration"""

import logging


DOMAIN = "supernotify"

PLATFORMS = ["notify"]

CONF_ALEXA_SHOW_TARGETS = "alexa_show_devices"
CONF_ALEXA_TARGETS = "alexa_devices"
CONF_CHIME_TARGETS = "chime_devices"
CONF_APPLE_TARGETS = "apple_devices"
CONF_ACTIONS = "actions"
CONF_RECIPIENTS = "recipients"
CONF_RECIPIENT = "recipients"
CONF_TEMPLATES = "templates"
CONF_TEMPLATE = "template"
CONF_LINKS = "links"
CONF_PERSON = "person"
CONF_METHOD = "method"
CONF_DELIVERY = "delivery"
CONF_OVERRIDES = "overrides"
CONF_OVERRIDE_BASE = "base"
CONF_OVERRIDE_REPLACE = "replace"

CONF_MOBILE = "mobile"
CONF_PHONE_NUMBER = "phone_number"
CONF_PRIORITY = "priority"
CONF_OCCUPANCY = "occupancy"

OCCUPANCY_ANY_IN = "any_in"
OCCUPANCY_ANY_OUT = "any_out"
OCCUPANCY_ALL_IN = "all_in"
OCCUPANCY_ALL = "all"
OCCUPANCY_NONE = "none"
OCCUPANCY_ALL_OUT = "all_out"
OCCUPANCY_ONLY_IN = "only_in"
OCCUPANCY_ONLY_OUT = "only_out"

ATTR_PRIORITY = "priority"

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
METHOD_APPLE_PUSH = "apple_push"
METHOD_MEDIA = "media"
METHOD_CHIME = "chime"
METHOD_VALUES = [METHOD_SMS, METHOD_ALEXA, METHOD_APPLE_PUSH,
                 METHOD_CHIME, METHOD_EMAIL, METHOD_MEDIA]


_LOGGER = logging.getLogger(__name__)
