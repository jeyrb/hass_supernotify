import asyncio
import copy
import logging
import os.path
from homeassistant.helpers.json import save_json
import voluptuous as vol
from homeassistant.components.notify import (
    ATTR_DATA,
)
from custom_components.supernotify.common import safe_extend
from homeassistant.components.notify import (
    ATTR_TARGET,
)
from .media_grab import move_camera_to_ptz_preset, select_avail_camera, snap_camera, snap_image, snapshot_from_url
from homeassistant.const import (
    CONF_ENABLED,
    CONF_ENTITIES,
    CONF_NAME,
    CONF_TARGET,
)
import uuid

from . import (
    ATTR_DEBUG,
    ATTR_DELIVERY,
    ATTR_DELIVERY_SELECTION,
    ATTR_JPEG_FLAGS,
    ATTR_MEDIA,
    ATTR_MEDIA_CAMERA_DELAY,
    ATTR_MEDIA_CAMERA_ENTITY_ID,
    ATTR_MEDIA_CAMERA_PTZ_PRESET,
    ATTR_MEDIA_SNAPSHOT_URL,
    ATTR_MESSAGE_HTML,
    ATTR_PRIORITY,
    ATTR_RECIPIENTS,
    ATTR_SCENARIOS,
    CONF_DATA,
    CONF_DELIVERY,
    CONF_OPTIONS,
    CONF_MESSAGE,
    CONF_OCCUPANCY,
    CONF_PERSON,
    CONF_PTZ_DELAY,
    CONF_PTZ_METHOD,
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
    def __init__(
        self,
        context: SupernotificationConfiguration,
        message: str = None,
        title: str = None,
        target: list = None,
        service_data: dict = None,
    ) -> None:

        self._message = message
        self.context = context
        service_data = service_data or {}
        self.target = ensure_list(target)
        self._title = title
        self.id = str(uuid.uuid1())
        self.snapshot_image_path = None
        self.delivered = 0
        self.errored = 0
        self.skipped = 0
        self.delivered_envelopes = []

        try:
            vol.humanize.validate_with_humanized_errors(service_data, SERVICE_DATA_SCHEMA)
        except vol.Invalid as e:
            _LOGGER.warning("SUPERNOTIFY invalid service data %s: %s", service_data, e)
            raise

        self.priority = service_data.get(ATTR_PRIORITY, PRIORITY_MEDIUM)
        self.message_html = service_data.get(ATTR_MESSAGE_HTML)
        self.requested_scenarios = ensure_list(service_data.get(ATTR_SCENARIOS))
        self.delivery_selection = service_data.get(ATTR_DELIVERY_SELECTION)
        self.delivery_overrides_type = service_data.get(ATTR_DELIVERY).__class__.__name__
        self.delivery_overrides = ensure_dict(service_data.get(ATTR_DELIVERY))
        self.recipients_override = service_data.get(ATTR_RECIPIENTS)
        self.data = service_data.get(ATTR_DATA) or {}
        self.media = service_data.get(ATTR_MEDIA) or {}
        self.debug = service_data.get(ATTR_DEBUG, False)
        self.delivery_results = {}

        self.selected_delivery_names = []
        self.enabled_scenarios = []

    async def initialize(self):

        if self.delivery_selection is None:
            if self.delivery_overrides_type in ("list", "str"):
                # a bare list of deliveries implies intent to restrict
                self.delivery_selection = DELIVERY_SELECTION_EXPLICIT
            else:
                # whereas a dict may be used to tune or restrict
                self.delivery_selection = DELIVERY_SELECTION_IMPLICIT

        self.enabled_scenarios = self.requested_scenarios or []
        self.enabled_scenarios.extend(await self.select_scenarios())
        scenario_enable_deliveries = []
        default_enable_deliveries = []
        scenario_disable_deliveries = []

        if self.delivery_selection != DELIVERY_SELECTION_FIXED:
            for scenario in self.enabled_scenarios:
                scenario_enable_deliveries.extend(self.context.delivery_by_scenario.get(scenario, ()))
            if self.delivery_selection == DELIVERY_SELECTION_IMPLICIT:
                default_enable_deliveries = self.context.delivery_by_scenario.get(SCENARIO_DEFAULT, [])

        override_enable_deliveries = []
        override_disable_deliveries = []

        for delivery, delivery_override in self.delivery_overrides.items():
            if (delivery_override is None or delivery_override.get(CONF_ENABLED, True)) and delivery in self.context.deliveries:
                override_enable_deliveries.append(delivery)
            elif delivery_override is not None and not delivery_override.get(CONF_ENABLED, True):
                override_disable_deliveries.append(delivery)

        if self.delivery_selection != DELIVERY_SELECTION_FIXED:
            scenario_disable_deliveries = [
                d
                for d, dc in self.context.deliveries.items()
                if dc.get(CONF_SELECTION) == SELECTION_BY_SCENARIO and d not in scenario_enable_deliveries
            ]
        all_enabled = list(set(scenario_enable_deliveries + default_enable_deliveries + override_enable_deliveries))
        all_disabled = scenario_disable_deliveries + override_disable_deliveries
        self.selected_delivery_names = [d for d in all_enabled if d not in all_disabled]

    def message(self, delivery_name):
        # message and title reverse the usual defaulting, delivery config overrides runtime call
        return self.context.deliveries.get(CONF_MESSAGE, self._message)

    def title(self, delivery_name):
        # message and title reverse the usual defaulting, delivery config overrides runtime call
        return self.context.deliveries.get(CONF_TITLE, self._title)

    async def deliver(self):
        for delivery in self.selected_delivery_names:
            await self.call_delivery_method(delivery)

        if self.delivered == 0 and self.errored == 0:
            for delivery in self.context.fallback_by_default:
                if delivery not in self.selected_delivery_names:
                    await self.call_delivery_method(delivery)

        if self.delivered == 0 and self.errored > 0:
            for delivery in self.context.fallback_on_error:
                if delivery not in self.selected_delivery_names:
                    await self.call_delivery_method(delivery)

    async def call_delivery_method(self, delivery):
        try:
            envelopes = await self.context.delivery_method(delivery).deliver(self, delivery=delivery)
            if envelopes is not None:
                self.delivered_envelopes.extend(envelopes)
        except Exception as e:
            _LOGGER.warning("SUPERNOTIFY Failed to notify using %s: %s", delivery, e)
            _LOGGER.debug("SUPERNOTIFY %s delivery failure", delivery, exc_info=True)

    def hash(self):
        return hash((self._message, self._title))

    def contents(self):
        sanitized = {k: v for k, v in self.__dict__.items() if k not in ("context")}
        sanitized["delivered_envelopes"] = [e.contents() for e in self.delivered_envelopes]
        return sanitized

    def archive(self, path):
        if not path:
            return
        try:
            filename = os.path.join(path, "%s.json" % self.id)
            save_json(filename, self.contents())
            _LOGGER.debug("SUPERNOTIFY Archived notification %s", filename)
        except Exception as e:
            _LOGGER.warning("SUPERNOTIFY Unable to archived notification: %s", e)

    def delivery_data(self, delivery_name):
        delivery_override = self.delivery_overrides.get(delivery_name)
        return delivery_override.get(CONF_DATA) if delivery_override else {}

    def delivery_scenarios(self, delivery_name):
        return {
            k: self.context.scenarios.get(k, {})
            for k in self.enabled_scenarios
            if delivery_name in self.context.delivery_by_scenario.get(k, [])
        }

    async def select_scenarios(self):
        scenarios = []
        for scenario in self.context.scenarios.values():
            if await scenario.evaluate():
                scenarios.append(scenario.name)
        return scenarios

    def merge(self, attribute, delivery_name):
        delivery = self.delivery_overrides.get(delivery_name, {})
        base = delivery.get(attribute, {})
        for scenario_name in self.enabled_scenarios:
            scenario = self.context.scenarios.get(scenario_name)
            if scenario and hasattr(scenario, attribute):
                base.update(getattr(scenario, attribute))
        if hasattr(self, attribute):
            base.update(getattr(self, attribute))
        return base

    def build_targets(self, delivery_config, method):
        delivery_name = delivery_config.get(CONF_NAME)

        recipients = []
        if self.target:
            # first priority is explicit target set on notify call, which overrides everything else
            for t in self.target:
                if t in self.context.people:
                    recipients.append(self.context.people[t])
                else:
                    recipients.append({ATTR_TARGET: t})
            _LOGGER.debug("SUPERNOTIFY %s Overriding with explicit targets: %s", __name__, recipients)
        else:
            # second priority is explicit entities on delivery
            if delivery_config and CONF_ENTITIES in delivery_config:
                recipients.extend({ATTR_TARGET: e} for e in delivery_config.get(CONF_ENTITIES))
                _LOGGER.debug("SUPERNOTIFY %s Using delivery config entities: %s", __name__, recipients)
            # third priority is explicit target on delivery
            if delivery_config and CONF_TARGET in delivery_config:
                recipients.extend({ATTR_TARGET: e} for e in delivery_config.get(CONF_TARGET))
                _LOGGER.debug("SUPERNOTIFY %s Using delivery config targets: %s", __name__, recipients)

            # next priority is explicit recipients on delivery
            if delivery_config and CONF_RECIPIENTS in delivery_config:
                recipients.extend(delivery_config[CONF_RECIPIENTS])
                _LOGGER.debug("SUPERNOTIFY %s Using overridden recipients: %s", method.method, recipients)

            # If target not specified on service call or delivery, then default to std list of recipients
            elif not delivery_config or (CONF_TARGET not in delivery_config and CONF_ENTITIES not in delivery_config):
                recipients = self.context.filter_people_by_occupancy(delivery_config.get(CONF_OCCUPANCY, OCCUPANCY_ALL))
                recipients = [
                    r for r in recipients if self.recipients_override is None or r.get(CONF_PERSON) in self.recipients_override
                ]
                _LOGGER.debug("SUPERNOTIFY %s Using recipients: %s", method.method, recipients)

        # now the list of recipients determined, resolve this to target addresses or entities
        default_targets = []
        custom_envelopes = []
        default_data = delivery_config.get(CONF_DATA)
        for recipient in recipients:
            recipient_targets = []
            enabled = True
            custom_data = default_data or {}
            # reuse standard recipient attributes like email or phone
            safe_extend(recipient_targets, method.recipient_target(recipient))
            # use entities or targets set at a method level for recipient
            if CONF_DELIVERY in recipient and delivery_config[CONF_NAME] in recipient.get(CONF_DELIVERY, {}):
                recp_meth_cust = recipient.get(CONF_DELIVERY, {}).get(delivery_config[CONF_NAME], {})
                safe_extend(recipient_targets, recp_meth_cust.get(CONF_ENTITIES, []))
                safe_extend(recipient_targets, recp_meth_cust.get(CONF_TARGET, []))
                custom_data = recp_meth_cust.get(CONF_DATA)
                enabled = recp_meth_cust.get(CONF_ENABLED, True)
            elif ATTR_TARGET in recipient:
                # non person recipient
                safe_extend(default_targets, recipient.get(ATTR_TARGET))
            if enabled:
                if custom_data:
                    custom_envelopes.append(Envelope(delivery_name, self, recipient_targets, custom_data))
                else:
                    default_targets.extend(recipient_targets)

        bundled_envelopes = custom_envelopes + [Envelope(delivery_name, self, default_targets, default_data)]
        filtered_envelopes = []
        for envelope in bundled_envelopes:
            pre_filter_count = len(envelope.targets)
            _LOGGER.debug("SUPERNOTIFY Prefiltered targets: %s", envelope.targets)
            targets = [t for t in envelope.targets if method.select_target(t)]
            if len(targets) < pre_filter_count:
                _LOGGER.debug(
                    "SUPERNOTIFY %s target list filtered by %s to %s", method.method, pre_filter_count - len(targets), targets
                )
            if not targets:
                _LOGGER.debug("SUPERNOTIFY %s No targets resolved out of %s", method.method, pre_filter_count)
            else:
                envelope.targets = targets
                filtered_envelopes.append(envelope)
        if not filtered_envelopes:
            # not all delivery methods require explicit targets, or can default them internally
            filtered_envelopes = [Envelope(delivery_name, self, data=default_data)]
        return filtered_envelopes

    async def grab_image(self, delivery_name):
        snapshot_url = self.media.get(ATTR_MEDIA_SNAPSHOT_URL)
        camera_entity_id = self.media.get(ATTR_MEDIA_CAMERA_ENTITY_ID)
        delivery_config = self.delivery_data(delivery_name)
        jpeg_args = self.media.get(ATTR_JPEG_FLAGS, delivery_config.get(CONF_OPTIONS, {}).get(ATTR_JPEG_FLAGS))

        if not snapshot_url and not camera_entity_id:
            return

        image_path = None
        if self.snapshot_image_path is not None:
            return self.snapshot_image_path
        elif snapshot_url and self.context.media_path:
            image_path = await snapshot_from_url(
                self.context.hass, snapshot_url, self.id, self.context.media_path, self.context.hass_internal_url, jpeg_args
            )
        elif camera_entity_id and camera_entity_id.startswith("image."):
            image_path = await snap_image(self.context.hass, camera_entity_id, self.context.media_path, self.id, jpeg_args)
        elif camera_entity_id:
            active_camera_entity_id = await select_avail_camera(self.context.hass, self.context.cameras, camera_entity_id)
            if active_camera_entity_id:
                camera_config = self.context.cameras.get(active_camera_entity_id, {})
                camera_delay = self.media.get(ATTR_MEDIA_CAMERA_DELAY, camera_config.get(CONF_PTZ_DELAY))
                camera_ptz_preset_default = camera_config.get(CONF_PTZ_PRESET_DEFAULT)
                camera_ptz_method = camera_config.get(CONF_PTZ_METHOD)
                camera_ptz_preset = self.media.get(ATTR_MEDIA_CAMERA_PTZ_PRESET)
                _LOGGER.debug(
                    "SUPERNOTIFY snapping camera %s, ptz %s->%s, delay %s secs",
                    active_camera_entity_id,
                    camera_ptz_preset,
                    camera_ptz_preset_default,
                    camera_delay,
                )
                if camera_ptz_preset:
                    await move_camera_to_ptz_preset(
                        self.context.hass, active_camera_entity_id, camera_ptz_preset, method=camera_ptz_method
                    )
                if camera_delay:
                    _LOGGER.debug("SUPERNOTIFY Waiting %s secs before snapping", camera_delay)
                    await asyncio.sleep(camera_delay)
                image_path = await snap_camera(
                    self.context.hass,
                    active_camera_entity_id,
                    media_path=self.context.media_path,
                    timeout=15,
                    jpeg_args=jpeg_args,
                )
                if camera_ptz_preset and camera_ptz_preset_default:
                    await move_camera_to_ptz_preset(
                        self.context.hass, active_camera_entity_id, camera_ptz_preset_default, method=camera_ptz_method
                    )

        if image_path is None:
            _LOGGER.warning("SUPERNOTIFY No media available to attach (%s,%s)", snapshot_url, camera_entity_id)
        else:
            return image_path


class Envelope:
    """
    Wrap a notification with a specific set of targets and service data possibly customized for those targets
    """

    def __init__(self, delivery_name, notification, targets=None, data=None):
        self.targets = targets or []
        self.delivery_name = delivery_name
        self._notification = notification
        self.notification_id = notification.id
        self.media = notification.media
        self.priority = notification.priority
        self.message = notification.message(delivery_name)
        self.message_html = notification.message_html
        self.title = notification.title(delivery_name)
        delivery_config_data = notification.delivery_data(delivery_name)
        if data:
            self.data = copy.deepcopy(delivery_config_data) if delivery_config_data else {}
            self.data |= data
        else:
            self.data = delivery_config_data

        self.delivered = 0
        self.errored = 0

    def grab_image(self):
        return self._notification.grab_image(self.delivery_name)

    def core_service_data(self):
        data = {}
        # message is mandatory for notify platform
        data[CONF_MESSAGE] = self.message or ""
        if self.title:
            data[CONF_TITLE] = self.title
        return data

    def contents(self):
        sanitized = {k: v for k, v in self.__dict__.items() if k not in ("_notification")}
        return sanitized

    def __eq__(self, other):
        if not isinstance(other, Envelope):
            return False
        return (
            self.targets == other.targets
            and self.delivery_name == other.delivery_name
            and self.data == other.data
            and self.notification_id == other.notification_id
        )
