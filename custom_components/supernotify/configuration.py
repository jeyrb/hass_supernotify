import logging
import os.path
import inspect
from homeassistant.const import (
    CONF_ENABLED,
)
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify
from homeassistant.helpers import device_registry, entity_registry
from homeassistant.helpers.network import get_url
import socket
from homeassistant.const import (
    CONF_ENTITIES,
    CONF_METHOD,
    CONF_NAME,
    CONF_SERVICE,
    CONF_TARGET,
)
from custom_components.supernotify.common import safe_get, ensure_list

from . import (
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
    OCCUPANCY_ALL,
    OCCUPANCY_ALL_IN,
    OCCUPANCY_ALL_OUT,
    OCCUPANCY_ANY_IN,
    OCCUPANCY_ANY_OUT,
    OCCUPANCY_NONE,
    OCCUPANCY_ONLY_IN,
    OCCUPANCY_ONLY_OUT,
    SCENARIO_DEFAULT,
    SELECTION_DEFAULT,
    SELECTION_FALLBACK,
    SELECTION_FALLBACK_ON_ERROR,
)
from .scenario import Scenario

_LOGGER = logging.getLogger(__name__)


class SupernotificationConfiguration:
    def __init__(self,
                 hass: HomeAssistant = None,
                 deliveries=None,
                 links=(),
                 recipients=(),
                 mobile_actions=None,
                 template_path=None,
                 media_path=None,
                 overrides=None,
                 scenarios=None,
                 method_defaults=None,
                 cameras=None):
        if hass:
            self.hass = hass
            self.hass_name = hass.config.location_name
            try:
                self.hass_internal_url = get_url(hass, prefer_external=False)
            except Exception as e:
                _LOGGER.warning("SUPERNOTIFY could not get internal hass url: %s", e)
                self.hass_internal_url = "http://%s" % socket.gethostname()
            try:
                self.hass_external_url = get_url(hass, prefer_external=True)
            except Exception as e:
                _LOGGER.warning("SUPERNOTIFY could not get external hass url: %s", e)
                self.hass_external_url = self.hass_internal_url            
        else:
            self.hass = None
            self.hass_internal_url = ""
            self.hass_external_url = ""
            self.hass_name = "!UNDEFINED!"
            
        _LOGGER.debug("SUPERNOTIFY Configured for HomeAssistant instance %s at %s , %s", 
                      self.hass_name, self.hass_internal_url, self.hass_external_url)
            
        if not self.hass_internal_url or not self.hass_internal_url.startswith("http"):
            _LOGGER.warning("SUPERNOTIFY invalid internal hass url %s", self.hass_internal_url)

        self.links = ensure_list(links)
        # raw configured deliveries
        self._deliveries = deliveries if isinstance(deliveries, dict) else {}
        # validated deliveries
        self.deliveries = {}
        self._recipients = ensure_list(recipients)
        self.mobile_actions = mobile_actions or {}
        self.template_path = template_path
        self.media_path = media_path
        self.cameras = {c[CONF_CAMERA]: c for c in cameras} if cameras else {}
        self.methods = {}
        self.method_defaults = method_defaults or {}
        self.scenarios = {}
        self.overrides = overrides or {}
        self.people = {}
        self.configured_scenarios = scenarios or {}
        self.delivery_by_scenario = {}
        self.fallback_on_error = {}
        self.fallback_by_default = {}

    async def initialize(self):
        self.people = self.setup_people(self._recipients)

        if self.configured_scenarios:
            for scenario_name, scenario_definition in self.configured_scenarios .items():
                scenario = Scenario(
                    scenario_name, scenario_definition, self.hass)
                if await scenario.validate():
                    self.scenarios[scenario_name] = scenario

        if self.template_path and not os.path.exists(self.template_path):
            _LOGGER.warning("SUPERNOTIFY template path not found at %s",
                            self.template_path)
            self.template_path = None

        if self.media_path and not os.path.exists(self.media_path):
            _LOGGER.info("SUPERNOTIFY media path not found at %s",
                         self.media_path)
            try:
                os.makedirs(self.media_path)
            except Exception as e:
                _LOGGER.warning(
                    "SUPERNOTIFY media path %s cannot be created: %s", self.media_path, e)
                self.media_path = None
        if self.media_path is not None:
            _LOGGER.info("SUPERNOTIFY abs media path: %s",
                         os.path.abspath(self.media_path))

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

                self.set_method_default(dc, CONF_SERVICE)
                self.set_method_default(dc, CONF_TARGET)
                self.set_method_default(dc, CONF_ENTITIES)

        for scenario_name, scenario in self.scenarios.items():
            self.delivery_by_scenario.setdefault(scenario_name, [])
            if scenario.delivery_selection == DELIVERY_SELECTION_IMPLICIT:
                scenario_deliveries = list(default_deliveries.keys())
            else:
                scenario_deliveries = []
            scenario_definition_delivery = scenario.delivery
            scenario_deliveries.extend(
                s for s in scenario_definition_delivery.keys() if s not in scenario_deliveries)

            for scenario_delivery in scenario_deliveries:
                if safe_get(scenario_definition_delivery.get(scenario_delivery), CONF_ENABLED, True):
                    self.delivery_by_scenario[scenario_name].append(
                        scenario_delivery)

        if SCENARIO_DEFAULT not in self.delivery_by_scenario:
            self.delivery_by_scenario[SCENARIO_DEFAULT] = list(
                default_deliveries.keys())

    async def register_delivery_methods(self, delivery_methods):
        """available directly for test fixtures supplying class or instance"""
        for delivery_method in delivery_methods:
            if inspect.isclass(delivery_method):
                self.methods[delivery_method.method] = delivery_method(
                    self.hass, self, self._deliveries
                )
            else:
                self.methods[delivery_method.method] = delivery_method
            await self.methods[delivery_method.method].initialize()
            self.deliveries.update(
                self.methods[delivery_method.method].valid_deliveries)

        for d, dc in self.deliveries.items():
            if dc.get(CONF_METHOD) not in self.methods:
                _LOGGER.info(
                    "SUPERNOTIFY Ignoring delivery %s without known method %s", d, dc.get(CONF_METHOD))

        _LOGGER.info("SUPERNOTIFY configured deliveries %s",
                     "; ".join(self.deliveries.keys()))

    def set_method_default(self, delivery_config, attr):
        if not delivery_config.get(attr):
            method_default = self.method_defaults.get(
                delivery_config.get(CONF_METHOD), {})
            if method_default.get(attr):
                delivery_config[attr] = method_default[attr]
                _LOGGER.debug("SUPERNOTIFY Defaulting delivery % to %s %s",
                              delivery_config[CONF_NAME], attr, delivery_config[attr])

    def delivery_method(self, delivery):
        method_name = self.deliveries.get(delivery, {}).get(CONF_METHOD)
        if not method_name:
            raise ValueError(
                "SUPERNOTIFY No method for delivery %s" % delivery)
        return self.methods.get(method_name)

    def setup_people(self, recipients):
        dev_reg = ent_reg = None
        try:
            dev_reg = device_registry.async_get(self.hass)
            ent_reg = entity_registry.async_get(self.hass)
        except Exception as e:
            _LOGGER.warning(
                "SUPERNOTIFY Unable to get device/entity registry, mobile app discovery disabled: %s", e)

        people = {}
        for r in recipients:
            if r.get(CONF_MOBILE_DISCOVERY) and dev_reg and ent_reg:
                r[CONF_MOBILE_DEVICES].extend(
                    self.mobile_devices_for_person(r[CONF_PERSON], dev_reg, ent_reg))
                if r.get(CONF_MOBILE_DEVICES):
                    _LOGGER.info("SUPERNOTIFY Auto configured %s for mobile devices %s",
                                 r[CONF_PERSON], r[CONF_MOBILE_DEVICES])
                else:
                    _LOGGER.warning(
                        "SUPERNOTIFY Unable to find mobile devices for %s", r[CONF_PERSON])
            people[r[CONF_PERSON]] = r
        return people

    def mobile_devices_for_person(self, person_entity_id: str,
                                  dev_reg: device_registry.DeviceRegistry = None,
                                  ent_reg: entity_registry.EntityRegistry = None) -> list:

        mobile_devices = []
        person_state = self.hass.states.get(person_entity_id)
        if not person_state:
            _LOGGER.warning("SUPERNOTIFY Unable to resolve %s",
                            person_entity_id)
        else:
            for d_t in person_state.attributes.get('device_trackers', ()):
                entity = ent_reg.async_get(d_t)
                if entity and entity.platform == 'mobile_app':
                    device = dev_reg.async_get(entity.device_id)
                    if device:
                        mobile_devices.append({
                            CONF_MANUFACTURER: device.manufacturer,
                            CONF_MODEL: device.model,
                            CONF_NOTIFY_SERVICE: 'mobile_app_%s' % slugify(device.name),
                            CONF_DEVICE_TRACKER: d_t
                        })
        return mobile_devices

    def filter_people_by_occupancy(self, occupancy):
        if occupancy == OCCUPANCY_ALL:
            return self.people.values()
        elif occupancy == OCCUPANCY_NONE:
            return []

        at_home = []
        away = []
        for person, person_config in self.people.items():
            # all recipients checked for occupancy, regardless of override
            try:
                tracker = self.hass.states.get(person)
                if tracker is not None and tracker.state == "home":
                    at_home.append(person_config)
                else:
                    away.append(person_config)
            except Exception as e:
                _LOGGER.warning(
                    "Unable to determine occupied status for %s: %s", person, e)
        if occupancy == OCCUPANCY_ALL_IN:
            return self.people.values() if len(away) == 0 else []
        elif occupancy == OCCUPANCY_ALL_OUT:
            return self.people.values() if len(at_home) == 0 else []
        elif occupancy == OCCUPANCY_ANY_IN:
            return self.people.values() if len(at_home) > 0 else []
        elif occupancy == OCCUPANCY_ANY_OUT:
            return self.people.values() if len(away) > 0 else []
        elif occupancy == OCCUPANCY_ONLY_IN:
            return at_home
        elif occupancy == OCCUPANCY_ONLY_OUT:
            return away
        else:
            _LOGGER.warning(
                "SUPERNOTIFY Unknown occupancy tested: %s" % occupancy)
            return []
