""" The SuperNotification integration """

import logging

DOMAIN = "supernotify"

PLATFORMS = ["notify"]

CONF_ALEXA_SHOW_TARGETS='alexa_show_targets'
CONF_ALEXA_TARGETS='alexa_targets'
CONF_SMS_TARGETS='sms_targets'
CONF_APPLE_TARGETS='apple_targets'
CONF_ACTIONS='action_definitions'

_LOGGER = logging.getLogger(__name__)


