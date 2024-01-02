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
    CONF_EMAIL,
    CONF_ENTITIES,
    CONF_ICON,
    CONF_NAME,
    CONF_PLATFORM,
    CONF_SERVICE,
    CONF_URL,
    Platform,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.reload import setup_reload_service

from . import (
    ATTR_PRIORITY,
    CONF_ACTIONS,
    CONF_APPLE_TARGETS,
    CONF_DELIVERY,
    CONF_LINKS,
    CONF_METHOD,
    CONF_MOBILE,
    CONF_OCCUPANCY,
    CONF_OVERRIDE_BASE,
    CONF_OVERRIDE_REPLACE,
    CONF_OVERRIDES,
    CONF_PERSON,
    CONF_PHONE_NUMBER,
    CONF_PRIORITY,
    CONF_RECIPIENTS,
    CONF_TEMPLATE,
    CONF_TEMPLATES,
    DOMAIN,
    METHOD_ALEXA,
    METHOD_APPLE_PUSH,
    METHOD_CHIME,
    METHOD_EMAIL,
    METHOD_MEDIA,
    METHOD_SMS,
    METHOD_VALUES,
    OCCUPANCY_ALL,
    OCCUPANCY_ALL_IN,
    OCCUPANCY_ALL_OUT,
    OCCUPANCY_ANY_IN,
    OCCUPANCY_ANY_OUT,
    OCCUPANCY_NONE,
    OCCUPANCY_ONLY_IN,
    OCCUPANCY_ONLY_OUT,
    OCCUPANCY_VALUES,
    PRIORITY_CRITICAL,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
    PRIORITY_VALUES,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.NOTIFY]
TEMPLATE_DIR = "/config/templates/supernotify"

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
DELIVERY_SCHEMA = {
    vol.Required(CONF_METHOD): vol.In(METHOD_VALUES),
    vol.Optional(CONF_SERVICE): cv.service,
    vol.Optional(CONF_PLATFORM): cv.string,
    vol.Optional(CONF_TEMPLATE): cv.string,
    vol.Optional(CONF_ENTITIES): vol.All(cv.ensure_list,
                                         [cv.entity_id]),
    vol.Optional(CONF_PRIORITY, default=PRIORITY_VALUES):
        vol.All(cv.ensure_list, [vol.In(PRIORITY_VALUES)]),
    vol.Optional(CONF_OCCUPANCY, default=OCCUPANCY_ALL):
        vol.In(OCCUPANCY_VALUES)
}
OVERRIDE_SCHEMA = {
    vol.Required(CONF_OVERRIDE_BASE): cv.string,
    vol.Required(CONF_OVERRIDE_REPLACE): cv.string
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_TEMPLATES, default=TEMPLATE_DIR):
            cv.path,
        vol.Optional(CONF_DELIVERY, default={}): {cv.string: DELIVERY_SCHEMA},
        vol.Optional(CONF_ACTIONS, default=[]):
            vol.All(cv.ensure_list, [PUSH_ACTION_SCHEMA]),
        vol.Optional(CONF_RECIPIENTS, default=[]):
            vol.All(cv.ensure_list, [RECIPIENT_SCHEMA]),
        vol.Optional(CONF_LINKS, default=[]):
            vol.All(cv.ensure_list, [LINK_SCHEMA]),
        vol.Optional(CONF_OVERRIDES, default={}): {cv.string: OVERRIDE_SCHEMA}
    }
)

MANDATORY_METHOD = [METHOD_EMAIL, METHOD_ALEXA, METHOD_SMS]


def get_service(hass, config, discovery_info=None):
    hass.states.async_set(
        "%s.configured" % DOMAIN,
        True,
        {
            CONF_DELIVERY: config.get(CONF_DELIVERY, {}),
            CONF_LINKS: config.get(CONF_LINKS, ()),
            CONF_TEMPLATES: config.get(CONF_TEMPLATES),
            CONF_RECIPIENTS: config.get(CONF_RECIPIENTS, ()),
            CONF_ACTIONS: config.get(CONF_ACTIONS, ()),
            CONF_OVERRIDES: config.get(CONF_OVERRIDES, {})
        },
    )
    setup_reload_service(hass, DOMAIN, PLATFORMS)
    return SuperNotificationService(hass,
                                    deliveries=config[CONF_DELIVERY],
                                    templates=config[CONF_TEMPLATES],
                                    recipients=config[CONF_RECIPIENTS],
                                    mobile_actions=config[CONF_ACTIONS],
                                    links=config[CONF_LINKS],
                                    overrides=config[CONF_OVERRIDES]
                                    )


class SuperNotificationService(BaseNotificationService):
    """Implement SuperNotification service."""

    def __init__(self, hass,
                 deliveries=None,
                 templates=None,
                 recipients=(),
                 mobile_actions=(),
                 links=(),
                 overrides=None):
        """Initialize the service."""
        self.hass = hass
        self.recipients = recipients
        self.templates = templates
        self.actions = mobile_actions
        self.links = links
        self.overrides = overrides or {}
        deliveries = deliveries or {}
        invalid_deliveries = [k for k, d in deliveries.items() if
                              d["method"] in MANDATORY_METHOD and
                              not d.get(CONF_SERVICE)]
        if invalid_deliveries:
            _LOGGER.warning("SUPERNOTIFY no services defined for "
                            "deliveries %s - DISABLING", invalid_deliveries)
        self.deliveries = {k: d for k, d in deliveries.items()
                           if k not in invalid_deliveries}
        self.people = {r["person"]: r for r in recipients}
        _LOGGER.info("SUPERNOTIFY configured deliveries %s",
                     ";".join(self.deliveries.keys()))
        if templates and not os.path.exists(templates):
            _LOGGER.warning("SUPERNOTIFY template directory not found at %s",
                            templates)
            self.templates = None

    def send_message(self, message="", **kwargs):
        """Send a message via chosen method."""
        _LOGGER.debug("Message: %s, kwargs: %s", message, kwargs)
        target = kwargs.get(ATTR_TARGET) or []
        priority = kwargs.get(ATTR_PRIORITY, PRIORITY_MEDIUM)
        if isinstance(target, str):
            target = [target]
        data = kwargs.get(ATTR_DATA) or {}
        title = kwargs.get(ATTR_TITLE)

        snapshot_url = data.get("snapshot_url")
        clip_url = data.get("clip_url")
        override_delivery = data.get("delivery")
        if not override_delivery:
            deliveries = self.deliveries.keys()
        else:
            deliveries = [
                d for d in override_delivery if d in self.deliveries]
            if override_delivery != deliveries:
                _LOGGER.info("SUPERNOTIFY overriding delivery %s->%s",
                             override_delivery, deliveries)
        camera_entity_id = data.get("camera_entity_id")

        stats_delivieries = stats_errors = 0

        for delivery in deliveries:
            delivery_config = self.deliveries.get(delivery, {})
            if priority not in delivery_config[ATTR_PRIORITY]:
                _LOGGER.debug(
                    "SUPERNOTIFY Skipping delivery %s and priority %s", delivery, priority)
                continue
            method = self.deliveries[delivery]["method"]

            if method == METHOD_CHIME:
                try:
                    self.on_notify_chime(
                        target=target,
                        data=data.get("chime", {}),
                        config=delivery_config)
                except Exception as e:
                    stats_errors += 1
                    _LOGGER.warning(
                        "SUPERNOTIFY Failed to chime %s: %s", delivery, e)
            if method == METHOD_SMS:
                try:
                    self.on_notify_sms(
                        title, message,
                        target=target,
                        data=data.get(delivery, {}),
                        config=delivery_config)
                    stats_delivieries += 1
                except Exception as e:
                    stats_errors += 1
                    _LOGGER.warning(
                        "SUPERNOTIFY Failed to sms %s: %s", delivery, e)
            if method == METHOD_ALEXA:
                try:
                    self.on_notify_alexa(
                        message,
                        target=target,
                        data=data.get(delivery, {}),
                        config=delivery_config)
                    stats_delivieries += 1
                except Exception as e:
                    stats_errors += 1
                    _LOGGER.warning(
                        "SUPERNOTIFY Failed to call alexa %s: %s", delivery, e)
            if method == METHOD_MEDIA:
                try:
                    self.on_notify_media_player(
                        message,
                        target=target,
                        snapshot_url=snapshot_url,
                        data=data.get(delivery, {}),
                        config=delivery_config)
                    stats_delivieries += 1
                except Exception as e:
                    stats_errors += 1
                    _LOGGER.warning(
                        "SUPERNOTIFY Failed to call media player %s: %s", delivery, e)
            if method == METHOD_EMAIL:
                try:
                    self.on_notify_email(message,
                                         title=title,
                                         target=target,
                                         snapshot_url=snapshot_url,
                                         data=data.get(delivery, {}),
                                         config=delivery_config)
                    stats_delivieries += 1
                except Exception as e:
                    stats_errors += 1
                    _LOGGER.warning(
                        "SUPERNOTIFY Failed to call email %s: %s", target, e)
            if method == METHOD_APPLE_PUSH:
                try:
                    self.on_notify_apple(title, message,
                                         target=target,
                                         category=data.get(
                                             "category", "general"),
                                         priority=priority,
                                         snapshot_url=snapshot_url,
                                         clip_url=clip_url,
                                         app_url=data.get(
                                             "app_url"),
                                         app_url_title=data.get(
                                             "app_url_title"),
                                         camera_entity_id=camera_entity_id,
                                         data=data.get(delivery, {}),
                                         config=delivery_config)
                    stats_delivieries += 1
                except Exception as e:
                    stats_errors += 1
                    _LOGGER.warning(
                        "SUPERNOTIFY Failed to push to apple %s: %s", target, e)
        return stats_delivieries, stats_errors

    def first_delivery_for_method(self, method):
        ''' Fall back for custom deliveries '''
        for delivery in self.deliveries:
            if self.deliveries.get(delivery, {}).get("method") == method:
                return self.deliveries[delivery]
        return {}

    def on_notify_apple(self, title, message, target=None,
                        category="general",
                        config=None,
                        priority=PRIORITY_MEDIUM,
                        snapshot_url=None, clip_url=None,
                        app_url=None, app_url_title=None,
                        camera_entity_id=None,
                        data=None):
        config = config or self.first_delivery_for_method(METHOD_APPLE_PUSH)
        mobile_devices = []
        if not target:
            target = []
            for recipient in self.filter_recipients(config.get("occupancy", OCCUPANCY_ALL)):
                mobile_devices.extend(recipient.get(
                    "mobile", {}).get("apple_devices", []))
        else:
            target = [target] if isinstance(target, str) else target
            for t in target:
                if t in self.people:
                    mobile_devices.extend(self.people[t].get(
                        "mobile", {}).get("apple_devices", []))
                else:
                    mobile_devices.append(t)

        title = title or ""
        _LOGGER.info("SUPERNOTIFY notify_apple: %s -> %s", title, target)

        data = data.get(ATTR_DATA) or {}
        if priority == PRIORITY_CRITICAL:
            push_priority = "critical"
        elif priority == PRIORITY_HIGH:
            push_priority = "time-sensitive"
        elif priority == PRIORITY_MEDIUM:
            push_priority = "active"
        elif priority == PRIORITY_LOW:
            push_priority = "passive"
        else:
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
        data["actions"].extend(self.actions)
        service_data = {
            ATTR_TITLE: title,
            "message": message,
            ATTR_DATA: data
        }
        for apple_target in mobile_devices:
            try:
                _LOGGER.debug("SUPERNOTIFY notify/%s %s", apple_target, service_data)
                self.hass.services.call("notify", apple_target,
                                        service_data=service_data)
            except Exception as e:
                _LOGGER.error(
                    "SUPERNOTIFY Apple push failure (m=%s): %s", message, e)
        _LOGGER.info("SUPERNOTIFY iOS Push t=%s m=%s d=%s",
                     title, message, data)

    def on_notify_email(self, message, title=None,
                        image_paths=None,
                        snapshot_url=None,
                        priority=None,
                        config=None, target=None, data=None):
        _LOGGER.info("SUPERNOTIFY notify_email: %s %s", config, target)
        config = config or self.first_delivery_for_method(METHOD_EMAIL)
        template = config.get(CONF_TEMPLATE)
        data = data or {}
        html = data.get("html")
        template = data.get("template", config.get("template"))
        addresses = []
        if not target:
            selected_recipients = self.filter_recipients(
                config.get(CONF_OCCUPANCY, OCCUPANCY_ALL))
            addresses = [recipient.get(
                "email") for recipient in selected_recipients if recipient.get("email")]
            if len(addresses) == 0:
                addresses is None  # default to SMTP platform default recipients
        else:
            for t in target:
                if t in self.people:
                    email = self.people[t].get("email")
                    if email:
                        addresses.append(email)
                elif '@' in t:
                    addresses.append(t)
                else:
                    _LOGGER.warning('SUPERNOTIFY Invalid email address %s', t)

        service_data = {
            'message':   message,
            ATTR_TARGET:   addresses
        }
        if title:
            service_data['title'] = title
        if data.get('data'):
            service_data[ATTR_DATA] = data.get('data')
        try:
            if not template:
                if image_paths:
                    service_data.setdefault("data", {})
                    service_data["data"]["images"] = image_paths
            else:
                template_path = os.path.join(self.templates, "email")
                alert = {"title": title,
                         "message": message,
                         "subheading": "Home Assistant Notification",
                         "site": "Barrs of Cloak",
                         "priority": priority,
                         "details_url": "https://home.barrsofcloak.org",
                         "server": {
                             "url": "https://home.barrsofcloak.org:8123",
                             "domain": "home.barrsofcloak.org"

                         }
                         }
                if snapshot_url:
                    alert['img'] = {
                        "text": "Snapshot Image",
                        "url": snapshot_url
                    }
                env = Environment(loader=FileSystemLoader(template_path))
                template_obj = env.get_template(template)
                html = template_obj.render(alert=alert)
                if not html:
                    self.error("Empty result from template %s" % template)
                else:
                    service_data.setdefault("data", {})
                    service_data["data"]["html"] = html
        except Exception as e:
            _LOGGER.error(
                "SUPERNOTIFY Failed to generate html mail: (data=%s) %s", data, e)
        try:
            domain, service = config.get(CONF_SERVICE).split(".", 1)
            self.hass.services.call(
                domain, service,
                service_data=service_data)
            return html
        except Exception as e:
            _LOGGER.error(
                "SUPERNOTIFY Failed to notify via mail (m=%s,addr=%s): %s", message, addresses, e)

    def on_notify_alexa(self, message, config=None, target=None, data=None):
        _LOGGER.info("SUPERNOTIFY notify_alexa: %s", message)
        config = config or self.first_delivery_for_method(METHOD_ALEXA)
        if target is None:
            target = config.get(CONF_ENTITIES, [])
        if target is None:
            _LOGGER.debug("SUPERNOTIFY skipping alexa, no targets")
            return

        service_data = {
            "message": message,
            ATTR_DATA: {"type": "announce"},
            ATTR_TARGET: target
        }
        if data.get('data'):
            service_data[ATTR_DATA].update(data.get('data'))
        try:
            domain, service = config.get(CONF_SERVICE).split(".", 1)
            self.hass.services.call(
                domain, service, service_data=service_data)
        except Exception as e:
            _LOGGER.error("Failed to notify via Alexa (m=%s): %s", message, e)

    def on_notify_media_player(self, message, config=None, target=None, snapshot_url=None, data=None):
        _LOGGER.info("SUPERNOTIFY notify media player: %s", message)
        config = config or self.first_delivery_for_method(METHOD_MEDIA)
        if target is None:
            target = config.get(CONF_ENTITIES, [])
        if target is None:
            _LOGGER.debug("SUPERNOTIFY skipping media player, no targets")
            return
        if snapshot_url is None:
            _LOGGER.debug("SUPERNOTIFY skipping media player, no image url")
            return

        override_config = self.overrides.get('image_url')
        if override_config:
            new_url = snapshot_url.replace(
                override_config[CONF_OVERRIDE_BASE], override_config[CONF_OVERRIDE_REPLACE])
            _LOGGER.debug(
                "SUPERNOTIFY Overriding image url from %s to %s", snapshot_url, new_url)
            image_url = new_url

        service_data = {
            "media_content_id": image_url,
            "media_content_type": "image",
            'entity_id': target
        }
        if data.get('data'):
            service_data['extra']=data.get('data')

        try:
            domain, service = config.get(
                CONF_SERVICE, "media_player.play_media").split(".", 1)
            if image_url.startswith("https:"):
                self.hass.services.call(
                    domain, service,
                    service_data=service_data
                )
        except Exception as e:
            _LOGGER.error(
                "SUPERNOTIFY Failed to notify via media player (url=%s): %s", image_url, e)

    def on_notify_sms(self, title, message, config=None, target=None, data=None):
        """Send an SMS notification."""
        _LOGGER.info("SUPERNOTIFY notify_sms: %s", title)
        config = config or self.first_delivery_for_method(METHOD_SMS)
        data = data or {}
        mobile_numbers = []
        if not target:
            for recipient in self.filter_recipients(config.get("occupancy", OCCUPANCY_ALL)):
                mobile_numbers.append(
                    recipient.get("mobile", {}).get("number"))
        else:
            for t in target:
                if t in self.people:
                    try:
                        mobile_numbers.append(
                            self.people[t]["mobile"]["number"])
                    except Exception as _:
                        _LOGGER.debug(
                            "SUPERNOTIFY skipping target without mobile number %s", t)
                elif t and not t.startswith("person."):
                    mobile_numbers.append(t)
                else:
                    _LOGGER.debug(
                        "SUPERNOTIFY skipping unknown target %s", t)

        combined = f"{title} {message}"
        service_data = {
            "message": combined[:158],
            ATTR_TARGET: mobile_numbers
        }
        if data.get('data'):
            service_data[ATTR_DATA] = data.get('data')
        try:
            domain, service = config.get(CONF_SERVICE).split(".", 1)
            self.hass.services.call(
                domain, service,
                service_data=service_data
            )
        except Exception as e:
            _LOGGER.error(
                "SUPERNOTIFY Failed to notify via SMS (m=%s): %s", message, e)

    def on_notify_chime(self, config=None, target=None, data=None):
        config = config or self.first_delivery_for_method(METHOD_CHIME)
        data = data or {}
        entities = config.get(CONF_ENTITIES, []) if not target else target
        chime_repeat = data.get("chime_repeat", 1)
        chime_interval = data.get("chime_interval", 3)
        data = data or {}
        _LOGGER.info("SUPERNOTIFY notify_chime: %s", entities)
        for chime_entity_id in entities:
            _LOGGER.debug("SUPERNOTIFY chime %s", entities)
            try:
                sequence = []  # TODO replace appdaemon sequencing
                chime_type = chime_entity_id.split(".")[0]
                if chime_type == "script":
                    domain = "script"
                    service = "turn_on"
                else:
                    domain = "switch"
                    service = "turn_on"
                service_data = {
                    "entity_id": chime_entity_id,
                }
                if chime_repeat == 1:
                    self.hass.services.call(
                        domain, service, service_data=service_data)
                else:
                    raise NotImplementedError("Repeat not implemented")
            except Exception as e:
                _LOGGER.error("SUPERNOTIFY Failed to chime %s: %s",
                              chime_entity_id, e)

    def filter_recipients(self, occupancy):
        at_home = []
        away = []
        try:
            for r in self.recipients:
                tracker = self.hass.states.get(r["person"])
                if tracker is not None and tracker.state == "home":
                    at_home.append(r)
                else:
                    away.append(r)
        except Exception as e:
            _LOGGER.warning(
                "Unable to determine occupied status for %s: %s", r["person"], e)
        if occupancy == OCCUPANCY_ALL_IN:
            return self.recipients if len(away) == 0 else []
        elif occupancy == OCCUPANCY_ALL_OUT:
            return self.recipients if len(at_home) == 0 else []
        elif occupancy == OCCUPANCY_ANY_IN:
            return self.recipients if len(at_home) > 0 else []
        elif occupancy == OCCUPANCY_ANY_OUT:
            return self.recipients if len(away) > 0 else []
        elif occupancy == OCCUPANCY_ONLY_IN:
            return at_home
        elif occupancy == OCCUPANCY_ONLY_OUT:
            return away
        elif occupancy == OCCUPANCY_ALL:
            return self.recipients
        elif occupancy == OCCUPANCY_NONE:
            return []
        else:
            _LOGGER.warning(
                "SUPERNOTIFY Unknown occupancy tested: %s" % occupancy)
            return []
