import asyncio
import datetime as dt
import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from traceback import format_exception
from typing import Any, cast

import voluptuous as vol
from homeassistant.components.notify import ATTR_DATA, ATTR_TARGET
from homeassistant.const import ATTR_STATE, CONF_ENABLED, CONF_ENTITIES, CONF_NAME, CONF_TARGET, STATE_HOME
from homeassistant.helpers.json import save_json
from voluptuous import humanize

from custom_components.supernotify.common import safe_extend
from custom_components.supernotify.delivery_method import DeliveryMethod
from custom_components.supernotify.envelope import Envelope
from custom_components.supernotify.scenario import Scenario

from . import (
    ATTR_ACTIONS,
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
    CONF_MESSAGE,
    CONF_METHOD,
    CONF_OCCUPANCY,
    CONF_OPTIONS,
    CONF_PERSON,
    CONF_PRIORITY,
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
    OCCUPANCY_ALL_IN,
    OCCUPANCY_ALL_OUT,
    OCCUPANCY_ANY_IN,
    OCCUPANCY_ANY_OUT,
    OCCUPANCY_NONE,
    OCCUPANCY_ONLY_IN,
    OCCUPANCY_ONLY_OUT,
    PRIORITY_CRITICAL,
    PRIORITY_MEDIUM,
    SCENARIO_DEFAULT,
    SELECTION_BY_SCENARIO,
    SERVICE_DATA_SCHEMA,
    STRICT_SERVICE_DATA_SCHEMA,
    GlobalTargetType,
    QualifiedTargetType,
    Snooze,
)
from .common import ensure_dict, ensure_list
from .configuration import SupernotificationConfiguration
from .media_grab import move_camera_to_ptz_preset, select_avail_camera, snap_camera, snap_image, snapshot_from_url

_LOGGER = logging.getLogger(__name__)


class Notification:
    def __init__(
        self,
        context: SupernotificationConfiguration,
        message: str | None = None,
        title: str | None = None,
        target: list | str | None = None,
        service_data: dict | None = None,
    ) -> None:
        self.created: dt.datetime = dt.datetime.now(tz=dt.UTC)
        self.debug_trace: DebugTrace = DebugTrace(message=message, title=title, data=service_data, target=target)
        self._message: str | None = message
        self.context: SupernotificationConfiguration = context
        service_data = service_data or {}
        self.target: list = ensure_list(target)
        self._title: str | None = title
        self.id = str(uuid.uuid1())
        self.snapshot_image_path: Path | None = None
        self.delivered: int = 0
        self.errored: int = 0
        self.skipped: int = 0
        self.delivered_envelopes: list[Envelope] = []
        self.undelivered_envelopes: list[Envelope] = []

        try:
            humanize.validate_with_humanized_errors(service_data, SERVICE_DATA_SCHEMA)
        except vol.Invalid as e:
            _LOGGER.warning("SUPERNOTIFY invalid service data %s: %s", service_data, e)
            raise
        # for compatibility with other notify calls, pass thru surplus data to underlying delivery methods
        self.data = {k: v for k, v in service_data.items() if k not in STRICT_SERVICE_DATA_SCHEMA(service_data)}
        service_data = {k: v for k, v in service_data.items() if k not in self.data}

        self.priority: str = service_data.get(ATTR_PRIORITY, PRIORITY_MEDIUM)
        self.message_html: str | None = service_data.get(ATTR_MESSAGE_HTML)
        self.requested_scenarios: list = ensure_list(service_data.get(ATTR_SCENARIOS))
        self.delivery_selection: str | None = service_data.get(ATTR_DELIVERY_SELECTION)
        self.delivery_overrides_type: str = service_data.get(ATTR_DELIVERY).__class__.__name__
        self.delivery_overrides: dict = ensure_dict(service_data.get(ATTR_DELIVERY))
        self.recipients_override: list[str] | None = service_data.get(ATTR_RECIPIENTS)
        self.data.update(service_data.get(ATTR_DATA, {}))
        self.media: dict = service_data.get(ATTR_MEDIA) or {}
        self.debug: bool = service_data.get(ATTR_DEBUG, False)
        self.actions: dict = service_data.get(ATTR_ACTIONS) or {}
        self.delivery_results: dict = {}
        self.delivery_errors: dict = {}
        self.inscope_snoozes: list[Snooze] = []

        self.selected_delivery_names: list[str] = []
        self.enabled_scenarios: list[str] = []
        self.people_by_occupancy: list = []

    async def initialize(self) -> None:
        """Async post-construction initialization"""
        if self.delivery_selection is None:
            if self.delivery_overrides_type in ("list", "str"):
                # a bare list of deliveries implies intent to restrict
                self.delivery_selection = DELIVERY_SELECTION_EXPLICIT
            else:
                # whereas a dict may be used to tune or restrict
                self.delivery_selection = DELIVERY_SELECTION_IMPLICIT

        self.enabled_scenarios = self.requested_scenarios or []
        self.enabled_scenarios.extend(await self.select_scenarios())
        scenario_enable_deliveries: list[str] = []
        default_enable_deliveries: list[str] = []
        scenario_disable_deliveries: list[str] = []

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
        self.globally_disabled, inscope_snoozes = self.check_for_snoozes()
        self.inscope_snoozes = inscope_snoozes

    def message(self, delivery_name: str) -> str | None:
        # message and title reverse the usual defaulting, delivery config overrides runtime call
        return self.context.deliveries.get(delivery_name, {}).get(CONF_MESSAGE, self._message)

    def title(self, delivery_name: str) -> str | None:
        # message and title reverse the usual defaulting, delivery config overrides runtime call
        return self.context.deliveries.get(delivery_name, {}).get(CONF_TITLE, self._title)

    async def deliver(self) -> None:
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

    async def call_delivery_method(self, delivery: str) -> None:
        try:
            delivery_method: DeliveryMethod = self.context.delivery_method(delivery)
            delivery_config = delivery_method.delivery_config(delivery)

            delivery_priorities = delivery_config.get(CONF_PRIORITY) or ()
            if self.priority and delivery_priorities and self.priority not in delivery_priorities:
                _LOGGER.debug("SUPERNOTIFY Skipping delivery %s based on priority (%s)", delivery, self.priority)
                self.skipped += 1
                return
            if not await delivery_method.evaluate_delivery_conditions(delivery_config):
                _LOGGER.debug("SUPERNOTIFY Skipping delivery %s based on conditions", delivery)
                self.skipped += 1
                return

            recipients = self.generate_recipients(delivery, delivery_method)
            envelopes = self.generate_envelopes(delivery, delivery_method, recipients)
            for envelope in envelopes:
                try:
                    await delivery_method.deliver(envelope)
                    self.delivered += envelope.delivered
                    self.errored += envelope.errored
                    self.delivered_envelopes.append(envelope)
                except Exception as e:
                    _LOGGER.warning("SUPERNOTIFY Failed to deliver %s: %s", envelope.delivery_name, e)
                    _LOGGER.debug("SUPERNOTIFY %s", e, exc_info=True)
                    self.errored += 1
                    envelope.delivery_error = format_exception(e)
                    self.undelivered_envelopes.append(envelope)

        except Exception as e:
            _LOGGER.warning("SUPERNOTIFY Failed to notify using %s: %s", delivery, e)
            _LOGGER.debug("SUPERNOTIFY %s delivery failure", delivery, exc_info=True)
            self.delivery_errors[delivery] = format_exception(e)

    def hash(self) -> int:
        return hash((self._message, self._title))

    def contents(self, minimal: bool = False) -> dict[str, Any]:
        sanitized = {k: v for k, v in self.__dict__.items() if k not in ("context")}
        sanitized["delivered_envelopes"] = [e.contents(minimal=minimal) for e in self.delivered_envelopes]
        return sanitized

    def archive(self, path: Path) -> None:
        if not path:
            return
        filename: Path = path / f"{self.created.isoformat()[:16]}_{self.id}.json"
        try:
            save_json(str(filename), self.contents())
            _LOGGER.debug("SUPERNOTIFY Archived notification %s", filename)
        except Exception as e:
            _LOGGER.warning("SUPERNOTIFY Unable to archived notification: %s", e)
            try:
                save_json(str(filename), self.contents(minimal=True))
                _LOGGER.debug("SUPERNOTIFY Archived pruned notification %s", filename)
            except Exception as e:
                _LOGGER.error("SUPERNOTIFY Unable to archived pruned notification: %s", e)

    def delivery_data(self, delivery_name: str) -> dict:
        delivery_override = self.delivery_overrides.get(delivery_name)
        return delivery_override.get(CONF_DATA) if delivery_override else {}

    def delivery_scenarios(self, delivery_name: str) -> dict[str, Scenario]:
        return {
            k: cast(Scenario, self.context.scenarios.get(k))
            for k in self.enabled_scenarios
            if delivery_name in self.context.delivery_by_scenario.get(k, [])
        }

    async def select_scenarios(self) -> list[str]:
        return [s.name for s in self.context.scenarios.values() if await s.evaluate()]

    def merge(self, attribute: str, delivery_name: str) -> dict:
        delivery: dict = self.delivery_overrides.get(delivery_name, {})
        base: dict = delivery.get(attribute, {})
        for scenario_name in self.enabled_scenarios:
            scenario = self.context.scenarios.get(scenario_name)
            if scenario and hasattr(scenario, attribute):
                base.update(getattr(scenario, attribute))
        if hasattr(self, attribute):
            base.update(getattr(self, attribute))
        return base

    def record_resolve(self, delivery_name: str, category: str, resolved: str | list | None) -> None:
        """Debug support for recording detailed target resolution in archived notification"""
        self.debug_trace.resolved.setdefault(delivery_name, {})
        self.debug_trace.resolved[delivery_name].setdefault(category, [])
        if isinstance(resolved, list):
            self.debug_trace.resolved[delivery_name][category].extend(resolved)
        else:
            self.debug_trace.resolved[delivery_name][category].append(resolved)

    def filter_people_by_occupancy(self, occupancy: str) -> list[dict]:
        people = list(self.context.people.values())
        if occupancy == OCCUPANCY_ALL:
            return people
        if occupancy == OCCUPANCY_NONE:
            return []

        at_home = []
        away = []
        for person_config in self.context.people_state():
            if person_config.get(ATTR_STATE) in (None, STATE_HOME):
                # default to at home if unknown tracker
                at_home.append(person_config)
            else:
                away.append(person_config)
        if occupancy == OCCUPANCY_ALL_IN:
            return people if len(away) == 0 else []
        if occupancy == OCCUPANCY_ALL_OUT:
            return people if len(at_home) == 0 else []
        if occupancy == OCCUPANCY_ANY_IN:
            return people if len(at_home) > 0 else []
        if occupancy == OCCUPANCY_ANY_OUT:
            return people if len(away) > 0 else []
        if occupancy == OCCUPANCY_ONLY_IN:
            return at_home
        if occupancy == OCCUPANCY_ONLY_OUT:
            return away

        _LOGGER.warning("SUPERNOTIFY Unknown occupancy tested: %s", occupancy)
        return []

    def generate_recipients(self, delivery_name: str, delivery_method: DeliveryMethod) -> list[dict]:
        delivery_config: dict[str, Any] = delivery_method.delivery_config(delivery_name)

        recipients = []
        if self.target:
            # first priority is explicit target set on notify call, which overrides everything else
            for t in self.target:
                if t in self.context.people:
                    recipients.append(self.context.people[t])
                    self.record_resolve(delivery_name, "1a_person_target", self.context.people[t])
                else:
                    recipients.append({ATTR_TARGET: t})
                    self.record_resolve(delivery_name, "1b_non_person_target", t)
            _LOGGER.debug("SUPERNOTIFY %s Overriding with explicit targets: %s", __name__, recipients)
        else:
            # second priority is explicit entities on delivery
            if delivery_config and CONF_ENTITIES in delivery_config:
                recipients.extend({ATTR_TARGET: e} for e in delivery_config.get(CONF_ENTITIES, []))
                self.record_resolve(delivery_name, "2a_delivery_config_entity", delivery_config.get(CONF_ENTITIES))
                _LOGGER.debug("SUPERNOTIFY %s Using delivery config entities: %s", __name__, recipients)
            # third priority is explicit target on delivery
            if delivery_config and CONF_TARGET in delivery_config:
                recipients.extend({ATTR_TARGET: e} for e in delivery_config.get(CONF_TARGET, []))
                self.record_resolve(delivery_name, "2b_delivery_config_target", delivery_config.get(CONF_TARGET))
                _LOGGER.debug("SUPERNOTIFY %s Using delivery config targets: %s", __name__, recipients)

            # next priority is explicit recipients on delivery
            if delivery_config and CONF_RECIPIENTS in delivery_config:
                recipients.extend(delivery_config[CONF_RECIPIENTS])
                self.record_resolve(delivery_name, "2c_delivery_config_recipient", delivery_config.get(CONF_RECIPIENTS))
                _LOGGER.debug("SUPERNOTIFY %s Using overridden recipients: %s", delivery_name, recipients)

            # If target not specified on service call or delivery, then default to std list of recipients
            elif not delivery_config or (CONF_TARGET not in delivery_config and CONF_ENTITIES not in delivery_config):
                recipients = self.filter_people_by_occupancy(delivery_config.get(CONF_OCCUPANCY, OCCUPANCY_ALL))
                self.record_resolve(delivery_name, "2d_recipients_by_occupancy", recipients)
                recipients = [
                    r for r in recipients if self.recipients_override is None or r.get(CONF_PERSON) in self.recipients_override
                ]
                self.record_resolve(
                    delivery_name, "2d_recipient_names_by_occupancy_filtered", [r.get(CONF_PERSON) for r in recipients]
                )
                _LOGGER.debug("SUPERNOTIFY %s Using recipients: %s", delivery_name, recipients)

        # snoozes = self.context.snoozes
        return recipients

    def generate_envelopes(self, delivery_name: str, method: DeliveryMethod, recipients: list[dict]) -> list[Envelope]:
        # now the list of recipients determined, resolve this to target addresses or entities

        delivery_config: dict = method.delivery_config(delivery_name)
        default_data: dict = delivery_config.get(CONF_DATA, {})
        default_targets: list = []
        custom_envelopes: list = []

        for recipient in recipients:
            recipient_targets: list = []
            enabled: bool = True
            custom_data: dict = {}
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
                    envelope_data = {}
                    envelope_data.update(default_data)
                    envelope_data.update(self.data)
                    envelope_data.update(custom_data)
                    custom_envelopes.append(Envelope(delivery_name, self, recipient_targets, envelope_data))
                else:
                    default_targets.extend(recipient_targets)

        envelope_data = {}
        envelope_data.update(default_data)
        envelope_data.update(self.data)

        bundled_envelopes = [*custom_envelopes, Envelope(delivery_name, self, default_targets, envelope_data)]
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
            filtered_envelopes = [Envelope(delivery_name, self, data=envelope_data)]
        return filtered_envelopes

    async def grab_image(self, delivery_name: str) -> Path | None:
        snapshot_url = self.media.get(ATTR_MEDIA_SNAPSHOT_URL)
        camera_entity_id = self.media.get(ATTR_MEDIA_CAMERA_ENTITY_ID)
        delivery_config = self.delivery_data(delivery_name)
        jpeg_args = self.media.get(ATTR_JPEG_FLAGS, delivery_config.get(CONF_OPTIONS, {}).get(ATTR_JPEG_FLAGS))

        if not snapshot_url and not camera_entity_id:
            return None

        image_path: Path | None = None
        if self.snapshot_image_path is not None:
            return self.snapshot_image_path
        if snapshot_url and self.context.media_path and self.context.hass:
            image_path = await snapshot_from_url(
                self.context.hass, snapshot_url, self.id, self.context.media_path, self.context.hass_internal_url, jpeg_args
            )
        elif camera_entity_id and camera_entity_id.startswith("image.") and self.context.hass and self.context.media_path:
            image_path = await snap_image(self.context.hass, camera_entity_id, self.context.media_path, self.id, jpeg_args)
        elif camera_entity_id:
            if not self.context.hass or not self.context.media_path:
                _LOGGER.warning("SUPERNOTIFY No homeassistant ref or media path for camera %s", camera_entity_id)
                return None
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
            return None
        self.snapshot_image_path = image_path
        return image_path

    def check_for_snoozes(self) -> tuple[bool, list[Snooze]]:
        inscope_snoozes: list[Snooze] = []
        if len(self.context.snoozes) == 0:
            return (False, inscope_snoozes)
        for snooze in self.context.snoozes.values():
            if snooze.active():
                match snooze.target_type:
                    case GlobalTargetType.EVERYTHING:
                        return (True, inscope_snoozes)
                    case GlobalTargetType.NONCRITICAL:
                        if self.priority != PRIORITY_CRITICAL:
                            return (True, inscope_snoozes)
                    case QualifiedTargetType.DELIVERY:
                        if snooze.target in self.selected_delivery_names:
                            inscope_snoozes.append(snooze)
                    case QualifiedTargetType.PRIORITY:
                        if snooze.target == self.priority:
                            inscope_snoozes.append(snooze)
                    case QualifiedTargetType.METHOD:
                        if snooze.target in [
                            self.context.deliveries.get(d, {}).get(CONF_METHOD) for d in self.selected_delivery_names
                        ]:
                            inscope_snoozes.append(snooze)
                    case QualifiedTargetType.CAMERA:
                        inscope_snoozes.append(snooze)
                    case QualifiedTargetType.LABEL:
                        inscope_snoozes.append(snooze)
                    case _:
                        _LOGGER.warning("SUPERNOTIFY Unhandled target type %s", snooze.target_type)

        return (False, inscope_snoozes)


@dataclass
class DebugTrace:
    message: str | None = field(default=None)
    title: str | None = field(default=None)
    data: dict | None = field(default_factory=lambda: {})
    target: list | str | None = field(default=None)
    resolved: dict = field(init=False, default_factory=lambda: {})
