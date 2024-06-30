from __future__ import annotations

import logging
import socket
from pathlib import Path
from typing import TYPE_CHECKING, Any

from homeassistant.const import (
    ATTR_STATE,
    CONF_ENABLED,
    CONF_METHOD,
    CONF_NAME,
    STATE_HOME,
    STATE_NOT_HOME,
)
from homeassistant.helpers import device_registry, entity_registry
from homeassistant.helpers.network import get_url
from homeassistant.util import slugify

from custom_components.supernotify.archive import NotificationArchive
from custom_components.supernotify.common import ensure_list, safe_get

from . import (
    ATTR_USER_ID,
    CONF_ARCHIVE_DAYS,
    CONF_ARCHIVE_PATH,
    CONF_CAMERA,
    CONF_DEVICE_TRACKER,
    CONF_MANUFACTURER,
    CONF_MOBILE_DEVICES,
    CONF_MOBILE_DISCOVERY,
    CONF_MODEL,
    CONF_NOTIFY_SERVICE,
    CONF_PERSON,
    CONF_SELECTION,
    DELIVERY_SELECTION_IMPLICIT,
    METHOD_DEFAULTS_SCHEMA,
    SCENARIO_DEFAULT,
    SELECTION_DEFAULT,
    SELECTION_FALLBACK,
    SELECTION_FALLBACK_ON_ERROR,
    CommandType,
    RecipientType,
    Snooze,
    TargetType,
)
from .scenario import Scenario

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, State

    from custom_components.supernotify.delivery_method import DeliveryMethod

_LOGGER = logging.getLogger(__name__)


class SupernotificationConfiguration:
    def __init__(
        self,
        hass: HomeAssistant | None = None,
        deliveries: dict | None = None,
        links: list | None = None,
        recipients: list | None = None,
        mobile_actions: dict | None = None,
        template_path: str | None = None,
        media_path: str | None = None,
        archive_config: dict[str, str] | None = None,
        scenarios: dict[str, dict] | None = None,
        method_defaults: dict | None = None,
        cameras: list[dict] | None = None,
    ) -> None:
        self.hass: HomeAssistant | None = None
        self.hass_internal_url: str
        self.hass_external_url: str
        if hass:
            self.hass = hass
            self.hass_name = hass.config.location_name
            try:
                self.hass_internal_url = get_url(hass, prefer_external=False)
            except Exception as e:
                _LOGGER.warning("SUPERNOTIFY could not get internal hass url: %s", e)
                self.hass_internal_url = f"http://{socket.gethostname()}"
            try:
                self.hass_external_url = get_url(hass, prefer_external=True)
            except Exception as e:
                _LOGGER.warning("SUPERNOTIFY could not get external hass url: %s", e)
                self.hass_external_url = self.hass_internal_url
        else:
            self.hass_internal_url = ""
            self.hass_external_url = ""
            self.hass_name = "!UNDEFINED!"
            _LOGGER.warning("SUPERNOTIFY Configured without HomeAssistant instance")

        _LOGGER.debug(
            "SUPERNOTIFY Configured for HomeAssistant instance %s at %s , %s",
            self.hass_name,
            self.hass_internal_url,
            self.hass_external_url,
        )

        if not self.hass_internal_url or not self.hass_internal_url.startswith("http"):
            _LOGGER.warning("SUPERNOTIFY invalid internal hass url %s", self.hass_internal_url)

        self.links = ensure_list(links)
        # raw configured deliveries
        self._deliveries: dict = deliveries if isinstance(deliveries, dict) else {}
        # validated deliveries
        self.deliveries: dict = {}
        self._recipients: list = ensure_list(recipients)
        self.mobile_actions: dict = mobile_actions or {}
        self.template_path: Path | None = Path(template_path) if template_path else None
        self.media_path: Path | None = Path(media_path) if media_path else None
        archive_config = archive_config or {}
        self.archive: NotificationArchive = NotificationArchive(
            archive_config.get(CONF_ARCHIVE_PATH), archive_config.get(CONF_ARCHIVE_DAYS)
        )
        self.cameras: dict[str, Any] = {c[CONF_CAMERA]: c for c in cameras} if cameras else {}
        self.methods: dict[str, DeliveryMethod] = {}
        self.method_defaults: dict = method_defaults or {}
        self.scenarios: dict[str, Scenario] = {}
        self.people: dict[str, Any] = {}
        self.applied_scenarios: dict = scenarios or {}
        self.delivery_by_scenario: dict[str, list] = {SCENARIO_DEFAULT: []}
        self.fallback_on_error: dict = {}
        self.fallback_by_default: dict = {}
        self.snoozes: dict[str, Snooze] = {}
        self._entity_registry: entity_registry.EntityRegistry | None = None
        self._device_registry: device_registry.DeviceRegistry | None = None

    async def initialize(self) -> None:
        self.people = self.setup_people(self._recipients)

        if self.applied_scenarios and self.hass:
            for scenario_name, scenario_definition in self.applied_scenarios.items():
                scenario = Scenario(scenario_name, scenario_definition, self.hass)
                if await scenario.validate():
                    self.scenarios[scenario_name] = scenario

        if self.template_path and not self.template_path.exists():
            _LOGGER.warning("SUPERNOTIFY template path not found at %s", self.template_path)
            self.template_path = None

        if self.media_path and not self.media_path.exists():
            _LOGGER.info("SUPERNOTIFY media path not found at %s", self.media_path)
            try:
                self.media_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                _LOGGER.warning("SUPERNOTIFY media path %s cannot be created: %s", self.media_path, e)
                self.media_path = None
        if self.media_path is not None:
            _LOGGER.info("SUPERNOTIFY abs media path: %s", self.media_path.absolute())
        if self.archive:
            self.archive.initialize()
        default_deliveries: dict = self.initialize_deliveries()
        self.initialize_scenarios(default_deliveries)

    def initialize_deliveries(self) -> dict:
        default_deliveries = {}
        if self._deliveries:
            for d, dc in self._deliveries.items():
                if dc.get(CONF_ENABLED, True):
                    if SELECTION_FALLBACK_ON_ERROR in dc.get(CONF_SELECTION, [SELECTION_DEFAULT]):
                        self.fallback_on_error[d] = dc
                    if SELECTION_FALLBACK in dc.get(CONF_SELECTION, [SELECTION_DEFAULT]):
                        self.fallback_by_default[d] = dc
                    if SELECTION_DEFAULT in dc.get(CONF_SELECTION, [SELECTION_DEFAULT]):
                        default_deliveries[d] = dc

                if not dc.get(CONF_NAME):
                    dc[CONF_NAME] = d  # for minimal tests
                for conf_key in METHOD_DEFAULTS_SCHEMA.schema:
                    self.set_method_default(dc, conf_key.schema)
        return default_deliveries

    def initialize_scenarios(self, default_deliveries: dict) -> None:
        for scenario_name, scenario in self.scenarios.items():
            self.delivery_by_scenario.setdefault(scenario_name, [])
            if scenario.delivery_selection == DELIVERY_SELECTION_IMPLICIT:
                scenario_deliveries: list[str] = list(default_deliveries.keys())
            else:
                scenario_deliveries = []
            scenario_definition_delivery = scenario.delivery
            scenario_deliveries.extend(s for s in scenario_definition_delivery if s not in scenario_deliveries)

            for scenario_delivery in scenario_deliveries:
                if safe_get(scenario_definition_delivery.get(scenario_delivery), CONF_ENABLED, True):
                    self.delivery_by_scenario[scenario_name].append(scenario_delivery)

        self.delivery_by_scenario[SCENARIO_DEFAULT] = list(default_deliveries.keys())

    async def register_delivery_methods(
        self,
        delivery_methods: list[DeliveryMethod] | None = None,
        delivery_method_classes: list[type[DeliveryMethod]] | None = None,
        set_as_default: bool = False,
    ) -> None:
        """Available directly for test fixtures supplying class or instance"""
        if delivery_methods:
            for delivery_method in delivery_methods:
                self.methods[delivery_method.method] = delivery_method
                await self.methods[delivery_method.method].initialize()
                self.deliveries.update(self.methods[delivery_method.method].valid_deliveries)
        if delivery_method_classes and self.hass:
            for delivery_method_class in delivery_method_classes:
                self.methods[delivery_method_class.method] = delivery_method_class(self.hass, self, self._deliveries)
                await self.methods[delivery_method_class.method].initialize()
                self.deliveries.update(self.methods[delivery_method_class.method].valid_deliveries)

        for d, dc in self.deliveries.items():
            if dc.get(CONF_METHOD) not in self.methods:
                _LOGGER.info("SUPERNOTIFY Ignoring delivery %s without known method %s", d, dc.get(CONF_METHOD))
            elif set_as_default and d not in self.delivery_by_scenario[SCENARIO_DEFAULT]:
                self.delivery_by_scenario[SCENARIO_DEFAULT].append(d)

        _LOGGER.info("SUPERNOTIFY configured deliveries %s", "; ".join(self.deliveries.keys()))

    def set_method_default(self, delivery_config: dict[str, Any], attr: str) -> None:
        if not delivery_config.get(attr):
            method_default = self.method_defaults.get(delivery_config.get(CONF_METHOD), {})
            if method_default.get(attr):
                delivery_config[attr] = method_default[attr]
                _LOGGER.debug(
                    "SUPERNOTIFY Defaulting delivery %s to %s %s", delivery_config[CONF_NAME], attr, delivery_config[attr]
                )

    def delivery_method(self, delivery: str) -> DeliveryMethod:
        method_name = self.deliveries.get(delivery, {}).get(CONF_METHOD)
        method: DeliveryMethod | None = self.methods.get(method_name)
        if not method:
            raise ValueError(f"SUPERNOTIFY No method for delivery {delivery}")
        return method

    def setup_people(self, recipients: list | tuple) -> dict[str, dict]:
        people: dict[str, dict] = {}
        for r in recipients:
            if r.get(CONF_MOBILE_DISCOVERY):
                r[CONF_MOBILE_DEVICES].extend(self.mobile_devices_for_person(r[CONF_PERSON]))
                if r.get(CONF_MOBILE_DEVICES):
                    _LOGGER.info("SUPERNOTIFY Auto configured %s for mobile devices %s", r[CONF_PERSON], r[CONF_MOBILE_DEVICES])
                else:
                    _LOGGER.warning("SUPERNOTIFY Unable to find mobile devices for %s", r[CONF_PERSON])
            if self.hass:
                state: State | None = self.hass.states.get(r[CONF_PERSON])
                if state is not None:
                    r[ATTR_USER_ID] = state.attributes.get(ATTR_USER_ID)
            people[r[CONF_PERSON]] = r
        return people

    def people_state(self) -> list[dict]:
        results = []
        if self.hass:
            for person, person_config in self.people.items():
                # TODO: possibly rate limit this
                try:
                    tracker = self.hass.states.get(person)
                    if tracker is None:
                        person_config[ATTR_STATE] = None
                    else:
                        person_config[ATTR_STATE] = tracker.state
                except Exception as e:
                    _LOGGER.warning("Unable to determine occupied status for %s: %s", person, e)
                results.append(person_config)
        return results

    def determine_occupancy(self) -> dict[str, list[dict]]:
        results: dict[str, list[dict]] = {STATE_HOME: [], STATE_NOT_HOME: []}
        for person_config in self.people_state():
            if person_config.get(ATTR_STATE) in (None, STATE_HOME):
                # default to at home if unknown tracker
                results[STATE_HOME].append(person_config)
            else:
                results[STATE_NOT_HOME].append(person_config)
        return results

    def entity_registry(self) -> entity_registry.EntityRegistry | None:
        """Hass entity registry is weird, every component ends up creating its own, with a store, subscribing
        to all entities, so do it once here
        """  # noqa: D205
        if self._entity_registry is not None:
            return self._entity_registry
        if self.hass:
            try:
                self._entity_registry = entity_registry.async_get(self.hass)
            except Exception as e:
                _LOGGER.warning("SUPERNOTIFY Unable to get entity registry: %s", e)
        return self._entity_registry

    def device_registry(self) -> device_registry.DeviceRegistry | None:
        """Hass device registry is weird, every component ends up creating its own, with a store, subscribing
        to all devices, so do it once here
        """  # noqa: D205
        if self._device_registry is not None:
            return self._device_registry
        if self.hass:
            try:
                self._device_registry = device_registry.async_get(self.hass)
            except Exception as e:
                _LOGGER.warning("SUPERNOTIFY Unable to get device registry: %s", e)
        return self._device_registry

    def mobile_devices_for_person(self, person_entity_id: str) -> list:
        mobile_devices = []
        person_state = self.hass.states.get(person_entity_id) if self.hass else None
        if not person_state:
            _LOGGER.warning("SUPERNOTIFY Unable to resolve %s", person_entity_id)
        else:
            entity_registry = self.entity_registry()
            device_registry = self.device_registry()
            if entity_registry and device_registry:
                for d_t in person_state.attributes.get("device_trackers", ()):
                    entity = entity_registry.async_get(d_t)
                    if entity and entity.platform == "mobile_app" and entity.device_id:
                        device = device_registry.async_get(entity.device_id)
                        if device:
                            mobile_devices.append({
                                CONF_MANUFACTURER: device.manufacturer,
                                CONF_MODEL: device.model,
                                CONF_NOTIFY_SERVICE: f"mobile_app_{slugify(device.name)}",
                                CONF_DEVICE_TRACKER: d_t,
                            })
        return mobile_devices

    def register_snooze(
        self,
        cmd: CommandType,
        target_type: TargetType,
        target: str | None,
        recipient_type: RecipientType,
        recipient: str | None,
        snooze_for: int | None,
    ) -> None:
        if cmd == CommandType.SNOOZE:
            snooze = Snooze(target_type, recipient_type, target, recipient, snooze_for)
            self.snoozes[snooze.short_key()] = snooze
        elif cmd == CommandType.SILENCE:
            snooze = Snooze(target_type, recipient_type, target, recipient)
            self.snoozes[snooze.short_key()] = snooze
        elif cmd == CommandType.NORMAL:
            anti_snooze = Snooze(target_type, recipient_type, target, recipient)
            to_del = [k for k, v in self.snoozes.items() if v.short_key() == anti_snooze.short_key()]
            for k in to_del:
                del self.snoozes[k]
        else:
            _LOGGER.warning(
                "SUPERNOTIFY Invalid mobile cmd %s (target_type: %s, target: %s, recipient_type: %s)",
                cmd,
                target_type,
                target,
                recipient_type,
            )

    def purge_snoozes(self) -> None:
        to_del = [k for k, v in self.snoozes.items() if not v.active()]
        for k in to_del:
            del self.snoozes[k]
