import io
import os.path
import tempfile
from unittest.mock import Mock

import pytest
from homeassistant.const import STATE_HOME, STATE_NOT_HOME
from homeassistant.core import HomeAssistant
from PIL import Image, ImageChops
from pytest_httpserver import BlockingHTTPServer
from custom_components.supernotify import PTZ_METHOD_FRIGATE

from custom_components.supernotify.media_grab import (
    move_camera_to_ptz_preset,
    select_avail_camera,
    snap_camera,
    snap_image,
    snapshot_from_url,
)
from tests.supernotify.doubles_lib import MockImageEntity

JPEG_PATH = os.path.join("tests", "supernotify", "fixtures", "media", "example_image.jpg")
PNG_PATH = os.path.join("tests", "supernotify", "fixtures", "media", "example_image.png")


@pytest.mark.enable_socket
async def test_snapshot_url_with_abs_path(hass: HomeAssistant, local_server: BlockingHTTPServer) -> None:
    media_path = tempfile.mkdtemp()

    original_image_path = PNG_PATH
    original_binary = io.FileIO(original_image_path, "rb").readall()
    snapshot_url = local_server.url_for("/snapshot_image")
    local_server.expect_request("/snapshot_image").respond_with_data(original_binary, content_type="image/png")
    retrieved_image_path = await snapshot_from_url(hass, snapshot_url, "notify-uuid-1", media_path, None)

    assert retrieved_image_path is not None
    retrieved_image = Image.open(retrieved_image_path)
    original_image = Image.open(original_image_path)
    assert retrieved_image.size == original_image.size
    diff = ImageChops.difference(retrieved_image, original_image)
    assert diff.getbbox() is None


@pytest.mark.enable_socket
async def test_snapshot_url_with_jpeg_flags(hass: HomeAssistant, local_server: BlockingHTTPServer) -> None:
    media_path = tempfile.mkdtemp()

    original_image_path = JPEG_PATH
    original_binary = io.FileIO(original_image_path, "rb").readall()
    snapshot_url = local_server.url_for("/snapshot_image")
    local_server.expect_request("/snapshot_image").respond_with_data(original_binary, content_type="image/jpeg")
    retrieved_image_path = await snapshot_from_url(
        hass,
        snapshot_url,
        "notify-uuid-1",
        media_path,
        None,
        jpeg_args={"quality": 30, "progressive": True, "optimize": True, "comment": "changed by test"},
    )

    retrieved_image = Image.open(retrieved_image_path)
    original_image = Image.open(original_image_path)
    assert retrieved_image.size == original_image.size
    assert retrieved_image.info.get("comment") == b"changed by test"
    assert retrieved_image.info.get("progressive") == 1


async def test_snapshot_url_with_broken_url(hass: HomeAssistant) -> None:
    media_path = tempfile.mkdtemp()
    snapshot_url = "http://no-such-domain.local:9494/snapshot_image_hass"
    retrieved_image_path = await snapshot_from_url(hass, snapshot_url, "notify-uuid-1", media_path, None)
    assert retrieved_image_path is None


async def test_snap_camera(mock_hass) -> None:
    with tempfile.TemporaryDirectory() as tmp_path:
        image_path = await snap_camera(mock_hass, "camera.xunit", media_path=tmp_path, timeout=1)
    assert image_path is not None
    mock_hass.services.async_call.assert_awaited_once_with(
        "camera", "snapshot", service_data={"entity_id": "camera.xunit", "filename": image_path}
    )


async def test_snap_image(mock_hass) -> None:
    image_path = PNG_PATH
    image_entity = MockImageEntity(image_path)
    mock_hass.states.get.return_value = image_entity
    with tempfile.TemporaryDirectory() as tmp_path:
        snap_image_path = await snap_image(mock_hass, "image.testing", media_path=tmp_path, notification_id="notify_001")
        assert snap_image_path is not None
        retrieved_image = Image.open(snap_image_path)
        
    original_image = Image.open(image_path)
    assert retrieved_image.size == original_image.size
    diff = ImageChops.difference(retrieved_image, original_image)
    assert diff.getbbox() is None


async def test_move_camera_onvif(mock_hass) -> None:
    await move_camera_to_ptz_preset(mock_hass, "camera.xunit", preset="Upstairs")
    mock_hass.services.async_call.assert_awaited_once_with(
        "onvif", "ptz", service_data={"move_mode": "GotoPreset", "preset": "Upstairs"}, target={"entity_id": "camera.xunit"}
    )


async def test_move_camera_frigate(mock_hass) -> None:
    await move_camera_to_ptz_preset(mock_hass, "camera.xunit", preset="Upstairs", method=PTZ_METHOD_FRIGATE)
    mock_hass.services.async_call.assert_awaited_once_with(
        "frigate", "ptz", service_data={"action": "preset", "argument": "Upstairs"}, target={"entity_id": "camera.xunit"}
    )


def set_states(hass, at_home=(), not_at_home=()):
    home_state = Mock(name="At Home")
    home_state.state = STATE_HOME
    not_home_state = Mock(name="Not at Home")
    not_home_state.state = STATE_NOT_HOME
    hass.states.get = Mock()
    hass.states.get.side_effect = lambda v: home_state if v in at_home else not_home_state if v in not_at_home else None


async def test_select_camera_not_in_config(mock_hass) -> None:
    assert "camera.unconfigured" == await select_avail_camera(mock_hass, {}, "camera.unconfigured")


async def test_select_untracked_primary_camera(mock_hass) -> None:
    assert "camera.untracked" == await select_avail_camera(
        mock_hass, {"camera.untracked": {"alias": "Test Untracked"}}, "camera.untracked"
    )


async def test_select_tracked_primary_camera(mock_hass) -> None:
    set_states(mock_hass, ["device_tracker.cam1"])
    assert "camera.tracked" == await select_avail_camera(
        mock_hass, {"camera.tracked": {"device_tracker": "device_tracker.cam1"}}, "camera.tracked"
    )


async def test_no_select_unavail_primary_camera(mock_hass) -> None:
    set_states(mock_hass, [], ["device_tracker.cam1"])
    assert (
        await select_avail_camera(
            mock_hass,
            {"camera.tracked": {"camera": "camera.tracked", "device_tracker": "device_tracker.cam1"}},
            "camera.tracked",
        )
        is None
    )


async def test_select_avail_alt_camera(mock_hass) -> None:
    set_states(mock_hass, ["device_tracker.altcam2"], ["device_tracker.cam1", "device_tracker.altcam1"])
    assert (
        await select_avail_camera(
            mock_hass,
            {
                "camera.tracked": {
                    "camera": "camera.tracked",
                    "device_tracker": "device_tracker.cam1",
                    "alt_camera": ["camera.alt1", "camera.alt2", "camera.alt3"],
                },
                "camera.alt1": {"camera": "camera.alt1", "device_tracker": "device_tracker.altcam1"},
                "camera.alt2": {"camera": "camera.alt2", "device_tracker": "device_tracker.altcam2"},
            },
            "camera.tracked",
        )
        == "camera.alt2"
    )


async def test_select_untracked_alt_camera(mock_hass) -> None:
    set_states(mock_hass, [], ["device_tracker.cam1", "device_tracker.altcam1", "device_tracker.altcam2"])
    assert (
        await select_avail_camera(
            mock_hass,
            {
                "camera.tracked": {
                    "camera": "camera.tracked",
                    "device_tracker": "device_tracker.cam1",
                    "alt_camera": ["camera.alt1", "camera.alt2", "camera.alt3"],
                },
                "camera.alt1": {"camera": "camera.alt1", "device_tracker": "device_tracker.altcam1"},
                "camera.alt2": {"camera": "camera.alt2", "device_tracker": "device_tracker.altcam2"},
            },
            "camera.tracked",
        )
        == "camera.alt3"
    )
