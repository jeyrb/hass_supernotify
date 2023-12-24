""" The SuperNotification integration """

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

DOMAIN = "supernotify"

PLATFORMS = ["notify"]
CONF_ALEXA_SHOW_TARGETS='alexa_show_targets'
CONF_ALEXA_TARGETS='alexa_targets'
CONF_SMS_TARGETS='alexa_sms_targets'

_LOGGER = logging.getLogger(__name__)


