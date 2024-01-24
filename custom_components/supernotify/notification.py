import logging
import voluptuous as vol
from homeassistant.components.notify import (
    ATTR_DATA,
)
from custom_components.supernotify.common import safe_extend
from homeassistant.components.notify import (
    ATTR_TARGET,
)
from .media_grab import move_camera_to_ptz_preset, select_avail_camera, snap_camera, snapshot_from_url
from homeassistant.const import (
    CONF_ENABLED,
    CONF_ENTITIES,
    CONF_NAME,
    CONF_TARGET,
)
import uuid

from . import (
    ATTR_DELIVERY,
    ATTR_DELIVERY_SELECTION,
    ATTR_MEDIA,
    ATTR_MEDIA_CAMERA_DELAY,
    ATTR_MEDIA_CAMERA_ENTITY_ID,
    ATTR_MEDIA_CAMERA_PTZ_PRESET,
    ATTR_MEDIA_SNAPSHOT_URL,
    ATTR_PRIORITY,
    ATTR_RECIPIENTS,
    ATTR_SCENARIOS,
    CONF_DATA,
    CONF_DELIVERY,
    CONF_MESSAGE,
    CONF_MQTT_TOPIC,
    CONF_OCCUPANCY,
    CONF_PERSON,
    CONF_PTZ_DELAY,
    CONF_PTZ_PRESET_DEFAULT,
    CONF_RECIPIENTS,
    CONF_SELECTION,
    CONF_TITLE,
    DELIVERY_SELECTION_EXPLICIT,
    DELIVERY_SELECTION_FIXED,
    DELIVERY_SELECTION_IMPLICIT,
    OCCUPANCY_ALL,
    PRIORITY_MEDIUM,
    SCENARIO_DEFAULT,
    SELECTION_BY_SCENARIO,
    SERVICE_DATA_SCHEMA,
)
from .configuration import SupernotificationConfiguration
from .common import ensure_list, ensure_dict

_LOGGER = logging.getLogger(__name__)


class Notification:
    def __init__(self,
                 context: SupernotificationConfiguration,
                 message: str = None,
                 title: str = None,
                 target: list = None,
                 service_data: dict = None) -> None:

        self._message = message
        self.context = context
        service_data = service_data or {}
        self.target = ensure_list(target)
        self._title = title
        self.id = str(uuid.uuid1())
        self.snapshot_image_path = None

        try:
            vol.humanize.validate_with_humanized_errors(
                service_data, SERVICE_DATA_SCHEMA)
        except vol.Invalid as e:
            _LOGGER.warning(
                "SUPERNOTIFY invalid service data %s: %s", service_data, e)
            raise

        self.priority = service_data.get(ATTR_PRIORITY, PRIORITY_MEDIUM)
        self.requested_scenarios = ensure_list(
            service_data.get(ATTR_SCENARIOS))
        self.delivery_selection = service_data.get(ATTR_DELIVERY_SELECTION)
        self.delivery_overrides_type = service_data.get(
            ATTR_DELIVERY).__class__.__name__
        self.delivery_overrides = ensure_dict(service_data.get(ATTR_DELIVERY))
        self.recipients_override = service_data.get(ATTR_RECIPIENTS)
        self.common_data = service_data.get(ATTR_DATA) or {}
        self.media = service_data.get(ATTR_MEDIA) or {}

        self.selected_delivery_names = []
        self.enabled_scenarios = []

    async def initialize(self):

        if self.delivery_selection is None:
            if self.delivery_overrides_type in ('list', 'str'):
                # a bare list of deliveries implies intent to restrict
                self.delivery_selection = DELIVERY_SELECTION_EXPLICIT
            else:
                # whereas a dict may be used to tune or restrict
                self.delivery_selection = DELIVERY_SELECTION_IMPLICIT

        self.enabled_scenarios = self.requested_scenarios or []
        self.enabled_scenarios.extend(await self.select_scenarios())
        scenario_enable_deliveries = []
        default_enable_deliveries = []
        override_enable_deliveries = []
        override_disable_deliveries = []
        scenario_disable_deliveries = []

        if self.delivery_selection != DELIVERY_SELECTION_FIXED:
            for scenario in self.enabled_scenarios:
                scenario_enable_deliveries.extend(
                    self.context.delivery_by_scenario.get(scenario, ()))
            if self.delivery_selection == DELIVERY_SELECTION_IMPLICIT:
                default_enable_deliveries = self.context.delivery_by_scenario.get(
                    SCENARIO_DEFAULT, [])

        for delivery, delivery_override in self.delivery_overrides.items():
            if (delivery_override is None or delivery_override.get(CONF_ENABLED, True)) and delivery in self.context.deliveries:
                override_enable_deliveries.append(delivery)
            elif delivery_override is not None and not delivery_override.get(CONF_ENABLED, True):
                override_disable_deliveries.append(delivery)

        if self.delivery_selection != DELIVERY_SELECTION_FIXED:
            scenario_disable_deliveries = [d for d, dc in self.context.deliveries.items()
                                           if dc.get(CONF_SELECTION) == SELECTION_BY_SCENARIO
                                           and d not in scenario_enable_deliveries]
        all_enabled = list(set(scenario_enable_deliveries +
                           default_enable_deliveries + override_enable_deliveries))
        all_disabled = scenario_disable_deliveries + override_disable_deliveries
        self.selected_delivery_names = [
            d for d in all_enabled if d not in all_disabled]

    def message(self, delivery_name):
        # message and title reverse the usual defaulting, delivery config overrides runtime call
        return self.context.deliveries.get(CONF_MESSAGE, self._message)

    def title(self, delivery_name):
        # message and title reverse the usual defaulting, delivery config overrides runtime call
        return self.context.deliveries.get(CONF_TITLE, self._title)

    def delivery_data(self, delivery_name):
        delivery_override = self.delivery_overrides.get(delivery_name)
        return delivery_override.get(CONF_DATA) if delivery_override else {}

    def delivery_scenarios(self, delivery_name):
        return {k: self.context.scenarios.get(k, {}) for k in self.enabled_scenarios if delivery_name in self.context.delivery_by_scenario.get(k, [])}

    async def select_scenarios(self):
        scenarios = []
        for scenario in self.context.scenarios.values():
            if await scenario.evaluate():
                scenarios.append(scenario.name)
        return scenarios

    def core_service_data(self, delivery_name):
        data = {}
        message = self.message(delivery_name)
        title = self.title(delivery_name)
        if message:
            data[CONF_MESSAGE] = message
        if title:
            data[CONF_TITLE] = title
        return data

    def build_targets(self, delivery_config, method):

        recipients = []
        if self.target:
            # first priority is explicit target set on notify call, which overrides everything else
            for t in self.target:
                if t in self.context.people:
                    recipients.append(self.context.people[t])
                else:
                    recipients.append({ATTR_TARGET: t})
            _LOGGER.debug(
                "SUPERNOTIFY %s Overriding with explicit targets: %s", __name__, recipients)
        else:
            # second priority is explicit entities on delivery
            if delivery_config and CONF_ENTITIES in delivery_config:
                recipients.extend({ATTR_TARGET: e}
                                  for e in delivery_config.get(CONF_ENTITIES))
                _LOGGER.debug(
                    "SUPERNOTIFY %s Using delivery config entities: %s", __name__, recipients)
            # third priority is explicit target on delivery
            if delivery_config and CONF_TARGET in delivery_config:
                recipients.extend({ATTR_TARGET: e}
                                  for e in delivery_config.get(CONF_TARGET))
                _LOGGER.debug(
                    "SUPERNOTIFY %s Using delivery config targets: %s", __name__, recipients)

            # next priority is explicit recipients on delivery
            if delivery_config and CONF_RECIPIENTS in delivery_config:
                recipients.extend(delivery_config[CONF_RECIPIENTS])
                _LOGGER.debug("SUPERNOTIFY %s Using overridden recipients: %s",
                              method.method, recipients)

            # If target not specified on service call or delivery, then default to std list of recipients
            elif not delivery_config or (CONF_TARGET not in delivery_config and CONF_ENTITIES not in delivery_config):
                recipients = self.context.filter_people_by_occupancy(
                    delivery_config.get(CONF_OCCUPANCY, OCCUPANCY_ALL))
                recipients = [r for r in recipients if self.recipients_override is None or r.get(
                    CONF_PERSON) in self.recipients_override]
                _LOGGER.debug("SUPERNOTIFY %s Using recipients: %s",
                              method.method, recipients)

        # now the list of recipients determined, resolve this to target addresses or entities
        default_targets = []
        custom_targets = []
        for recipient in recipients:
            recipient_targets = []
            enabled = True
            custom_data = {}
            # reuse standard recipient attributes like email or phone
            safe_extend(recipient_targets,
                        method.recipient_target(recipient))
            # use entities or targets set at a method level for recipient
            if CONF_DELIVERY in recipient and delivery_config[CONF_NAME] in recipient.get(CONF_DELIVERY, {}):
                recp_meth_cust = recipient.get(
                    CONF_DELIVERY, {}).get(delivery_config[CONF_NAME], {})
                safe_extend(
                    recipient_targets, recp_meth_cust.get(CONF_ENTITIES, []))
                safe_extend(recipient_targets,
                            recp_meth_cust.get(CONF_TARGET, []))
                custom_data = recp_meth_cust.get(CONF_DATA)
                enabled = recp_meth_cust.get(CONF_ENABLED, True)
            elif ATTR_TARGET in recipient:
                # non person recipient
                safe_extend(default_targets, recipient.get(ATTR_TARGET))
            if enabled:
                if custom_data:
                    custom_targets.append((recipient_targets, custom_data))
                else:
                    default_targets.extend(recipient_targets)

        bundled_targets = custom_targets + [(default_targets, None)]
        filtered_bundles = []
        for targets, custom_data in bundled_targets:
            pre_filter_count = len(targets)
            _LOGGER.debug("SUPERNOTIFY Prefiltered targets: %s", targets)
            targets = [t for t in targets if method.select_target(t)]
            if len(targets) < pre_filter_count:
                _LOGGER.debug("SUPERNOTIFY %s target list filtered by %s to %s", method.method,
                              pre_filter_count-len(targets), targets)
            if not targets:
                _LOGGER.warning(
                    "SUPERNOTIFY %s No targets resolved", method.method)
            else:
                filtered_bundles.append((targets, custom_data))
        if not filtered_bundles:
            # not all delivery methods require explicit targets, or can default them internally
            filtered_bundles = [([], None)]
        return filtered_bundles

    async def grab_image(self):
        snapshot_url = self.media.get(ATTR_MEDIA_SNAPSHOT_URL)
        camera_entity_id = self.media.get(ATTR_MEDIA_CAMERA_ENTITY_ID)
        mqtt_topic = self.media.get(CONF_MQTT_TOPIC)
        image_path = None
        if self.snapshot_image_path is not None:
            return self.snapshot_image_path
        elif snapshot_url and self.context.media_path:
            image_path = await snapshot_from_url(self.context.hass, snapshot_url,
                                                 self.id, self.context.media_path,
                                                 self.context.hass_base_url)
        elif camera_entity_id:
            active_camera_entity_id = select_avail_camera(self.context.hass,
                                                          self.context.cameras,
                                                          camera_entity_id)
            camera_config = self.context.cameras.get(
                active_camera_entity_id, {})
            camera_delay = self.media.get(
                ATTR_MEDIA_CAMERA_DELAY, camera_config.get(CONF_PTZ_DELAY))
            camera_ptz_preset_default = camera_config.get(
                CONF_PTZ_PRESET_DEFAULT)
            camera_ptz_preset = self.media.get(ATTR_MEDIA_CAMERA_PTZ_PRESET)

            if camera_ptz_preset:
                await move_camera_to_ptz_preset(self.context.hass, active_camera_entity_id, camera_ptz_preset)
            image_path = await snap_camera(self.context.hass,
                                           active_camera_entity_id,
                                           camera_delay, self.context.media_path)
            if camera_ptz_preset and camera_ptz_preset_default:
                await move_camera_to_ptz_preset(self.context.hass, active_camera_entity_id, camera_ptz_preset_default)
        elif mqtt_topic:
            pass

        if image_path is None:
            _LOGGER.warning("SUPERNOTIFY No media available to attach")
        else:
            return image_path
