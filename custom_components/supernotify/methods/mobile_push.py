import logging
import re

from homeassistant.components.notify.const import ATTR_DATA, ATTR_TITLE
from custom_components.supernotify import (
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

    async def _delivery_impl(self, message=None,
                             title=None,
                             config=None,
                             targets=None,
                             priority=PRIORITY_MEDIUM,
                             data=None,
                             **kwargs) -> bool:
        config = config or {}
        data = data or {}
        app_url = data.get("app_url")
        app_url_title = data.get("app_url_title")
        camera_entity_id = data.get("camera_entity_id")
        clip_url = data.get("clip_url")
        snapshot_url = data.get("snapshot_url")
        category = data.get("category", "general")
        action_groups = data.get("action_groups")

        title = title or ""
        _LOGGER.info("SUPERNOTIFY notify_mobile: %s -> %s", title, targets)

        data = data and data.get(ATTR_DATA) or {}

        if priority == PRIORITY_CRITICAL:
            push_priority = "critical"
        elif priority == PRIORITY_HIGH:
            push_priority = "time-sensitive"
        elif priority == PRIORITY_MEDIUM:
            push_priority = "active"
        elif priority == PRIORITY_LOW:
            push_priority = "passive"
        else:
            push_priority = "active"
            _LOGGER.warning("SUPERNOTIFY Unexpected priority %s", priority)

        data.setdefault("actions", [])
        data.setdefault("push", {})
        data["push"]["interruption-level"] = push_priority
        if push_priority == "critical":
            data["push"].setdefault("sound",{})
            data['push']['sound']['name'] = 'default'
            data['push']['sound']['critical'] = 1
            data['push']['sound']['volume'] = 1.0
        else:
            # critical notifications cant be grouped on iOS
            data.setdefault("group", "%s-%s" %
                            (category, camera_entity_id or "appd"))

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
        service_data = {
            ATTR_TITLE: title,
            "message": message,
            ATTR_DATA: data
        }
        calls = 0
        for mobile_target in targets:
            try:
                _LOGGER.debug("SUPERNOTIFY notify/%s %s",
                              mobile_target, service_data)
                await self.hass.services.async_call("notify", mobile_target,
                                                    service_data=service_data)
                calls +=1
            except Exception as e:
                _LOGGER.error(
                    "SUPERNOTIFY Mobile push failure (m=%s): %s", message, e)
        _LOGGER.info("SUPERNOTIFY Mobile Push t=%s m=%s d=%s",
                     title, message, data)
        return calls > 0


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
