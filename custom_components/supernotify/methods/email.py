import logging
import os.path
import re

from jinja2 import Environment, FileSystemLoader

from homeassistant.components.notify.const import ATTR_DATA, ATTR_TARGET, ATTR_MESSAGE, ATTR_TITLE
from homeassistant.const import CONF_EMAIL, CONF_SERVICE

from custom_components.supernotify import CONF_TEMPLATE, METHOD_EMAIL
from custom_components.supernotify.delivery_method import DeliveryMethod

RE_VALID_EMAIL = r"([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+"

_LOGGER = logging.getLogger(__name__)


class EmailDeliveryMethod(DeliveryMethod):
    method = METHOD_EMAIL

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.template_path = None
        if self.context.template_path:
            self.template_path = os.path.join(
                self.context.template_path, "email")
            if not os.path.exists(self.template_path):
                self.template_path = None
        if self.template_path is None:
            _LOGGER.warning("SUPERNOTIFY Email templates not available")
        else:
            _LOGGER.debug(
                "SUPERNOTIFY Loading email templates from %s", self.template_path)

    def select_target(self, target):
        return re.fullmatch(RE_VALID_EMAIL, target)

    def recipient_target(self, recipient):
        email = recipient.get(CONF_EMAIL)
        return [email] if email else []

    async def _delivery_impl(self, 
                             notification,
                             delivery,
                             targets=None,
                             data=None,
                             **kwargs) -> bool:
        _LOGGER.info("SUPERNOTIFY notify_email: %s %s", delivery, targets)
        config = notification.delivery_config.get(delivery) or self.default_delivery or {}
        template = config.get(CONF_TEMPLATE)
        data = data or {}
        scenarios = notification.delivery_scenarios(delivery) or []
        html = data.get("html")
        template = data.get("template", config.get("template"))
        addresses = targets or []
        image_paths = data.get("image_paths")
        snapshot_url = data.get("snapshot_url")

        service_data = notification.core_service_data(delivery)
        
        if len(addresses) > 0:
            service_data[ATTR_TARGET]=addresses
            # default to SMTP platform default recipients if no explicit addresses

        if data and data.get("data"):
            service_data[ATTR_DATA] = data.get("data")

        if not template or not self.template_path:
            if image_paths:
                service_data.setdefault("data", {})
                service_data["data"]["images"] = image_paths
        else:
            html = self.render_template(
                template, service_data[ATTR_TITLE], 
                service_data[ATTR_MESSAGE], 
                scenarios, 
                notification.priority, snapshot_url)
            if html:
                service_data.setdefault("data", {})
                service_data["data"]["html"] = html
        return await self.call_service(config.get(CONF_SERVICE),service_data)
     
    def render_template(self, template, title, message, scenarios, priority, snapshot_url):
        alert = {}
        try:
            alert = {"title": title,
                     "message": message,
                     "subheading": "Home Assistant Notification",
                     "site": self.context.hass_name,
                     "priority": priority,
                     "scenarios": scenarios,
                     "img": None,
                     "server": {
                         "url": self.context.hass_url,
                         "name":  "Home Assistant"

                     }
                     }
            if snapshot_url:
                alert["img"] = {
                    "text": "Snapshot Image",
                    "url": snapshot_url
                }
            env = Environment(loader=FileSystemLoader(self.template_path))
            template_obj = env.get_template(template)
            html = template_obj.render(alert=alert)
            if not html:
                _LOGGER.error("Empty result from template %s" % template)
            else:
                return html
        except Exception as e:
            _LOGGER.error("SUPERNOTIFY Failed to generate html mail: %s", e)
            _LOGGER.debug("SUPERNOTIFY Template failure: %s",
                          alert, exc_info=True)
