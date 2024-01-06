import logging
from homeassistant.components.notify.const import ATTR_DATA, ATTR_TARGET
import os.path
from jinja2 import Environment, FileSystemLoader
from homeassistant.components.supernotify import CONF_OCCUPANCY, CONF_TEMPLATE, METHOD_EMAIL, OCCUPANCY_ALL
from homeassistant.const import CONF_SERVICE
from homeassistant.components.supernotify.common import DeliveryMethod
import re
RE_VALID_EMAIL = r"([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+"

_LOGGER = logging.getLogger(__name__)


class EmailDeliveryMethod(DeliveryMethod):
    def __init__(self, *args, **kwargs):
        super().__init__( METHOD_EMAIL, True, *args, **kwargs)

    def _delivery_impl(self, message=None,
                       title=None,
                       image_paths=None,
                       snapshot_url=None,
                       scenarios=None,
                       priority=None,
                       config=None,
                       recipients=None,
                       data=None):
        _LOGGER.info("SUPERNOTIFY notify_email: %s %s", config, recipients)
        config = config or self.default_delivery or {}
        template = config.get(CONF_TEMPLATE)
        recipients = recipients or {}
        data = data or {}
        scenarios = scenarios or []
        html = data.get("html")
        template = data.get("template", config.get("template"))
        addresses = []
        for recipient in recipients:
            if recipient.get("email"):
                addresses.append(recipient.get("email"))
            elif ATTR_TARGET in recipient:
                target = recipient.get(ATTR_TARGET)
                if re.fullmatch(RE_VALID_EMAIL, target):
                    addresses.append(target)

        service_data = {
            "message":   message,
            ATTR_TARGET:   addresses
        }
        if len(addresses) == 0:
            addresses is None  # default to SMTP platform default recipients

        if title:
            service_data["title"] = title
        if data and data.get("data"):
            service_data[ATTR_DATA] = data.get("data")
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
                         "site": self.context.hass_name,
                         "priority": priority,
                         "scenarios": scenarios,
                         "img": None,
                         "details_url": "https://home.barrsofcloak.org",
                         "server": {
                             "url": self.context.hass_url,
                             "domain":  "home.barrsofcloak.org"

                         }
                         }
                if snapshot_url:
                    alert["img"] = {
                        "text": "Snapshot Image",
                        "url": snapshot_url
                    }
                env = Environment(loader=FileSystemLoader(template_path))
                template_obj = env.get_template(template)
                html = template_obj.render(alert=alert)
                if not html:
                    _LOGGER.error("Empty result from template %s" % template)
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
