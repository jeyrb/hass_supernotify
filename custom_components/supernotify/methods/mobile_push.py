import logging
import re

from homeassistant.components.notify.const import ATTR_DATA, ATTR_TITLE
from custom_components.supernotify import (
    CONF_MOBILE_DEVICES,
    CONF_NOTIFY,
    CONF_PERSON,
    METHOD_MOBILE_PUSH,
    PRIORITY_CRITICAL,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_MEDIUM
)
from custom_components.supernotify.common import DeliveryMethod
from homeassistant.const import CONF_SERVICE

RE_VALID_MOBILE_APP = r"mobile_app_[A-Za-z0-9_]+"

_LOGGER = logging.getLogger(__name__)


class MobilePushDeliveryMethod(DeliveryMethod):
    def __init__(self, *args, **kwargs):
        super().__init__(METHOD_MOBILE_PUSH, False, *args, **kwargs)

    def select_target(self, target):
        return re.fullmatch(RE_VALID_MOBILE_APP, target)

    def recipient_target(self, recipient):
        if CONF_PERSON in recipient:
            services = [md.get(CONF_NOTIFY, {}).get(CONF_SERVICE)
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
                             **kwargs):
        config = config or {}
        app_url = data.get("app_url")
        app_url_title = data.get("app_url_title")
        camera_entity_id = data.get("camera_entity_id")
        clip_url = data.get("clip_url")
        snapshot_url = data.get("snapshot_url")
        category = data.get("category", "general")

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
            pass
        #    data['data']['push']['sound']['name'] = 'default'
        #    data['data']['push']['sound']['critical'] = 1
        #    data['data']['push']['sound']['volume'] = 1.0
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
            data["actions"].append({"action": "silence-%s" % camera_entity_id,
                                    "title": "Stop camera notifications for %s" % camera_entity_id,
                                    "destructive": "true"})
        data["actions"].extend(self.context.mobile_actions)
        service_data = {
            ATTR_TITLE: title,
            "message": message,
            ATTR_DATA: data
        }
        for mobile_target in targets:
            try:
                _LOGGER.debug("SUPERNOTIFY notify/%s %s",
                              mobile_target, service_data)
                await self.hass.services.async_call("notify", mobile_target,
                                                    service_data=service_data)
            except Exception as e:
                _LOGGER.error(
                    "SUPERNOTIFY Mobile push failure (m=%s): %s", message, e)
        _LOGGER.info("SUPERNOTIFY Mobile Push t=%s m=%s d=%s",
                     title, message, data)
