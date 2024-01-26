import asyncio
from http import HTTPStatus
import logging
from aiohttp import ClientTimeout
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import time

import os
import os.path

from custom_components.supernotify import CONF_ALT_CAMERA, CONF_CAMERA, CONF_DEVICE_TRACKER

_LOGGER = logging.getLogger(__name__)


async def snapshot_from_url(hass, snapshot_url, notification_id,
                            media_path, hass_base_url,
                            timeout=15):

    image_path = None
    try:
        media_dir = os.path.join(media_path, "snapshot")
        os.makedirs(media_dir, exist_ok=True)
        if snapshot_url.startswith("http"):
            image_url = snapshot_url
        else:
            image_url = '%s%s' % (hass_base_url, snapshot_url)
        websession = async_get_clientsession(hass)
        r = await websession.get(image_url, timeout=ClientTimeout(total=timeout))
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
                media_dir, '%s.%s' % (notification_id, media_ext))
            with open(image_path, 'wb') as img_file:
                img_file.write(await r.content.read())
                img_file.close()
                _LOGGER.debug(
                    'SUPERNOTIFY Fetched image from %s to %s', image_url, image_path)
            return image_path
    except Exception as e:
        _LOGGER.error('SUPERNOTIFY Image snap fail: %s', e)


async def move_camera_to_ptz_preset(hass, camera_entity_id, preset):
    try:
        _LOGGER.info("SUPERNOTIFY Executing PTZ to %s for %s",
                     preset, camera_entity_id)
        await hass.services.async_call("onvif", "ptz",
                                       service_data={
                                                "move_mode": 'GotoPreset',
                                                "entity_id": camera_entity_id,
                                                "preset": preset
                                       }
                                       )
    except Exception as e:
        _LOGGER.warning(
            "SUPERNOTIFY Unable to move %s to ptz preset %s: %s", camera_entity_id, preset, e)


async def snap_mqtt_topic(topic):
    pass


async def snap_camera(hass, camera_entity_id, camera_delay=None, media_path=None):

    image_path = None

    if camera_delay is not None and camera_delay > 0:
        await asyncio.sleep(camera_delay)

    try:
        media_dir = os.path.join(media_path, "camera")
        os.makedirs(media_dir, exist_ok=True)

        image_path = os.path.join(
            media_dir, "%s-%s.jpg" % (camera_entity_id, time.time()))
        await hass.services.async_call("camera", "snapshot",
                                       service_data={
                                           'entity_id': camera_entity_id,
                                           'filename': image_path
                                       }
                                       )

        # give async service time
        cutoff_time = time.time() + 20
        while time.time() < cutoff_time and not os.path.exists(image_path):
            _LOGGER.info(
                'Image file not available yet at %s, pausing', image_path)
            await asyncio.sleep(1)

    except Exception as e:
        _LOGGER.warning(
            'Failed to snap avail camera %s to %s: %s', camera_entity_id, image_path, e)
        image_path = None
        
    return image_path


async def select_avail_camera(hass, cameras, camera_entity_id):

    preferred_cam = cameras.get(camera_entity_id)
    avail_camera_entity_id = None

    if not preferred_cam or not preferred_cam.get(CONF_DEVICE_TRACKER):
        # assume unconfigured camera, or configured without tracker, available
        avail_camera_entity_id = camera_entity_id
    elif hass.get_tracker_state(preferred_cam[CONF_DEVICE_TRACKER]) == "home":
        avail_camera_entity_id = camera_entity_id
    else:
        alt_cams_with_tracker = [cameras[c] for c in preferred_cam.get(
            CONF_ALT_CAMERA, []) if c in cameras and cameras[c].get(CONF_DEVICE_TRACKER)]
        for alt_cam in alt_cams_with_tracker:
            if hass.get_tracker_state(alt_cam.get(CONF_DEVICE_TRACKER)) == "home":
                avail_camera_entity_id = alt_cam[CONF_CAMERA]
                _LOGGER.info("SUPERNOTIFY Selecting available camera %s rather than %s",
                             avail_camera_entity_id, camera_entity_id)
                break
        if avail_camera_entity_id is None:
            alt_cam_ids_without_tracker = [c for c in preferred_cam.get(
                        CONF_ALT_CAMERA, []) if c not in cameras or not cameras[c].get(CONF_DEVICE_TRACKER)]
            if len(alt_cam_ids_without_tracker) > 0:
                _LOGGER.info("SUPERNOTIFY Selecting untracked camera %s rather than %s",
                             avail_camera_entity_id, camera_entity_id)
                avail_camera_entity_id = alt_cam_ids_without_tracker[0]

    if avail_camera_entity_id is None:
        _LOGGER.warning(
            "%s not available and no alternative available", camera_entity_id)
        for c in cameras.values():
            if c.get(CONF_DEVICE_TRACKER):
                _LOGGER.debug('TRACKER %s: %s', c.get(CONF_CAMERA), hass.get_tracker_state(
                    c[CONF_DEVICE_TRACKER]))
        return
    return avail_camera_entity_id
