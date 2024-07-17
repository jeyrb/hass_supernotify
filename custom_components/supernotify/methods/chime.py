import logging
import re
from typing import Any

from homeassistant.components.group import expand_entity_ids
from homeassistant.components.notify.const import ATTR_MESSAGE, ATTR_TITLE
from homeassistant.const import ATTR_ENTITY_ID, CONF_VARIABLES  # ATTR_VARIABLES from script.const has import issues

from custom_components.supernotify import ATTR_DATA, CONF_DATA, CONF_OPTIONS, CONF_TARGET, METHOD_CHIME
from custom_components.supernotify.common import ensure_list
from custom_components.supernotify.delivery_method import DeliveryMethod
from custom_components.supernotify.envelope import Envelope

RE_VALID_CHIME = r"(switch|script|group|siren|media_player)\.[A-Za-z0-9_]+"

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA_RESTRICT: dict[str, list[str]] = {
    "media_player": ["data", "entity_id", "media_content_id", "media_content_type", "enqueue", "announce"],
    "switch": ["entity_id"],
    "script": ["data", "variables", "context", "wait"],
    "siren": ["data", "entity_id"],
}  # TODO: source directly from component schema


class ChimeDeliveryMethod(DeliveryMethod):
    method = METHOD_CHIME

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.chime_aliases = self.context.method_defaults.get(self.method, {}).get(CONF_OPTIONS, {}).get("chime_aliases", {})
        self.chime_entities = self.context.method_defaults.get(self.method, {}).get(CONF_TARGET, [])

    def validate_service(self, service: str | None) -> bool:
        return service is None

    def select_target(self, target: str) -> bool:
        return re.fullmatch(RE_VALID_CHIME, target) is not None

    async def deliver(self, envelope: Envelope) -> bool:
        config = self.delivery_config(envelope.delivery_name)
        data: dict[str, Any] = {}
        data.update(config.get(CONF_DATA) or {})
        data.update(envelope.data or {})
        targets = envelope.targets or []

        # chime_repeat = data.pop("chime_repeat", 1)
        chime_tune: str | None = data.pop("chime_tune", None)

        _LOGGER.info(
            "SUPERNOTIFY notify_chime: %s -> %s (delivery: %s, env_data:%s, dlv_data:%s)",
            chime_tune,
            targets,
            envelope.delivery_name,
            envelope.data,
            config.get(CONF_DATA),
        )

        expanded_targets = dict.fromkeys(expand_entity_ids(self.hass, targets), chime_tune)
        entities_and_tunes = self.resolve_tune(chime_tune)
        expanded_targets.update(entities_and_tunes)  # overwrite and extend
        chimes = 0
        for chime_entity_id, tune in expanded_targets.items():
            _LOGGER.debug("SUPERNOTIFY chime %s: %s", chime_entity_id, tune)
            service_data = None
            try:
                domain, service, service_data = self.analyze_target(chime_entity_id, tune, data)
                if domain is not None and service is not None:
                    service_data = self.prune_data(domain, service_data)

                    if domain == "script":
                        self.set_service_data(service_data[CONF_VARIABLES], ATTR_MESSAGE, envelope.message)
                        self.set_service_data(service_data[CONF_VARIABLES], ATTR_TITLE, envelope.title)
                        self.set_service_data(service_data[CONF_VARIABLES], "chime_tune", tune)

                    if await self.call_service(envelope, f"{domain}.{service}", service_data=service_data):
                        chimes += 1
                else:
                    _LOGGER.debug("SUPERNOTIFY Chime skipping incomplete service for %s,%s", chime_entity_id, tune)
            except Exception as e:
                _LOGGER.error("SUPERNOTIFY Failed to chime %s: %s [%s]", chime_entity_id, service_data, e)
        return chimes > 0

    def prune_data(self, domain: str, data: dict) -> dict:
        pruned: dict[str, Any] = {}
        if data and domain in DATA_SCHEMA_RESTRICT:
            restrict: list[str] = DATA_SCHEMA_RESTRICT.get(domain) or []
            for key in list(data.keys()):
                if key in restrict:
                    pruned[key] = data[key]
        return pruned

    def analyze_target(self, target: str, chime_tune: str | None, data: dict) -> tuple[str, str | None, dict[str, Any]]:
        if not target:
            _LOGGER.warning("SUPERNOTIFY Empty chime target")
            return "", None, {}
        domain, name = target.split(".", 1)
        service_data: dict[str, Any] = {}
        service: str | None = None
        chime_volume = data.pop("chime_volume", 1)
        chime_duration = data.pop("chime_duration", 10)

        if domain == "switch":
            service = "turn_on"
            service_data[ATTR_ENTITY_ID] = target
        elif domain == "siren":
            service = "turn_on"
            service_data[ATTR_ENTITY_ID] = target
            service_data[ATTR_DATA] = {}
            if chime_tune:
                service_data[ATTR_DATA]["tone"] = chime_tune
            service_data[ATTR_DATA]["duration"] = chime_duration
            service_data[ATTR_DATA]["volume_level"] = chime_volume

        elif domain == "script":
            if data:
                service_data.update(data)
            service = name
            service_data.setdefault(CONF_VARIABLES, {})

        elif domain == "media_player" and chime_tune:
            if data:
                service_data.update(data)
            service = "play_media"
            service_data[ATTR_ENTITY_ID] = target
            service_data["media_content_type"] = "sound"
            service_data["media_content_id"] = chime_tune

        else:
            _LOGGER.warning("SUPERNOTIFY No matching chime domain/tune: %s, target: %s, tune: %s", domain, target, chime_tune)

        return domain, service, service_data

    def resolve_tune(self, tune: str | None) -> dict[str, Any]:
        entities_and_tunes: dict[str, Any] = {}
        if tune is not None:
            for domain, alias_config in self.chime_aliases.get(tune, {}).items():
                if isinstance(alias_config, str):
                    alias_config = {"tune": alias_config}
                domain = alias_config.get("domain", domain)
                actual_tune = alias_config.get("tune", tune)
                if ATTR_ENTITY_ID in alias_config:
                    entities_and_tunes.update(dict.fromkeys(ensure_list(alias_config[ATTR_ENTITY_ID]), actual_tune))
                else:
                    entities_and_tunes.update({ent: actual_tune for ent in self.chime_entities if ent.startswith(f"{domain}.")})

        return entities_and_tunes
