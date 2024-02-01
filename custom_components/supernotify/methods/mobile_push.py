import logging
import re

from homeassistant.components.notify.const import ATTR_DATA
from custom_components.supernotify import (
    ATTR_ACTION_CATEGORY,
    ATTR_ACTION_GROUPS,
    ATTR_ACTION_URL,
    ATTR_ACTION_URL_TITLE,
    ATTR_MEDIA_CAMERA_ENTITY_ID,
    ATTR_MEDIA_CLIP_URL,
    ATTR_MEDIA_SNAPSHOT_URL,
    CONF_MOBILE_DEVICES,
    CONF_NOTIFY_SERVICE,
    CONF_PERSON,
    METHOD_MOBILE_PUSH,
    PRIORITY_CRITICAL,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_MEDIUM
)
from custom_components.supernotify.delivery_method import DeliveryMethod
from custom_components.supernotify.notification import Envelope

RE_VALID_MOBILE_APP = r"mobile_app_[A-Za-z0-9_]+"

_LOGGER = logging.getLogger(__name__)


class MobilePushDeliveryMethod(DeliveryMethod):
    method = METHOD_MOBILE_PUSH

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def select_target(self, target):
        return re.fullmatch(RE_VALID_MOBILE_APP, target)

    def validate_service(self, service):
        return service is None

    def recipient_target(self, recipient):
        if CONF_PERSON in recipient:
            services = [md.get(CONF_NOTIFY_SERVICE)
                        for md in recipient.get(CONF_MOBILE_DEVICES, [])]
            return list(filter(None, services))
        else:
            return []

    async def _delivery_impl(self, envelope: Envelope) -> None:

        data = envelope.data or {}
        app_url = self.abs_url(data.get(ATTR_ACTION_URL))
        app_url_title = data.get(ATTR_ACTION_URL_TITLE)
        
        category = data.get(ATTR_ACTION_CATEGORY, "general")
        action_groups = data.get(ATTR_ACTION_GROUPS)

        _LOGGER.info("SUPERNOTIFY notify_mobile: %s -> %s",
                     envelope.title, envelope.targets)

        data = data and data.get(ATTR_DATA) or {}
        media = envelope.notification.media or {}
        camera_entity_id = media.get(ATTR_MEDIA_CAMERA_ENTITY_ID)
        clip_url = self.abs_url(media.get(ATTR_MEDIA_CLIP_URL))
        snapshot_url = self.abs_url(media.get(ATTR_MEDIA_SNAPSHOT_URL))
        
        if envelope.notification.priority == PRIORITY_CRITICAL:
            push_priority = "critical"
        elif envelope.notification.priority == PRIORITY_HIGH:
            push_priority = "time-sensitive"
        elif envelope.notification.priority == PRIORITY_MEDIUM:
            push_priority = "active"
        elif envelope.notification.priority == PRIORITY_LOW:
            push_priority = "passive"
        else:
            push_priority = "active"
            _LOGGER.warning("SUPERNOTIFY Unexpected priority %s",
                            envelope.notification.priority)

        data.setdefault("actions", [])
        data.setdefault("push", {})
        data["push"]["interruption-level"] = push_priority
        if push_priority == "critical":
            data["push"].setdefault("sound", {})
            data['push']['sound']['name'] = 'default'
            data['push']['sound']['critical'] = 1
            data['push']['sound']['volume'] = 1.0
        else:
            # critical notifications cant be grouped on iOS
            category = category or camera_entity_id or "appd"
            data.setdefault("group", category)

        if camera_entity_id:
            data["entity_id"] = camera_entity_id
            # data['actions'].append({'action':'URI','title':'View Live','uri':'/cameras/%s' % device}
        if clip_url:
            data["video"] = clip_url
        if snapshot_url:
            data["image"] = snapshot_url
        if app_url:
            data["url"] = app_url
            data["actions"].append(
                {"action": "URI", "title": app_url_title, "uri": app_url})
        if camera_entity_id:
            # TODO generalize
            data["actions"].append({"action": "silence-%s" % camera_entity_id,
                                    "title": "Stop camera notifications for %s" % camera_entity_id,
                                    "destructive": "true"})
        for group, actions in self.context.mobile_actions.items():
            if action_groups is None or group in action_groups:
                data["actions"].extend(actions)
        service_data = envelope.core_service_data()
        service_data[ATTR_DATA] = data

        calls = 0
        for mobile_target in envelope.targets:
            try:
                _LOGGER.debug("SUPERNOTIFY notify/%s %s",
                              mobile_target, service_data)
                await self.hass.services.async_call("notify", mobile_target,
                                                    service_data=service_data)
                calls += 1
            except Exception as e:
                _LOGGER.error(
                    "SUPERNOTIFY Mobile push failure (d=%s): %s", service_data, e)
        _LOGGER.info("SUPERNOTIFY Mobile Push, d=%s", service_data)
        if calls > 0:
            envelope.delivered = True


'''
FRIGATE Example

 - device_id: !input notify_device
                            domain: mobile_app
                            type: notify
                            title: "{{title}}"
                            message: "{{message}}"
                            data:
                              tag: "{{ id }}"
                              group: "{{ group }}"
                              color: "{{color}}"
                              # Android Specific
                              subject: "{{subtitle}}"
                              image: "{{base_url}}/api/frigate{{client_id}}/notifications/{{id}}/{{attachment}}{{'&' if '?' in attachment else '?'}}format=android"
                              video: "{{video}}"
                              clickAction: "{{tap_action}}"
                              ttl: 0
                              priority: high
                              notification_icon: "{{icon}}"
                              sticky: "{{sticky}}"
                              channel: "{{'alarm_stream' if critical else channel}}"
                              car_ui: "{{android_auto}}"
                              # iOS Specific
                              subtitle: "{{subtitle}}"
                              url: "{{tap_action}}"
                              attachment:
                                url: "{{base_url}}/api/frigate{{client_id}}/notifications/{{id}}/{{attachment}}"
                              push:
                                sound: "{{sound}}"
                                interruption-level: "{{ iif(critical, 'critical', 'active') }}"
                              entity_id: "{{ios_live_view}}"
                              # Actions
                              actions:
                                - action: URI
                                  title: "{{button_1}}"
                                  uri: "{{url_1}}"
                                  icon: "{{icon_1}}"
                                - action: URI
                                  title: "{{button_2}}"
                                  uri: "{{url_2}}"
                                  icon: "{{icon_2}}"
                                - action: "{{ 'URI' if '/' in url_3 else url_3 }}"
                                  title: "{{button_3}}"
                                  uri: "{{url_3}}"
                                  icon: "{{icon_3}}"
                                  destructive: true
'''
