from http import HTTPStatus
import logging
import voluptuous as vol
from homeassistant.components.notify import (
    ATTR_DATA,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.const import (
    CONF_ENABLED,
)
import time
import uuid
import tempfile

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
    CONF_MESSAGE,
    CONF_MQTT_TOPIC,
    CONF_SELECTION,
    CONF_TITLE,
    DELIVERY_SELECTION_EXPLICIT,
    DELIVERY_SELECTION_FIXED,
    DELIVERY_SELECTION_IMPLICIT,
    PRIORITY_MEDIUM,
    SCENARIO_DEFAULT,
    SELECTION_BY_SCENARIO,
    SERVICE_DATA_SCHEMA,
)
from .configuration import SupernotificationConfiguration, ensure_list, ensure_dict
import os
import os.path

_LOGGER = logging.getLogger(__name__)


class Notification:
    def __init__(self,
                 context: SupernotificationConfiguration,
                 message: str = None,
                 title: str = None,
                 target: list = None,
                 service_data: dict = None,
                 delivery_config: dict = None) -> None:

        self._message = message
        self.context = context
        service_data = service_data or {}
        self.target = ensure_list(target)
        self._title = title
        self.delivery_config = delivery_config or {}
        self.id = str(uuid.uuid1())
        self.snapshot_image_path = None

        try:
            SERVICE_DATA_SCHEMA(service_data)
        except vol.Invalid as e:
            _LOGGER.warning(
                "SUPERNOTIFY invalid service data %s: %s", service_data, e)
            raise

        self.priority = service_data.get(ATTR_PRIORITY, PRIORITY_MEDIUM)
        self.requested_scenarios = ensure_list(
            service_data.get(ATTR_SCENARIOS))
        self.delivery_selection = service_data.get(ATTR_DELIVERY_SELECTION)
        self.delivery_overrides = ensure_dict(service_data.get(ATTR_DELIVERY))
        self.recipients_override = service_data.get(ATTR_RECIPIENTS)
        self.common_data = service_data.get(ATTR_DATA) or {}
        self.media = service_data.get(ATTR_MEDIA) or {}

        self.selected_delivery_names = []
        self.enabled_scenarios = []
        self.media_config = service_data.get(ATTR_MEDIA) or {}

    async def intialize(self):

        if self.delivery_selection is None:
            if self.delivery_overrides or self.requested_scenarios:
                self.delivery_selection = DELIVERY_SELECTION_EXPLICIT
            else:
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
        return self.delivery_config.get(CONF_MESSAGE, self._message)
    
    def title(self, delivery_name):
        # message and title reverse the usual defaulting, delivery config overrides runtime call
        return self.delivery_config.get(CONF_TITLE, self._title)
    
    def delivery_data(self, delivery_name):
        return self.delivery_overrides.get(delivery_name, {}).get(CONF_DATA) if delivery_name else {}

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
    
    async def grab_image(self):
        
        if self.snapshot_image_path is not None:
            return self.snapshot_image_path
        snapshot_url = self.media.get(ATTR_MEDIA_SNAPSHOT_URL)
        camera_entity_id = self.media.get(ATTR_MEDIA_CAMERA_ENTITY_ID)
        camera_delay = self.media.get(ATTR_MEDIA_CAMERA_DELAY, 0)
        camera_ptz_preset = self.media.get(ATTR_MEDIA_CAMERA_PTZ_PRESET)
        camera_ptz_preset_default = None  # TODO FIX
        mqtt_topic = self.media.get(CONF_MQTT_TOPIC)

        if not snapshot_url and not camera_entity_id:
            return None

        image_path = None

        if snapshot_url:
            try:
                media_dir = os.path.join(self.context.media_path, "snapshot")
                os.makedirs(media_dir, exist_ok=True)
                if snapshot_url.startswith("http"):
                    image_url = snapshot_url
                else:
                    image_url = '%s%s' % (self.hass_base_url, snapshot_url)
                websession = async_get_clientsession(self.context.hass)
                r = await websession.get(image_url)
                if r.status != HTTPStatus.OK:
                    _LOGGER.warning(
                        "SUPERNOTIFY Unable to retrieve %s: %s", image_url, r.status)
                else:
                    if r.content_type == "image/jpeg":
                        media_ext = "jpg"
                    elif r.content_type == "image/png":
                        media_ext = "png"
                    elif r.content_type == "image/gif":
                        media_ext = "gif"
                    else:
                        media_ext = "img"
                    image_path = os.path.join(
                        media_dir, '%s.%s' % (self.id, media_ext))
                    with open(image_path, 'wb') as img_file:
                        img_file.write(await r.content.read())
                        img_file.close()
                        _LOGGER.debug(
                            'SUPERNOTIFY Fetched image from %s to %s', image_url, image_path)
            except Exception as e:
                image_path = None
                _LOGGER.error('SUPERNOTIFY Image snap fail: %s', e)

        elif camera_entity_id:
            if camera_ptz_preset:
                await self.move_camera_to_ptz_preset(camera_entity_id, camera_ptz_preset)
            image_path = self.snap_avail_camera(camera_entity_id, camera_delay)
            if camera_ptz_preset and camera_ptz_preset_default:
                await self.move_camera_to_ptz_preset(camera_entity_id, camera_ptz_preset_default)
        elif mqtt_topic:
            pass

        if image_path is None:
            _LOGGER.warning("SUPERNOTIFY No media available to attach")
        else:
            self.snapshot_image_path = image_path
            return image_path

    async def move_camera_to_ptz_preset(self, camera_entity_id, preset):
        try:
            _LOGGER.info("SUPERNOTIFY Executing PTZ to default %s for %s",
                         preset, camera_entity_id)
            await self.hass.services.async_call("onvif", "ptz",
                                                service_data={
                                                    "move_mode": 'GotoPreset',
                                                    "entity_id": camera_entity_id,
                                                    "preset": preset
                                                }
                                                )
        except Exception as e:
            _LOGGER.warning(
                "SUPERNOTIFY Unable to move %s to ptz preset %s: %s", camera_entity_id, preset, e)

    def snap_mqtt_topic(self, topic):
        pass

    def snap_avail_camera(self, camera_entity_id, camera_delay):
        image_path = None
        availableCams = [k for k, v in self.camera_tracker.items(
        ) if self.hass.get_tracker_state(v) == "home"]
        if len(availableCams) < 1:
            self.log(
                "No camera available, sending email without image", level='WARNING')
            for v in self.camera_tracker.values():
                self.log('TRACKER %s: %s', v, self.hass.get_tracker_state(v))
        else:
            if camera_entity_id in availableCams:
                availableCam = camera_entity_id
            else:
                if 'camera.driveway' in availableCams:
                    availableCam = 'camera.driveway'
                else:
                    availableCam = availableCams[0]
                self.log('No camera found in %s so using %s' %
                         (availableCams, availableCam))
            # wait for vehicle to get up to camera range
            sequence = []
            if camera_delay > 0:
                sequence.append({'sleep': '%s' % camera_delay})

            try:
                with tempfile.TemporaryDirectory(
                    dir=self.hass_shared_tmp, prefix="appd", suffix=availableCam
                ) as tmpdirname:
                    image_path = os.path.join(
                        tmpdirname, "hass_driveway_alert.jpg")
                    sequence.append({'camera/snapshot':
                                     {'entity_id': availableCam,
                                      'filename': image_path
                                      }
                                     })
                    self.hass.run_sequence(sequence)
                    # give async service time
                    cutoff_time = time.time() + 20
                    while time.time() < cutoff_time and not os.path.exists(image_path):
                        self.log(
                            'Image file not available yet at %s, pausing', image_path)
                        time.sleep(1)
            except Exception as e:
                self.error('Failed to snap avail camera %s: %s' %
                           (availableCam, e), level='ERROR')
        return image_path
