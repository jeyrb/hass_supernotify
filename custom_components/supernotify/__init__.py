""" The SuperNotification integration """

import logging

DOMAIN = "supernotify"

PLATFORMS = ["notify"]

CONF_ALEXA_SHOW_TARGETS = 'alexa_show_devices'
CONF_ALEXA_TARGETS = 'alexa_devices'
CONF_CHIME_TARGETS = 'chime_devices'
CONF_APPLE_TARGETS = 'apple_devices'
CONF_ACTIONS = 'action_definitions'
CONF_RECIPIENTS = 'recipients'
CONF_RECIPIENT = 'recipients'
CONF_PERSON = 'person'
CONF_SERVICES = 'services'
CONF_SERVICE_SMS = 'sms'
CONF_SERVICE_EMAIL = 'email'
CONF_MOBILE = 'mobile'
CONF_PHONE_NUMBER = 'phone_number'


_LOGGER = logging.getLogger(__name__)
