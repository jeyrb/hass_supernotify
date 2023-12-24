import logging

import asyncio
import async_timeout
import voluptuous as vol
from jinja2 import Environment, FileSystemLoader
import os.path
import homeassistant.helpers.config_validation as cv

from homeassistant.components.notify import (
    ATTR_TARGET,
    ATTR_DATA,
    ATTR_TITLE,
    PLATFORM_SCHEMA,
    BaseNotificationService,
)
from homeassistant.components.ios import PUSH_ACTION_SCHEMA

TEMPLATE_DIR='/config/templates' if os.path.exists('/config/templates') else '/addon_configs/a0d7b954_appdaemon/templates'
EVENT_PREFIX='supernotify'
NS_MOBILE_ACTIONS='mobile_actions'

from . import (
    DOMAIN,
    CONF_ALEXA_SHOW_TARGETS,
    CONF_ALEXA_TARGETS,
    CONF_SMS_TARGETS,
    CONF_APPLE_TARGETS,
    CONF_ACTIONS
)

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

METHODS=['chime','email','sms','alexa','apple']

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
        self.alexa_devices=alexa_targets
        self.alexa_show_devices=alexa_show_targets
        self.apple_devices=apple_targets
        self.sms_recipients=sms_targets
        self.actions=mobile_actions

    def send_message(self, message="", **kwargs):
        """Send a message via chosen method."""
        _LOGGER.debug("Message: %s, kwargs: %s", message, kwargs)
        target = kwargs.get(ATTR_TARGET)
        data = kwargs.get(ATTR_DATA)
        title = kwargs.get(ATTR_TITLE)
        event_type = kwargs.get('method')
        if not target:
            _LOGGER.info("At least 1 target is required")
            return

        extra_data = data.get('data',{})
        snapshot_url = extra_data.get('snapshot_url')    
        clip_url = extra_data.get('clip_url')    
        camera_entity_id=extra_data.get('camera_entity_id')
        
        match event_type:
            case "chime":   return self.on_notify_chime(target,
                                                      extra_data.get('chime_repeat',1),
                                                      extra_data.get('chime_interval',3))   
            case "sms":     return self.on_notify_sms(title,message,target)
            case "alexa":   return self.on_notify_alexa(message,image_url=snapshot_url)
            case "email":   return self.on_notify_email(title,message,
                                                        html=extra_data.get('html'),
                                                        template=extra_data.get('template'))
            case "apple":   return self.on_notify_apple( title, message, target,
                                                        category=extra_data.get('category','general'), 
                                                        push_priority=extra_data.get('push_priority','time-sensitive'),
                                                        snapshot_url=snapshot_url, 
                                                        clip_url=clip_url,
                                                        app_url=extra_data.get('app_url'),
                                                        app_url_title=extra_data.get('app_url_title'),
                                                        camera_entity_id=camera_entity_id)
            case _: 
                self.log('SUPERNOTIFY unhandled notify %s' % event_type)
                return None
             

    def on_notify_apple(self, title, message, target, 
                        category='general', 
                        push_priority='time-sensitive', # passive, active, critical
                        device=None, 
                        snapshot_url=None, clip_url=None, 
                        app_url=None, app_url_title=None,
                        camera_entity_id=None):
        target = target or self.apple_devices
        title = title or ''
        self.log('SUPERNOTIFY notify_apple: %s -> %s' % (title,target))
           

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
                                    'title': action.get('title',action['action']),
                                    'icon' : action.get('icon'),
                                    'destructive': action.get('destructive',False)
                                    })
        data['actions'].extend(self.shared_actions())
        service_data={
            'title'     : title,
            'message'   : message,
            'data'      : data
        }
        for apple_target in target:
            try:
                self.hass.services.call("notify",apple_target, 
                                        service_data=service_data)
            except Exception as e:
                self.error('SUPERNOTIFY Apple push failure (m=%s): %s' % (message, e))
        self.log('SUPERNOTIFY iOS Push t=%s m=%s d=%s' % (title, message, data))


    def shared_actions(self):
        actions=[]
        if NS_MOBILE_ACTIONS not in self.list_namespaces():
            self.log('SUPERNOTIFY %s namespace not configured in appdaemon.yaml so actions not shared across apps' % NS_MOBILE_ACTIONS)
        else:
            for entity_name in self.AD.state.list_namespace_entities(NS_MOBILE_ACTIONS):
                entity=self.get_entity(entity_name,namespace=NS_MOBILE_ACTIONS)
                actions.append({
                            'action'        : entity.get_state(attribute='action'),
                            'title'         : entity.get_state(attribute='title'),
                            'icon'          : entity.get_state(attribute='icon'),
                            'destructive'   : entity.get_state(attribute='destructive'),
                    
                })
        return actions
            
        
    def on_notify_email(self, title, message, html=None,template=None):
        self.log('SUPERNOTIFY notify_email: %s' % title)
        try:
            if template:
                alert={'title'      : title,
                       'message'    : message,
                       'subheading' : 'Home Assistant Notification',
                       'site'       : 'Barrs of Cloak',
                       'level'      : 'WARNING',
                       'details_url': 'https://home.barrsofcloak.org',
                       'server'     : {
                           'url'    : 'https://home.barrsofcloak.org:8123',
                           'domain' : 'home.barrsofcloak.org'
                           
                       },
                       'img'        : {
                           'text'   : "Driveway CCTV capture",
                           'url'    : "http://10.111.10.100/cctv/Driveway/20231125085811471_SL13UKK_VEHICLE_DETECTION.jpg"
                       }
                }
                env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
                template_obj = env.get_template(template)
                html=template_obj.render(alert=alert)
                if not html:
                    self.error('Empty result from template %s' % template)
            service_data={
                'title'     : title,
                'message'   : message,
                'data'      : {}
            }   
            if html:
                service_data['data']['html']=html
            self.hass.services.call(
                    "notify","email", service_data=service_data)
            return html
        except Exception as e:
            self.error('SUPERNOTIFY Failed to notify via mail (m=%s): %s' % (message, e))

    def _service_check(self, *args, **kwargs):
        self.log('SUPERNOTIFY Service result %s %s' % (args, kwargs))

    def on_notify_alexa(self, message, image_url=None):
        self.log('SUPERNOTIFY notify_alexa: %s' % message)
        try:
            self.call_service(
                "notify/alexa",
                message=message,
                data={"type": "announce"},
                target=self.alexa_devices,
                callback=self._service_check
            )
        except Exception as e:
            self.error('Failed to notify via Alex (m=%s): %s' % (message, e))
        if self.alexa_show_devices and image_url:
            image_url=image_url.replace('http://10.111.10.100','https://dockernuc.internal.barrsofcloak.org')
            try:
                if image_url.startswith('https:'):
                    self.call_service(
                        "media_player/play_media",
                        message=message,
                        data={"media_content_id": image_url,
                            "media_content_type": "image"},
                        target=self.alexa_show_devices,
                        callback=self._service_check
                    )
            except Exception as e:
                self.error('SUPERNOTIFY Failed to notify via Alex Show (url=%s): %s' % (image_url, e))

    def on_notify_sms(self, title, message, target=None):
        self.log('SUPERNOTIFY notify_sms: %s' % title)
        target = target or self.sms_recipients
        try:
            combined = '%s %s' % (title, message)
            self.call_service(
                "notify/mikrotik_sms",
                message=combined[:158],
                target=target,
                callback=self._service_check
            )
        except Exception as e:
            self.error('SUPERNOTIFY Failed to notify via SMS (m=%s): %s' % (message, e))

    def on_notify_chime(self, target, chime_repeat=1, 
                chime_interval=3):
        self.log('SUPERNOTIFY notify_chime: %s' % target)
        for chime_entity_id in target:
            self.log('SUPERNOTIFY chime %s' % target)
            try:
                sequence = []
                chime_type = chime_entity_id.split('.')[0]
                if chime_type == 'script':
                    service = 'script/turn_on'
                else:
                    service = 'switch/turn_on'
                if chime_repeat == 1:
                    self.call_service(
                        service, entity_id=chime_entity_id, callback=self._service_check)
                else:
                    for _ in range(0, chime_repeat):
                        if len(sequence):
                            sequence.append({'sleep': '%s' % chime_interval})
                        sequence.append(
                            {service: {'entity_id': chime_entity_id}})
                    self.log('SUPERNOTIFY run sequence--> %s' % sequence)
                    self.run_sequence(sequence)
            except Exception as e:
                self.error('SUPERNOTIFY Failed to chime %s: %s' % (chime_entity_id, e))



