import logging
import os.path

from jinja2 import Environment, FileSystemLoader
import voluptuous as vol
from homeassistant.helpers.reload import setup_reload_service
from homeassistant.components.ios import PUSH_ACTION_SCHEMA
from homeassistant.components.notify import (
    ATTR_DATA,
    ATTR_TARGET,
    ATTR_TITLE,
    PLATFORM_SCHEMA,
    BaseNotificationService,
)
from homeassistant.const import (
    CONF_DEVICE,
    CONF_DEVICES,
    CONF_EMAIL,
    Platform
)
from homeassistant.helpers import entity_registry as er
import homeassistant.helpers.config_validation as cv

from . import (
    CONF_ACTIONS,
    CONF_ALEXA_SHOW_TARGETS,
    CONF_ALEXA_TARGETS,
    CONF_APPLE_TARGETS,
    CONF_CHIME_TARGETS,
    CONF_RECIPIENTS,
    CONF_SERVICES,
    CONF_SERVICE_EMAIL,
    CONF_SERVICE_SMS,
    CONF_PHONE_NUMBER,
    CONF_PERSON,
    CONF_MOBILE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)
TEMPLATE_DIR = 'config/templates/supernotify' if os.path.exists(
    'config/templates/supernotify') else None

PLATFORMS = [Platform.NOTIFY]

_LOGGER = logging.getLogger(__name__)

MOBILE_SCHEMA = {
    vol.Optional(CONF_PHONE_NUMBER): cv.string,
    vol.Optional(CONF_APPLE_TARGETS): vol.All(cv.ensure_list, [cv.string]),
}

RECIPIENT_SCHEMA = {
    vol.Required(CONF_PERSON): cv.entity_id,
    vol.Optional(CONF_EMAIL): cv.string,
    vol.Optional(CONF_MOBILE):  MOBILE_SCHEMA
}
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_SERVICES, default={}): {vol.Exclusive(CONF_SERVICE_EMAIL, CONF_SERVICE_SMS): cv.string},
        vol.Optional(CONF_CHIME_TARGETS, default=[]): vol.All(cv.ensure_list, [cv.entity_id]),
        vol.Optional(CONF_ALEXA_TARGETS, default=[]): vol.All(cv.ensure_list, [cv.entity_id]),
        vol.Optional(CONF_ALEXA_SHOW_TARGETS, default=[]): vol.All(cv.ensure_list, [cv.entity_id]),
        vol.Optional(CONF_ACTIONS, default=[]): vol.All(cv.ensure_list, [PUSH_ACTION_SCHEMA]),
        vol.Optional(CONF_RECIPIENTS, default=[]): vol.All(cv.ensure_list, [RECIPIENT_SCHEMA])
    }
)


def get_service(hass, config, discovery_info=None):
    hass.states.async_set(
        "%s.configured" % DOMAIN,
        True,
        {
            CONF_SERVICES: config.get(CONF_SERVICES),
            CONF_CHIME_TARGETS: config.get(CONF_CHIME_TARGETS),
            CONF_ALEXA_TARGETS: config.get(CONF_ALEXA_TARGETS),
            CONF_ALEXA_SHOW_TARGETS: config.get(CONF_ALEXA_SHOW_TARGETS),
            CONF_RECIPIENTS: config.get(CONF_RECIPIENTS),
            CONF_ACTIONS: config.get(CONF_ACTIONS)
        },
    )
    setup_reload_service(hass, DOMAIN, PLATFORMS)
    return SuperNotificationService(hass,
                                    config[CONF_SERVICES],
                                    config[CONF_CHIME_TARGETS],
                                    config[CONF_ALEXA_TARGETS],
                                    config[CONF_ALEXA_SHOW_TARGETS],
                                    config[CONF_RECIPIENTS],
                                    config[CONF_ACTIONS])


class SuperNotificationService(BaseNotificationService):
    """Implement SuperNotification service."""

    def __init__(self, hass,
                 services=None,
                 chime_targets=(),
                 alexa_targets=(),
                 alexa_show_targets=(),
                 recipients=(),
                 mobile_actions=()):
        """Initialize the service."""
        self.hass = hass
        self.chime_devices = chime_targets
        self.alexa_devices = alexa_targets
        self.alexa_show_devices = alexa_show_targets
        self.recipients = recipients
        self.actions = mobile_actions
        self.services = services or {}
        self.all_methods = ['chime', 'alexa', 'apple']
        if services.get(CONF_SERVICE_EMAIL):
            self.all_methods.append('email')
        else:
            _LOGGER.warning(
                'SUPERNOTIFY Disabling email since no service defined')
        if services.get(CONF_SERVICE_SMS):
            self.all_methods.append('sms')
        else:
            _LOGGER.info('SUPERNOTIFY Disabling sms since no service defined')

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
            methods = self.all_methods
        else:
            methods = [
                method for method in methods if method in self.all_methods]
        camera_entity_id = data.get('camera_entity_id')

        for method in methods:
            match method:
                case "chime":
                    try:
                        self.on_notify_chime(target,
                                             data.get(
                                                 'chime_repeat', 1),
                                             data.get('chime_interval', 3),
                                             data=data.get('chime', None))
                    except Exception as e:
                        _LOGGER.warning(
                            'SUPERNOTIFY Failed to chime %s: %s' % (target, e))
                case "sms":
                    try:
                        self.on_notify_sms(
                            title, message, target=target, data=data.get('sms', None))
                    except Exception as e:
                        _LOGGER.warning(
                            'SUPERNOTIFY Failed to sms %s: %s' % (target, e))
                case "alexa":
                    try:
                        self.on_notify_alexa(
                            message, image_url=snapshot_url, data=data.get('alexa', None))
                    except Exception as e:
                        _LOGGER.warning(
                            'SUPERNOTIFY Failed to call alexa %s: %s' % (target, e))
                case "email":
                    try:
                        self.on_notify_email(title, message,
                                             html=data.get(
                                                 'html'),
                                             template=data.get('template'),
                                             data=data.get('email', None))
                    except Exception as e:
                        _LOGGER.warning(
                            'SUPERNOTIFY Failed to email %s: %s' % (target, e))
                case "apple":
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
                    except Exception as e:
                        _LOGGER.warning(
                            'SUPERNOTIFY Failed to push to apple %s: %s' % (target, e))
                case _:
                    _LOGGER.warning("SUPERNOTIFY unhandled notify %s" %
                                    method)

    def on_notify_apple(self, title, message, target=(),
                        category="general",
                        push_priority='time-sensitive',  # passive, active, critical
                        device=None,
                        snapshot_url=None, clip_url=None,
                        app_url=None, app_url_title=None,
                        camera_entity_id=None,
                        data=None):
        if not target:
            target = []
            for recipient in self.recipients:
                target.extend(recipient.get('mobile',{}).get('apple_devices',[]))

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
        service = self.services.get(CONF_SERVICE_EMAIL)
        data = data or {}
        if not target:
            target = [recipient.get(
                'email') for recipient in self.recipients if recipient.get('email')]
            if len(target) == 0:
                target is None  # default to SMTP platform default recipients
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
                'data': data
            }
            if html:
                service_data['data']['html'] = html
            self.hass.services.call(
                "notify", service, service_data=service_data)
            return html
        except Exception as e:
            _LOGGER.error(
                'SUPERNOTIFY Failed to notify via mail (m=%s): %s' % (message, e))

    def on_notify_alexa(self, message, target=None, image_url=None, data=None):
        _LOGGER.info('SUPERNOTIFY notify_alexa: %s' % message)
        if target is None:
            target = self.alexa_devices
        if target is None:
            target = self.alexa_show_devices
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

    def on_notify_sms(self, title, message, target=None, data=None):
        _LOGGER.info('SUPERNOTIFY notify_sms: %s' % title)
        service = self.services.get(CONF_SERVICE_SMS)
        data = data or {}
        if not target:
            target = []
            for recipient in self.recipients:
                target.append(recipient.get('mobile',{}).get('number'))
        combined = '%s %s' % (title, message)
        service_data = {
            'message': combined[:158],
            'data': data,
            'target': target
        }
        try:
            self.hass.services.call(
                "notify", service,
                service_data=service_data
            )
        except Exception as e:
            _LOGGER.error(
                'SUPERNOTIFY Failed to notify via SMS (m=%s): %s' % (message, e))

    def on_notify_chime(self, target=(), chime_repeat=1,
                        chime_interval=3, data=None):
        entities = self.chime_devices if not target else target
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
                    'data': data
                }
                if chime_repeat == 1:
                    self.hass.services.call(
                        domain, service, service_data=service_data)
                else:
                    raise NotImplementedError("Repeat not implemented")
            except Exception as e:
                _LOGGER.error('SUPERNOTIFY Failed to chime %s: %s' %
                              (chime_entity_id, e))
