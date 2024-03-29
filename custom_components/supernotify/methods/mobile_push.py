import logging
import re
import requests
from bs4 import BeautifulSoup

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
    CONF_OPTIONS,
    CONF_PERSON,
    METHOD_MOBILE_PUSH,
    PRIORITY_CRITICAL,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
)
from custom_components.supernotify.delivery_method import DeliveryMethod
from custom_components.supernotify.notification import Envelope

RE_VALID_MOBILE_APP = r"mobile_app_[A-Za-z0-9_]+"

_LOGGER = logging.getLogger(__name__)


class MobilePushDeliveryMethod(DeliveryMethod):
    method = METHOD_MOBILE_PUSH

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.action_titles = {}

    def select_target(self, target):
        return re.fullmatch(RE_VALID_MOBILE_APP, target)

    def validate_service(self, service):
        return service is None

    def recipient_target(self, recipient):
        if CONF_PERSON in recipient:
            services = [md.get(CONF_NOTIFY_SERVICE) for md in recipient.get(CONF_MOBILE_DEVICES, [])]
            return list(filter(None, services))
        else:
            return []

    async def action_title(self, url):
        if url in self.action_titles:
            return self.action_titles[url]
        try:
            resp = requests.get(url, allow_redirects=True, timeout=5)
            html = BeautifulSoup(resp.text)
            self.action_titles[url] = html.title.string
            return html.title.string
        except Exception as e:
            _LOGGER.debug("SUPERNOTIFY failed to retrieve url title at %s: %s", url, e)
            return None

    async def deliver(self, envelope: Envelope) -> None:

        data = envelope.data or {}
        app_url = self.abs_url(envelope.actions.get(ATTR_ACTION_URL))
        if app_url:
            app_url_title = envelope.actions.get(ATTR_ACTION_URL_TITLE) or self.action_title(app_url) or "Click for Action"

        category = data.get(ATTR_ACTION_CATEGORY, "general")
        action_groups = data.get(ATTR_ACTION_GROUPS)

        _LOGGER.info("SUPERNOTIFY notify_mobile: %s -> %s", envelope.title, envelope.targets)

        media = envelope.media or {}
        camera_entity_id = media.get(ATTR_MEDIA_CAMERA_ENTITY_ID)
        clip_url = self.abs_url(media.get(ATTR_MEDIA_CLIP_URL))
        snapshot_url = self.abs_url(media.get(ATTR_MEDIA_SNAPSHOT_URL))
        options = data.get(CONF_OPTIONS, {})

        if envelope.priority == PRIORITY_CRITICAL:
            push_priority = "critical"
        elif envelope.priority == PRIORITY_HIGH:
            push_priority = "time-sensitive"
        elif envelope.priority == PRIORITY_MEDIUM:
            push_priority = "active"
        elif envelope.priority == PRIORITY_LOW:
            push_priority = "passive"
        else:
            push_priority = "active"
            _LOGGER.warning("SUPERNOTIFY Unexpected priority %s", envelope.priority)

        data.setdefault("actions", [])
        data.setdefault("push", {})
        data["push"]["interruption-level"] = push_priority
        if push_priority == "critical":
            data["push"].setdefault("sound", {})
            data["push"]["sound"].setdefault("name", "default")
            data["push"]["sound"]["critical"] = 1
            data["push"]["sound"].setdefault("volume", 1.0)
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
            data["actions"].append({"action": "URI", "title": app_url_title, "uri": app_url})
        if camera_entity_id:
            # TODO generalize and add the actual action
            data["actions"].append(
                {
                    "action": "silence-%s" % camera_entity_id,
                    "title": "Stop camera notifications for %s" % camera_entity_id,
                    "destructive": "true",
                }
            )
        for group, actions in self.context.mobile_actions.items():
            if action_groups is None or group in action_groups:
                data["actions"].extend(actions)
        service_data = envelope.core_service_data()
        service_data[ATTR_DATA] = data

        for mobile_target in envelope.targets:
            await self.call_service(envelope, "notify.%s" % mobile_target, service_data=service_data)


"""
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
"""
