import logging
import re

from homeassistant.components.notify.const import ATTR_DATA, ATTR_TARGET, ATTR_TITLE
from homeassistant.components.supernotify import (
    METHOD_APPLE_PUSH,
    PRIORITY_CRITICAL,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_MEDIUM
)
from homeassistant.components.supernotify.common import DeliveryMethod
from homeassistant.const import CONF_ENTITIES, CONF_SERVICE, CONF_TARGET

RE_VALID_MOBILE_APP = r"mobile_app\.[A-Za-z0-9_]+"

_LOGGER = logging.getLogger(__name__)


class ApplePushDeliveryMethod(DeliveryMethod):
    def __init__(self, *args, **kwargs):
        super().__init__(METHOD_APPLE_PUSH, False, *args, **kwargs)

    def select_target(self, target):
        return re.fullmatch(RE_VALID_MOBILE_APP, target)
    
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
        _LOGGER.info("SUPERNOTIFY notify_apple: %s -> %s", title, targets)

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
        for apple_target in targets:
            try:
                _LOGGER.debug("SUPERNOTIFY notify/%s %s",
                              apple_target, service_data)
                self.hass.services.call("notify", apple_target,
                                        service_data=service_data)
            except Exception as e:
                _LOGGER.error(
                    "SUPERNOTIFY Apple push failure (m=%s): %s", message, e)
        _LOGGER.info("SUPERNOTIFY iOS Push t=%s m=%s d=%s",
                     title, message, data)
