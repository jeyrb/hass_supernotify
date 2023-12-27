from . import (
    DOMAIN,
    CONF_ALEXA_SHOW_TARGETS,
    CONF_ALEXA_TARGETS,
    CONF_SMS_TARGETS,
    CONF_APPLE_TARGETS,
    CONF_ACTIONS
)
import logging

from homeassistant.helpers.script import Script
import voluptuous as vol
from jinja2 import Environment, FileSystemLoader
import os.path
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import entity_registry

from homeassistant.components.notify import (
    ATTR_TARGET,
    ATTR_DATA,
    ATTR_TITLE,
    PLATFORM_SCHEMA,
    BaseNotificationService,
)
from homeassistant.components.ios import PUSH_ACTION_SCHEMA

_LOGGER = logging.getLogger(__name__)
TEMPLATE_DIR = '/config/templates' if os.path.exists(
    '/config/templates') else None
NS_MOBILE_ACTIONS = 'mobile_actions'


_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_ALEXA_TARGETS, default=[]): vol.All(cv.ensure_list, [cv.entity_id]),
        vol.Optional(CONF_ALEXA_SHOW_TARGETS, default=[]): vol.All(cv.ensure_list, [cv.entity_id]),
        vol.Optional(CONF_SMS_TARGETS, default=[]): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(CONF_APPLE_TARGETS, default=[]): vol.All(cv.ensure_list, [cv.entity_id]),
        vol.Optional(CONF_ACTIONS, default=[]): vol.All(cv.ensure_list, [PUSH_ACTION_SCHEMA]),

    }
)


def get_service(hass, config, discovery_info=None):
    hass.states.async_set(
        "%s.configured" % DOMAIN,
        True,
        {
            CONF_ALEXA_TARGETS: config.get(CONF_ALEXA_TARGETS),
            CONF_ALEXA_SHOW_TARGETS: config.get(CONF_ALEXA_SHOW_TARGETS),
            CONF_SMS_TARGETS: config.get(CONF_SMS_TARGETS),
            CONF_APPLE_TARGETS: config.get(CONF_APPLE_TARGETS),
            CONF_ACTIONS: config.get(CONF_ACTIONS)
        },
    )
    return SuperNotificationService(hass,
                                    config[CONF_ALEXA_TARGETS],
                                    config[CONF_ALEXA_SHOW_TARGETS],
                                    config[CONF_SMS_TARGETS],
                                    config[CONF_APPLE_TARGETS],
                                    config[CONF_ACTIONS])


class SuperNotificationService(BaseNotificationService):
    """Implement SuperNotification service."""

    def __init__(self, hass,
                 alexa_targets=(),
                 alexa_show_targets=(),
                 sms_targets=(),
                 apple_targets=(),
                 mobile_actions=()):
        """Initialize the service."""
        self.hass = hass
        self.alexa_devices = alexa_targets
        self.alexa_show_devices = alexa_show_targets
        self.apple_devices = apple_targets
        self.sms_recipients = sms_targets
        self.actions = mobile_actions
        self.all_methods = ['chime', 'email', 'sms', 'alexa', 'apple']

    def send_message(self, message="", **kwargs):
        """Send a message via chosen method."""
        _LOGGER.debug("Message: %s, kwargs: %s", message, kwargs)
        target = kwargs.get(ATTR_TARGET)
        data = kwargs.get(ATTR_DATA)
        title = kwargs.get(ATTR_TITLE)

        snapshot_url = data.get('snapshot_url')
        clip_url = data.get('clip_url')
        methods = data.get('methods')
        if not methods:
            methods = self.all_methods
        else:
            methods = [
                method for method in methods if method in self.all_methods]
        camera_entity_id = data.get('camera_entity_id')

        for method in methods:
            match method:
                case "chime": return self.on_notify_chime(target,
                                                          data.get(
                                                              'chime_repeat', 1),
                                                          data.get('chime_interval', 3))
                case "sms": return self.on_notify_sms(title, message, target)
                case "alexa": return self.on_notify_alexa(message, image_url=snapshot_url)
                case "email": return self.on_notify_email(title, message,
                                                          html=data.get(
                                                              'html'),
                                                          template=data.get('template'))
                case "apple": return self.on_notify_apple(title, message, target,
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
                                                          camera_entity_id=camera_entity_id)
                case _:
                    _LOGGER.warn('SUPERNOTIFY unhandled notify %s' %
                                 event_type)
                    return None

    def on_notify_apple(self, title, message, target,
                        category='general',
                        push_priority='time-sensitive',  # passive, active, critical
                        device=None,
                        snapshot_url=None, clip_url=None,
                        app_url=None, app_url_title=None,
                        camera_entity_id=None):
        target = target or self.apple_devices
        title = title or ''
        _LOGGER.info('SUPERNOTIFY notify_apple: %s -> %s' % (title, target))

        data = {}
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
        data['actions'].extend(self.shared_actions())
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

    def shared_actions(self):
        actions = []
        for entity in entity_registry.entities:
            if entity.domain == 'mobile_action':
                actions.append({
                    'action': entity.get_state(attribute='action'),
                    'title': entity.get_state(attribute='title'),
                    'icon': entity.get_state(attribute='icon'),
                    'destructive': entity.get_state(attribute='destructive'),

                })
        return actions

    def on_notify_email(self, title, message, html=None, template=None):
        _LOGGER.info('SUPERNOTIFY notify_email: %s' % title)
        try:
            if template:
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
                env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
                template_obj = env.get_template(template)
                html = template_obj.render(alert=alert)
                if not html:
                    self.error('Empty result from template %s' % template)
            service_data = {
                'title': title,
                'message': message,
                'data': {}
            }
            if html:
                service_data['data']['html'] = html
            self.hass.services.call(
                "notify", "smtp", service_data=service_data)
            return html
        except Exception as e:
            _LOGGER.error(
                'SUPERNOTIFY Failed to notify via mail (m=%s): %s' % (message, e))

    def on_notify_alexa(self, message, image_url=None):
        _LOGGER.info('SUPERNOTIFY notify_alexa: %s' % message)
        service_data = {
            'message': message,
            'data': {"type": "announce"},
            'target': self.alexa_devices
        }
        try:
            self.services.call("notify", "alexa", service_data=service_data)
        except Exception as e:
            _LOGGER.error('Failed to notify via Alex (m=%s): %s' %
                          (message, e))
        if self.alexa_show_devices and image_url:
            image_url = image_url.replace(
                'http://10.111.10.100', 'https://dockernuc.internal.barrsofcloak.org')
            try:
                if image_url.startswith('https:'):
                    service_data = {
                        'message': message,
                        'data': {
                            "media_content_id": image_url,
                            "media_content_type": "image"
                        },
                        'target': self.alexa_show_devices
                    }
                    self.hass.services.call(
                        "media_player", "play_media",
                        service_data=service_data
                    )
            except Exception as e:
                _LOGGER.error(
                    'SUPERNOTIFY Failed to notify via Alex Show (url=%s): %s' % (image_url, e))

    def on_notify_sms(self, title, message, target=None):
        _LOGGER.info('SUPERNOTIFY notify_sms: %s' % title)
        target = target or self.sms_recipients
        combined = '%s %s' % (title, message)
        service_data = {
            'message': combined[:158],
            'data': {"type": "announce"},
            'target': target
        }
        try:
            self.hass.services.call(
                "notify", "mikrotik_sms",
                service_data=service_data
            )
        except Exception as e:
            _LOGGER.error(
                'SUPERNOTIFY Failed to notify via SMS (m=%s): %s' % (message, e))

    def on_notify_chime(self, target, chime_repeat=1,
                        chime_interval=3):
        _LOGGER.info('SUPERNOTIFY notify_chime: %s' % target)
        for chime_entity_id in target:
            self.log('SUPERNOTIFY chime %s' % target)
            try:
                sequence = []
                chime_type = chime_entity_id.split('.')[0]
                if chime_type == 'script':
                    domain = 'script'
                    service = 'turn_on'
                else:
                    domain = 'switch'
                    service = 'turn_on'
                service_data = {
                    'entity_id': chime_entity_id
                }
                if chime_repeat == 1:
                    self.hass.services.call(
                        domain, service, service_data=service_data)
                else:
                    raise NotImplementedError("Repeat not implemented")
            except Exception as e:
                _LOGGER.error('SUPERNOTIFY Failed to chime %s: %s' %
                              (chime_entity_id, e))
