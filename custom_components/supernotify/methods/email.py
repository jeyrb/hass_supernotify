import logging
import os.path
import re
from typing import Any

from homeassistant.components.notify.const import ATTR_DATA, ATTR_MESSAGE, ATTR_TARGET, ATTR_TITLE
from homeassistant.const import CONF_EMAIL
from homeassistant.core import HomeAssistant
from jinja2 import Environment, FileSystemLoader

from custom_components.supernotify import CONF_TEMPLATE, METHOD_EMAIL
from custom_components.supernotify.configuration import SupernotificationConfiguration
from custom_components.supernotify.delivery_method import DeliveryMethod
from custom_components.supernotify.envelope import Envelope

RE_VALID_EMAIL = (
    r"^[a-zA-Z0-9.+/=?^_-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)

_LOGGER = logging.getLogger(__name__)


class EmailDeliveryMethod(DeliveryMethod):
    method = METHOD_EMAIL

    def __init__(self, hass: HomeAssistant, context: SupernotificationConfiguration, deliveries: dict | None = None):
        super().__init__(hass, context, deliveries)
        self.template_path = None
        if self.context.template_path:
            self.template_path = os.path.join(self.context.template_path, "email")
            if not os.path.exists(self.template_path):
                _LOGGER.warning("SUPERNOTIFY Email templates not available at %s", self.template_path)
                self.template_path = None
        if self.template_path is None:
            _LOGGER.warning("SUPERNOTIFY Email templates not available")
        else:
            _LOGGER.debug("SUPERNOTIFY Loading email templates from %s", self.template_path)

    def select_target(self, target) -> bool:
        return re.fullmatch(RE_VALID_EMAIL, target) is not None

    def recipient_target(self, recipient) -> list[str]:
        email = recipient.get(CONF_EMAIL)
        return [email] if email else []

    async def deliver(self, envelope: Envelope) -> bool:
        _LOGGER.info("SUPERNOTIFY notify_email: %s %s", envelope.delivery_name, envelope.targets)

        data = envelope.data or {}
        config = self.delivery_config(envelope.delivery_name)
        html = data.get("html")
        template = data.get(CONF_TEMPLATE, config.get(CONF_TEMPLATE))
        addresses = envelope.targets or []
        snapshot_url = data.get("snapshot_url")
        # TODO centralize in config
        footer_template = data.get("footer")
        footer = footer_template.format(e=envelope) if footer_template else None

        service_data = envelope.core_service_data()

        if len(addresses) > 0:
            service_data[ATTR_TARGET] = addresses
            # default to SMTP platform default recipients if no explicit addresses

        if data and data.get("data"):
            service_data[ATTR_DATA] = data.get("data")

        if not template or not self.template_path:
            if footer and service_data.get(ATTR_MESSAGE):
                service_data[ATTR_MESSAGE] = f"{service_data[ATTR_MESSAGE]}\n\n{footer}"

            image_path: str | None = await envelope.grab_image()
            if image_path:
                service_data.setdefault("data", {})
                service_data["data"]["images"] = [image_path]
            if envelope.message_html:
                service_data.setdefault("data", {})
                html = envelope.message_html
                if image_path:
                    image_name = os.path.basename(image_path)
                    if html and "cid:%s" not in html and not html.endswith("</html"):
                        if snapshot_url:
                            html += '<div><p><a href="%s">' % snapshot_url
                            html += '<img src="cid:%s"/></a>' % image_name
                            html += "</p></div>"
                        else:
                            html += '<div><p><img src="cid:%s"></p></div>' % image_name

                service_data["data"]["html"] = html
        else:
            html = self.render_template(template, envelope, service_data, snapshot_url, envelope.message_html)
            if html:
                service_data.setdefault("data", {})
                service_data["data"]["html"] = html
        return await self.call_service(envelope, service_data=service_data)

    def render_template(
        self, template: str, envelope: Envelope, service_data: dict[str, Any], snapshot_url, preformatted_html
    ) -> str | None:
        alert = {}
        try:
            alert = {
                "message": service_data.get(ATTR_MESSAGE),
                "title": service_data.get(ATTR_TITLE),
                "envelope": envelope,
                "subheading": "Home Assistant Notification",
                "configuration": self.context,
                "preformatted_html": preformatted_html,
                "img": None,
            }
            if snapshot_url:
                alert["img"] = {"text": "Snapshot Image", "url": snapshot_url}
            env = Environment(loader=FileSystemLoader(self.template_path or ""), autoescape=True)
            template_obj = env.get_template(template)
            html = template_obj.render(alert=alert)
            if not html:
                _LOGGER.error("Empty result from template %s", template)
            else:
                return html
        except Exception as e:
            _LOGGER.error("SUPERNOTIFY Failed to generate html mail: %s", e)
            _LOGGER.debug("SUPERNOTIFY Template failure: %s", alert, exc_info=True)
        return None
