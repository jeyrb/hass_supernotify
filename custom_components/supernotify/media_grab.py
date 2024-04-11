import asyncio
import io
import logging
import os
import os.path
import time
from http import HTTPStatus

from aiohttp import ClientTimeout
from homeassistant.const import STATE_HOME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from PIL import Image

from custom_components.supernotify import (
    CONF_ALT_CAMERA,
    CONF_CAMERA,
    CONF_DEVICE_TRACKER,
    PTZ_METHOD_FRIGATE,
    PTZ_METHOD_ONVIF,
)

_LOGGER = logging.getLogger(__name__)


async def snapshot_from_url(hass, snapshot_url, notification_id, media_path, hass_base_url, timeout=15, jpeg_args=None):

    image_path = None
    hass_base_url = hass_base_url or ""
    try:
        media_dir = os.path.join(media_path, "snapshot")
        os.makedirs(media_dir, exist_ok=True)
        if snapshot_url.startswith("http"):
            image_url = snapshot_url
        else:
            image_url = f"{hass_base_url}{snapshot_url}"
        websession = async_get_clientsession(hass)
        r = await websession.get(image_url, timeout=ClientTimeout(total=timeout))
        if r.status != HTTPStatus.OK:
            _LOGGER.warning("SUPERNOTIFY Unable to retrieve %s: %s", image_url, r.status)
        else:
            if r.content_type == "image/jpeg":
                media_ext = "jpg"
            elif r.content_type == "image/png":
                media_ext = "png"
            elif r.content_type == "image/gif":
                media_ext = "gif"
            else:
                _LOGGER.info("SUPERNOTIFY Unexpected MIME type %s from snap of %s", r.content_type, image_url)
                media_ext = "img"

            # TODO configure image rewrite
            image_path = os.path.join(media_dir, f"{notification_id}.{media_ext}")
            image = Image.open(io.BytesIO(await r.content.read()))
            # rewrite to remove metadata, incl custom CCTV comments that confusie python MIMEImage
            clean_image = Image.new(image.mode, image.size)
            clean_image.putdata(image.getdata())
            if media_ext == "jpg" and jpeg_args:
                clean_image.save(image_path, **jpeg_args)
            else:
                clean_image.save(image_path)
            _LOGGER.debug("SUPERNOTIFY Fetched image from %s to %s", image_url, image_path)
            return image_path
    except Exception as e:
        _LOGGER.error("SUPERNOTIFY Image snap fail: %s", e)


async def move_camera_to_ptz_preset(hass, camera_entity_id, preset, method=PTZ_METHOD_ONVIF):
    try:
        _LOGGER.info("SUPERNOTIFY Executing PTZ by %s to %s for %s", method, preset, camera_entity_id)
        if method == PTZ_METHOD_FRIGATE:
            await hass.services.async_call(
                "frigate",
                "ptz",
                service_data={"action": "preset", "argument": preset},
                target={
                    "entity_id": camera_entity_id,
                },
            )
        elif method == PTZ_METHOD_ONVIF:
            await hass.services.async_call(
                "onvif",
                "ptz",
                service_data={"move_mode": "GotoPreset", "preset": preset},
                target={
                    "entity_id": camera_entity_id,
                },
            )
        else:
            _LOGGER.warning("SUPERNOTIFY Unknown PTZ method %s", method)
    except Exception as e:
        _LOGGER.warning("SUPERNOTIFY Unable to move %s to ptz preset %s: %s", camera_entity_id, preset, e)


async def snap_image(hass: HomeAssistant, entity_id: str, media_path: str, notification_id: str, jpeg_args: dict | None = None):
    """Use for any image, including MQTT Image"""
    image_path = None

    image_entity = hass.states.get(entity_id)
    if image_entity:
        image: Image.Image = Image.open(io.BytesIO(await image_entity.async_image()))
        media_dir = os.path.join(media_path, "image")
        os.makedirs(media_dir, exist_ok=True)
        media_ext = image.format.lower() if image.format else "img"
        timed = str(time.time()).replace(".", "_")
        image_path = os.path.join(media_dir, f"{notification_id}_{timed}.{media_ext}")
        image.save(image_path)
        if media_ext == "jpg" and jpeg_args:
            image.save(image_path, **jpeg_args)
        else:
            image.save(image_path)
    return image_path


async def snap_camera(
    hass: HomeAssistant, camera_entity_id: str, media_path: str, timeout: int = 20, jpeg_args: dict | None = None
):

    image_path = None
    if not camera_entity_id:
        _LOGGER.warning("SUPERNOTIFY Empty camera entity id for snap")
        return image_path

    try:
        media_dir = os.path.join(media_path, "camera")
        os.makedirs(media_dir, exist_ok=True)
        timed = str(time.time()).replace(".", "_")
        image_path = os.path.join(media_dir, f"{camera_entity_id}_{timed}.jpg")
        await hass.services.async_call(
            "camera", "snapshot", service_data={"entity_id": camera_entity_id, "filename": image_path}
        )

        # give async service time
        cutoff_time = time.time() + timeout
        while time.time() < cutoff_time and not os.path.exists(image_path):
            _LOGGER.info("Image file not available yet at %s, pausing", image_path)
            await asyncio.sleep(1)

    except Exception as e:
        _LOGGER.warning("Failed to snap avail camera %s to %s: %s", camera_entity_id, image_path, e)
        image_path = None

    return image_path


async def select_avail_camera(hass, cameras, camera_entity_id):
    avail_camera_entity_id = None

    try:
        preferred_cam = cameras.get(camera_entity_id)

        if not preferred_cam or not preferred_cam.get(CONF_DEVICE_TRACKER):
            # assume unconfigured camera, or configured without tracker, available
            avail_camera_entity_id = camera_entity_id
        elif hass.states.get(preferred_cam[CONF_DEVICE_TRACKER]).state == STATE_HOME:
            avail_camera_entity_id = camera_entity_id
        else:
            alt_cams_with_tracker = [
                cameras[c]
                for c in preferred_cam.get(CONF_ALT_CAMERA, [])
                if c in cameras and cameras[c].get(CONF_DEVICE_TRACKER)
            ]
            for alt_cam in alt_cams_with_tracker:
                alt_cam_state = hass.states.get(alt_cam.get(CONF_DEVICE_TRACKER))
                if alt_cam_state.state == STATE_HOME:
                    avail_camera_entity_id = alt_cam[CONF_CAMERA]
                    _LOGGER.info(
                        "SUPERNOTIFY Selecting available camera %s rather than %s", avail_camera_entity_id, camera_entity_id
                    )
                    break
            if avail_camera_entity_id is None:
                alt_cam_ids_without_tracker = [
                    c
                    for c in preferred_cam.get(CONF_ALT_CAMERA, [])
                    if c not in cameras or not cameras[c].get(CONF_DEVICE_TRACKER)
                ]
                if len(alt_cam_ids_without_tracker) > 0:
                    _LOGGER.info(
                        "SUPERNOTIFY Selecting untracked camera %s rather than %s", avail_camera_entity_id, camera_entity_id
                    )
                    avail_camera_entity_id = alt_cam_ids_without_tracker[0]

        if avail_camera_entity_id is None:
            _LOGGER.warning("%s not available and no alternative available", camera_entity_id)
            for c in cameras.values():
                if c.get(CONF_DEVICE_TRACKER):
                    _LOGGER.debug(
                        "SUPERNOTIFY Tracker %s: %s", c.get(CONF_DEVICE_TRACKER), hass.states.get(c[CONF_DEVICE_TRACKER])
                    )

    except Exception as e:
        _LOGGER.warning("SUPERNOTIFY Unable to select available camera: %s", e)

    return avail_camera_entity_id
