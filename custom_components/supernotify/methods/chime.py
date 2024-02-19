import logging
import re

from homeassistant.components.notify.const import (
    ATTR_MESSAGE,
    ATTR_TITLE
)
from homeassistant.components.script.const import ATTR_VARIABLES
from homeassistant.components.group import expand_entity_ids
from custom_components.supernotify import ATTR_DATA, CONF_OPTIONS, METHOD_CHIME, CONF_TARGET
from custom_components.supernotify.common import ensure_list
from custom_components.supernotify.delivery_method import DeliveryMethod
from homeassistant.const import ATTR_ENTITY_ID

RE_VALID_CHIME = r"(switch|script|group|media_player)\.[A-Za-z0-9_]+"

_LOGGER = logging.getLogger(__name__)


class ChimeDeliveryMethod(DeliveryMethod):
    method = METHOD_CHIME

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chime_aliases = self.context.method_defaults.get(
            self.method, {}).get(CONF_OPTIONS, {}).get('chime_aliases', {})
        self.chime_entities = self.context.method_defaults.get(
            self.method, {}).get(CONF_TARGET, [])

    def validate_service(self, service):
        return service is None

    def select_target(self, target):
        return re.fullmatch(RE_VALID_CHIME, target)

    async def _delivery_impl(self, envelope) -> None:
        data = envelope.data or {}
        targets = envelope.targets or []

        chime_repeat = data.pop("chime_repeat", 1)
        chime_tune = data.pop("chime_tune", None)

        _LOGGER.info("SUPERNOTIFY notify_chime: %s", targets)
        calls = 0
        expanded_targets = [(ent, chime_tune)
                            for ent in expand_entity_ids(self.hass, targets)]
        entities_and_tunes = self.resolve_tune(chime_tune)
        expanded_targets.extend(entities_and_tunes)

        for chime_entity_id, tune in expanded_targets:
            _LOGGER.debug("SUPERNOTIFY chime %s: %s", chime_entity_id, tune)
            service_data = None
            try:
                domain, service, service_data = self.analyze_target(
                    chime_entity_id, tune, data)

                if service == "script":
                    self.set_service_data(
                        service_data[ATTR_VARIABLES], ATTR_MESSAGE,
                        envelope.message)
                    self.set_service_data(
                        service_data[ATTR_VARIABLES], ATTR_TITLE,
                        envelope.title)
                    self.set_service_data(
                        service_data[ATTR_VARIABLES], "chime_tune",
                        tune)

                if domain is not None and service is not None:
                    await self.hass.services.async_call(
                        domain, service, service_data=service_data)
                    calls += 1
            except Exception as e:
                _LOGGER.error("SUPERNOTIFY Failed to chime %s: %s [%s]",
                              chime_entity_id, service_data, e)
                envelope.errored += 1
        if calls > 0:
            envelope.delivered = 1

    def analyze_target(self, target: str, chime_tune: str, data: dict):
        domain, name = target.split(".", 1)
        service_data = {}
        service = None
        chime_volume = data.pop("chime_volume", 1)
        chime_duration = data.pop("chime_duration", 10)

        if domain == "switch":
            service = "turn_on"
            service_data[ATTR_ENTITY_ID] = target
        elif domain == "siren":
            service == "turn_on"
            service_data[ATTR_ENTITY_ID] = target
            service_data[ATTR_DATA] = {}
            if chime_tune:
                service_data["tone"] = chime_tune
            service_data["duration"] = chime_duration
            service_data["volume_level"] = chime_volume

        elif domain == "script":
            service = name
            service_data.setdefault(ATTR_VARIABLES, {})
            if data:
                service_data.update(data)
        elif domain == "media_player" and chime_tune:
            service = "play_media"
            service_data[ATTR_ENTITY_ID] = target
            service_data["media_content_type"] = "sound"
            service_data["media_content_id"] = chime_tune
            if data:
                service_data.update(data)
        else:
            _LOGGER.debug("SUPERNOTIFY No matching chime domain: %s, target: %s, tune: %s", domain, target, chime_tune)

        return domain, service, service_data

    def resolve_tune(self, tune: str):
        entities_and_tunes = []
        for domain, alias_config in self.chime_aliases.get(tune, {}).items():
            if isinstance(alias_config, str):
                alias_config = {"tune": alias_config}
            domain = alias_config.get("domain", domain)
            actual_tune = alias_config.get("tune", tune)
            if ATTR_ENTITY_ID in alias_config:
                entities_and_tunes.extend(
                    (ent, actual_tune) for ent in ensure_list(alias_config[ATTR_ENTITY_ID]))
            else:
                entities_and_tunes.extend(
                    [(ent, actual_tune) for ent in self.chime_entities if ent.startswith("%s." % domain)])

        return entities_and_tunes
