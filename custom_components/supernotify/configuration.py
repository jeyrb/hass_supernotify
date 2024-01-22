import logging
import os.path
from homeassistant.const import (
    CONF_ENABLED,
)
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify
from homeassistant.helpers import device_registry, entity_registry

from . import (
    CONF_DEVICE_TRACKER,
    CONF_MANUFACTURER,
    CONF_MOBILE_DEVICES,
    CONF_MOBILE_DISCOVERY,
    CONF_MODEL,
    CONF_NOTIFY_SERVICE,
    CONF_PERSON,
    CONF_SELECTION,
    DELIVERY_SELECTION_IMPLICIT,
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
                 hass_url: str = None,
                 hass_name: str = None,
                 deliveries=None,
                 links=(),
                 recipients=(),
                 mobile_actions=None,
                 template_path=(),
                 overrides=None,
                 scenarios=None,
                 method_defaults=None):
        self.hass = hass
        self.hass_url = hass_url
        self.hass_name = hass_name
        self.links = ensure_list(links)
        self.deliveries = deliveries or {}
        self.recipients = ensure_list(recipients)
        self.mobile_actions = mobile_actions or {}
        self.template_path = template_path
        self.method_defaults = method_defaults or {}
        self.scenarios = {}
        self.overrides = overrides or {}
        self.people = {}
        self.configured_scenarios = scenarios or {}
        self.delivery_by_scenario = {}
        self.fallback_on_error = {}
        self.fallback_by_default = {}

    async def initialize(self):
        self.people = self.setup_people(self.recipients)

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

        default_deliveries = {}
        if self.deliveries:
            for d, dc in self.deliveries.items():
                if dc.get(CONF_ENABLED, True):
                    if SELECTION_FALLBACK_ON_ERROR in dc.get(CONF_SELECTION, [SELECTION_DEFAULT]):
                        self.fallback_on_error[d] = dc
                    if SELECTION_FALLBACK in dc.get(CONF_SELECTION, [SELECTION_DEFAULT]):
                        self.fallback_by_default[d] = dc
                    if SELECTION_DEFAULT in dc.get(CONF_SELECTION, [SELECTION_DEFAULT]):
                        default_deliveries[d] = dc

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
                if delivery_enabled(scenario_definition_delivery.get(scenario_delivery)):
                    self.delivery_by_scenario[scenario_name].append(
                        scenario_delivery)

        if SCENARIO_DEFAULT not in self.delivery_by_scenario:
            self.delivery_by_scenario[SCENARIO_DEFAULT] = list(
                default_deliveries.keys())

    def setup_people(self, recipients):
        dev_reg = ent_reg = None
        try:
            dev_reg = device_registry.async_get(self.hass)
            ent_reg = entity_registry.async_get(self.hass)
        except Exception as e:
            _LOGGER.warning("SUPERNOTIFY Unable to get device/entity registry, mobile app discovery disabled: %s", e)
       
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


def delivery_enabled(delivery):
    delivery = delivery or {}
    return delivery.get(CONF_ENABLED, True)


def ensure_list(v):
    if v is None:
        return []
    elif isinstance(v, list):
        return v
    elif isinstance(v, tuple):
        return list(v)
    else:
        return [v]


def ensure_dict(v, default=None):
    if v is None:
        return {}
    elif isinstance(v, dict):
        return v
    elif isinstance(v, list):
        return {vv: default for vv in v}
    else:
        return {v: default}