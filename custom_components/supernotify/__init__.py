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
CONF_TEMPLATES = 'templates'
CONF_TEMPLATE = 'template'
CONF_LINKS = 'links'
CONF_PERSON = 'person'
CONF_METHODS = 'methods'
CONF_METHOD = 'method'
CONF_METHOD_SMS = 'sms'
CONF_METHOD_EMAIL = 'email'
CONF_METHOD_ALEXA = 'alexa'
CONF_METHOD_APPLE_PUSH = 'apple_push'
CONF_METHOD_MEDIA = 'media'
CONF_METHOD_CHIME = 'chime'
CONF_MOBILE = 'mobile'
CONF_PHONE_NUMBER = 'phone_number'

CONF_METHOD_LIST = (CONF_METHOD_SMS, CONF_METHOD_ALEXA, CONF_METHOD_APPLE_PUSH,
                    CONF_METHOD_CHIME, CONF_METHOD_EMAIL, CONF_METHOD_MEDIA)


_LOGGER = logging.getLogger(__name__)
