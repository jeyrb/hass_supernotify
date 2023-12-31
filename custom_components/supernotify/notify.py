import logging
import os.path

from jinja2 import Environment, FileSystemLoader
import voluptuous as vol

from homeassistant.components.ios import PUSH_ACTION_SCHEMA
from homeassistant.components.notify import (
    ATTR_DATA,
    ATTR_TARGET,
    ATTR_TITLE,
    PLATFORM_SCHEMA,
    BaseNotificationService,
)
from homeassistant.const import (
    CONF_DESCRIPTION,
    CONF_DEVICE,
    CONF_DEVICES,
    CONF_EMAIL,
    CONF_ENTITIES,
    CONF_ICON,
    CONF_NAME,
    CONF_PLATFORM,
    CONF_SERVICE,
    CONF_URL,
    Platform,
)
from homeassistant.helpers import entity_registry as er
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.reload import setup_reload_service

from . import (
    CONF_ACTIONS,
    CONF_APPLE_TARGETS,
    CONF_LINKS,
    CONF_METHOD,
    CONF_METHOD_LIST,
    CONF_METHOD_ALEXA,
    CONF_METHOD_CHIME,
    CONF_METHOD_EMAIL,
    CONF_METHOD_APPLE_PUSH,
    CONF_METHOD_MEDIA,
    CONF_METHOD_SMS,
    CONF_METHODS,
    CONF_MOBILE,
    CONF_PERSON,
    CONF_PHONE_NUMBER,
    CONF_RECIPIENTS,
    CONF_TEMPLATE,
    CONF_TEMPLATES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.NOTIFY]

_LOGGER = logging.getLogger(__name__)

MOBILE_SCHEMA = {
    vol.Optional(CONF_PHONE_NUMBER): cv.string,
    vol.Optional(CONF_APPLE_TARGETS): vol.All(cv.ensure_list, [cv.string]),
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
    vol.Optional(CONF_MOBILE):  MOBILE_SCHEMA
}
METHOD_SCHEMA = {
    vol.Required(CONF_METHOD): vol.In(CONF_METHOD_LIST),
    vol.Optional(CONF_SERVICE): cv.service,
    vol.Optional(CONF_PLATFORM): cv.string,
    vol.Optional(CONF_TEMPLATE): cv.string,
    vol.Optional(CONF_ENTITIES): vol.All(cv.ensure_list, [cv.entity_id])
}
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_TEMPLATES, default='config/templates/supernotify'): cv.path,
        vol.Optional(CONF_METHODS, default=[]): vol.All(cv.ensure_list, [METHOD_SCHEMA]),
        vol.Optional(CONF_ACTIONS, default=[]): vol.All(cv.ensure_list, [PUSH_ACTION_SCHEMA]),
        vol.Optional(CONF_RECIPIENTS, default=[]): vol.All(cv.ensure_list, [RECIPIENT_SCHEMA]),
        vol.Optional(CONF_LINKS, default=[]): vol.All(cv.ensure_list, [LINK_SCHEMA])
    }
)


def get_service(hass, config, discovery_info=None):
    hass.states.async_set(
        "%s.configured" % DOMAIN,
        True,
        {
            CONF_METHODS: config.get(CONF_METHODS),
            CONF_LINKS: config.get(CONF_LINKS),
            CONF_TEMPLATES: config.get(CONF_TEMPLATES),
            CONF_RECIPIENTS: config.get(CONF_RECIPIENTS),
            CONF_ACTIONS: config.get(CONF_ACTIONS)
        },
    )
    setup_reload_service(hass, DOMAIN, PLATFORMS)
    return SuperNotificationService(hass,
                                    config[CONF_METHODS],
                                    config[CONF_TEMPLATES],
                                    config[CONF_RECIPIENTS],
                                    config[CONF_ACTIONS],
                                    config[CONF_LINKS])


class SuperNotificationService(BaseNotificationService):
    """Implement SuperNotification service."""

    def __init__(self, hass,
                 methods=None,
                 templates=None,
                 recipients=(),
                 mobile_actions=(),
                 links=()):
        """Initialize the service."""
        self.hass = hass
        self.recipients = recipients
        self.templates = templates
        self.actions = mobile_actions
        self.links = links
        self.methods = {m['method']: m for m in methods}
        _LOGGER.info('SUPERNOTIFY configured methods %s' %
                     ';'.join(self.methods.keys()))
        if not os.path.exists(templates):
            _LOGGER.warning(
                'SUPERNOTIFY template directory not found at %s' % templates)

    def send_message(self, message="", **kwargs):
        """Send a message via chosen method."""
        _LOGGER.debug("Message: %s, kwargs: %s", message, kwargs)
        target = kwargs.get(ATTR_TARGET)
        if isinstance(target, str):
            target = [target]
        data = kwargs.get(ATTR_DATA) or {}
        title = kwargs.get(ATTR_TITLE)

        snapshot_url = data.get('snapshot_url')
        clip_url = data.get('clip_url')
        methods = data.get('methods')
        if not methods:
            methods = self.methods.keys()
        else:
            methods = [
                method for method in methods if method in self.methods]
        camera_entity_id = data.get('camera_entity_id')

        stats_methods = stats_errors = 0

        for method in methods:
            if method == CONF_METHOD_CHIME:
                try:
                    self.on_notify_chime(target,
                                         data.get(
                                             'chime_repeat', 1),
                                         data.get('chime_interval', 3),
                                         data=data.get('chime', None))
                except Exception as e:
                    stats_errors += 1
                    _LOGGER.warning(
                        'SUPERNOTIFY Failed to chime %s: %s' % (target, e))
            if method == CONF_METHOD_SMS:
                try:
                    self.on_notify_sms(
                        title, message, target=target, data=data.get('sms', None))
                    stats_methods += 1
                except Exception as e:
                    stats_errors += 1
                    _LOGGER.warning(
                        'SUPERNOTIFY Failed to sms %s: %s' % (target, e))
            if method == CONF_METHOD_ALEXA:
                try:
                    self.on_notify_alexa(
                        message, data=data.get('alexa', None))
                    stats_methods += 1
                except Exception as e:
                    stats_errors += 1
                    _LOGGER.warning(
                        'SUPERNOTIFY Failed to call alexa %s: %s' % (target, e))
            if method == CONF_METHOD_MEDIA:
                try:
                    self.on_notify_media_player(
                        message, image_url=snapshot_url, data=data.get('media', None))
                    stats_methods += 1
                except Exception as e:
                    stats_errors += 1
                    _LOGGER.warning(
                        'SUPERNOTIFY Failed to call media player %s: %s' % (target, e))
            if method == CONF_METHOD_EMAIL:
                try:
                    self.on_notify_email(title, message,
                                         html=data.get(
                                             'html'),
                                         template=data.get('template'),
                                         data=data.get('email', None))
                    stats_methods += 1
                except Exception as e:
                    stats_errors += 1
                    _LOGGER.warning(
                        'SUPERNOTIFY Failed to email %s: %s' % (target, e))
            if method == CONF_METHOD_APPLE_PUSH:
                try:
                    self.on_notify_apple(title, message, target,
                                         category=data.get(
                                             'category', 'general'),
                                         push_priority=data.get(
                                             'push_priority', 'time-sensitive'),
                                         snapshot_url=snapshot_url,
                                         clip_url=clip_url,
                                         app_url=data.get(
                                             'app_url'),
                                         app_url_title=data.get(
                                             'app_url_title'),
                                         camera_entity_id=camera_entity_id,
                                         data=data.get('apple', None))
                    stats_methods += 1
                except Exception as e:
                    stats_errors += 1
                    _LOGGER.warning(
                        'SUPERNOTIFY Failed to push to apple %s: %s' % (target, e))
        return stats_methods, stats_errors

    def on_notify_apple(self, title, message, target=(),
                        category="general",
                        push_priority='time-sensitive',  # passive, active, critical
                        device=None,
                        snapshot_url=None, clip_url=None,
                        app_url=None, app_url_title=None,
                        camera_entity_id=None,
                        data=None):
        config = self.methods.get(CONF_METHOD_APPLE_PUSH, {})
        if not target:
            target = []
            for recipient in self.recipients:
                target.extend(recipient.get(
                    'mobile', {}).get('apple_devices', []))

        title = title or ''
        _LOGGER.info('SUPERNOTIFY notify_apple: %s -> %s' % (title, target))

        data = data or {}
        data.setdefault('actions', [])
        data.setdefault('push', {})
        data['push']['interruption-level'] = push_priority
        if push_priority == 'critical':
            pass
        #    data['data']['push']['sound']['name'] = 'default'
        #    data['data']['push']['sound']['critical'] = 1
        #    data['data']['push']['sound']['volume'] = 1.0
        else:
            # critical notifications cant be grouped on iOS
            data.setdefault('group', '%s-%s' %
                            (category, camera_entity_id or 'appd'))

        if camera_entity_id:
            data['entity_id'] = camera_entity_id
            # data['actions'].append({'action':'URI','title':'View Live','uri':'/cameras/%s' % device}
        if clip_url:
            data['video'] = clip_url
        if snapshot_url:
            data['image'] = snapshot_url
        if app_url:
            data['url'] = app_url
            data['actions'].append(
                {'action': 'URI', 'title': app_url_title, 'uri': app_url})
        if camera_entity_id:
            data['actions'].append({'action': 'silence-%s' % camera_entity_id,
                                    'title': 'Stop camera notifications for %s' % camera_entity_id,
                                    'destructive': 'true'})
        for action in self.actions:
            data['actions'].append({'action': action['action'],
                                    'title': action.get('title', action['action']),
                                    'icon': action.get('icon'),
                                    'destructive': action.get('destructive', False)
                                    })
        data['actions'].extend(self.actions)
        service_data = {
            'title': title,
            'message': message,
            'data': data
        }
        for apple_target in target:
            try:
                self.hass.services.call("notify", apple_target,
                                        service_data=service_data)
            except Exception as e:
                _LOGGER.error(
                    'SUPERNOTIFY Apple push failure (m=%s): %s' % (message, e))
        _LOGGER.info('SUPERNOTIFY iOS Push t=%s m=%s d=%s' %
                     (title, message, data))

    def on_notify_email(self, title, message, target=None, html=None, template=None, data=None):
        _LOGGER.info('SUPERNOTIFY notify_email: %s' % title)
        config = self.methods.get(CONF_METHOD_EMAIL, {})
        template = template or config.get(CONF_TEMPLATE)
        data = data or {}
        if not target:
            target = [recipient.get(
                'email') for recipient in self.recipients if recipient.get('email')]
            if len(target) == 0:
                target is None  # default to SMTP platform default recipients
        try:
            if template:
                template_path = os.path.join(self.templates, 'email')
                alert = {'title': title,
                         'message': message,
                         'subheading': 'Home Assistant Notification',
                         'site': 'Barrs of Cloak',
                         'level': 'WARNING',
                         'details_url': 'https://home.barrsofcloak.org',
                         'server': {
                             'url': 'https://home.barrsofcloak.org:8123',
                             'domain': 'home.barrsofcloak.org'

                         },
                         'img': {
                             'text': "Driveway CCTV capture",
                             'url': "http://10.111.10.100/cctv/Driveway/20231125085811471_SL13UKK_VEHICLE_DETECTION.jpg"
                         }
                         }
                env = Environment(loader=FileSystemLoader(template_path))
                template_obj = env.get_template(template)
                html = template_obj.render(alert=alert)
                if not html:
                    self.error('Empty result from template %s' % template)
            service_data = {
                'title': title,
                'message': message,
                'data': data
            }
            if html:
                service_data['data']['html'] = html

            domain, service = self.methods.get(CONF_METHOD_EMAIL).get(
                CONF_SERVICE, 'notify.smtp').split('.', 1)
            self.hass.services.call(
                domain, service, service_data=service_data)
            return html
        except Exception as e:
            _LOGGER.error(
                'SUPERNOTIFY Failed to notify via mail (m=%s): %s' % (message, e))

    def on_notify_alexa(self, message, target=None, image_url=None, data=None):
        _LOGGER.info('SUPERNOTIFY notify_alexa: %s' % message)
        config = self.methods.get(CONF_METHOD_ALEXA, {})
        if target is None:
            target = config.get(CONF_ENTITIES, [])
        if target is None:
            _LOGGER.debug('SUPERNOTIFY skipping alexa, no targets')
            return

        service_data = {
            'message': message,
            'data': {"type": "announce"},
            'target': target
        }
        if data:
            service_data['data'].update(data)
        try:
            domain, service = self.methods.get(CONF_METHOD_ALEXA).get(
                CONF_SERVICE, 'notify.alexa').split('.', 1)
            self.hass.services.call(
                domain, service, service_data=service_data)
        except Exception as e:
            _LOGGER.error('Failed to notify via Alexa (m=%s): %s' %
                          (message, e))

    def on_notify_media_player(self, message, target=None, image_url=None, data=None):
        _LOGGER.info('SUPERNOTIFY notify media player: %s' % message)
        config = self.methods.get(CONF_METHOD_MEDIA, {})
        if target is None:
            target = config.get(CONF_ENTITIES, [])
        if target is None:
            _LOGGER.debug('SUPERNOTIFY skipping media player, no targets')
            return
        if image_url is None:
            _LOGGER.debug('SUPERNOTIFY skipping media player, no image url')
            return

        service_data = {
            'message': message,
            'data': {
                "media_content_id": image_url,
                "media_content_type": "image"
            },
            'target': self.alexa_show_devices
        }
        if data:
            service_data['data'].update(data)

        if image_url:
            image_url = image_url.replace(
                'http://10.111.10.100', 'https://dockernuc.internal.barrsofcloak.org')
        try:
            domain, service = self.methods.get(
                CONF_METHOD_MEDIA).get(CONF_SERVICE, "media_player.play_media").split('.', 1)
            if image_url.startswith('https:'):
                self.hass.services.call(
                    domain, service,
                    service_data=service_data
                )
        except Exception as e:
            _LOGGER.error(
                'SUPERNOTIFY Failed to notify via media player (url=%s): %s' % (image_url, e))

    def on_notify_sms(self, title, message, target=None, data=None):
        _LOGGER.info('SUPERNOTIFY notify_sms: %s' % title)
        config = self.methods.get(CONF_METHOD_SMS, {})
        data = data or {}
        if not target:
            target = []
            for recipient in self.recipients:
                target.append(recipient.get('mobile', {}).get('number'))
        combined = '%s %s' % (title, message)
        service_data = {
            'message': combined[:158],
            'data': data,
            'target': target
        }
        try:
            domain, service = self.methods.get(
                CONF_METHOD_SMS).get(CONF_SERVICE).split('.', 1)
            self.hass.services.call(
                domain, service,
                service_data=service_data
            )
        except Exception as e:
            _LOGGER.error(
                'SUPERNOTIFY Failed to notify via SMS (m=%s): %s' % (message, e))

    def on_notify_chime(self, target=(), chime_repeat=1,
                        chime_interval=3, data=None):
        config = self.methods.get(CONF_METHOD_CHIME, {})
        entities = config.get(CONF_ENTITIES, []) if not target else target
        data = data or {}
        _LOGGER.info('SUPERNOTIFY notify_chime: %s' % entities)
        for chime_entity_id in entities:
            _LOGGER.debug('SUPERNOTIFY chime %s' % entities)
            try:
                sequence = []  # TODO replace appdaemon sequencing
                chime_type = chime_entity_id.split('.')[0]
                if chime_type == 'script':
                    domain = 'script'
                    service = 'turn_on'
                else:
                    domain = 'switch'
                    service = 'turn_on'
                service_data = {
                    'entity_id': chime_entity_id,
                }
                if chime_repeat == 1:
                    self.hass.services.call(
                        domain, service, service_data=service_data)
                else:
                    raise NotImplementedError("Repeat not implemented")
            except Exception as e:
                _LOGGER.error('SUPERNOTIFY Failed to chime %s: %s' %
                              (chime_entity_id, e))
