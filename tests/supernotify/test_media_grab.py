from unittest.mock import Mock
from homeassistant.core import HomeAssistant
import pytest
from pytest_httpserver import BlockingHTTPServer
import os.path
import tempfile
import io


from custom_components.supernotify.media_grab import select_avail_camera, snapshot_from_url


@pytest.mark.enable_socket
async def test_snapshot_url_with_abs_path(hass: HomeAssistant, httpserver_ipv4: BlockingHTTPServer) -> None:
    media_path = tempfile.mkdtemp()

    original_image_path = os.path.join(
        "tests", "supernotify", "fixtures", "media", "example_image.png")
    original_image = io.FileIO(original_image_path, "rb").readall()
    snapshot_url = httpserver_ipv4.url_for("/snapshot_image")
    httpserver_ipv4.expect_request(
        "/snapshot_image").respond_with_data(original_image, content_type="image/png")
    retrieved_image_path = await snapshot_from_url(hass, snapshot_url, "notify-uuid-1", media_path, None)

    assert retrieved_image_path is not None
    retrieved_image = io.FileIO(retrieved_image_path, "rb").readall()
    assert retrieved_image == original_image


@pytest.mark.enable_socket
async def test_snapshot_url_with_broken_url(hass: HomeAssistant, httpserver_ipv4: BlockingHTTPServer) -> None:
    media_path = tempfile.mkdtemp()
    snapshot_url = "http://no-such-domain.local:9494/snapshot_image_hass"
    retrieved_image_path = await snapshot_from_url(hass, snapshot_url, "notify-uuid-1", media_path, None)
    assert retrieved_image_path is None


async def test_snap_alt_camera(hass: HomeAssistant) -> None:
    pass


async def test_select_camera_not_in_config() -> None:
    hass = Mock()
    assert "camera.unconfigured" == await select_avail_camera(hass, {}, "camera.unconfigured")


async def test_select_untracked_primary_camera() -> None:
    hass = Mock()
    assert "camera.untracked" == await select_avail_camera(hass, {"camera.untracked": {"alias": "Test Untracked"}}, "camera.untracked")


async def test_select_tracked_primary_camera() -> None:
    hass = Mock()
    hass.states.get.return_value = "home"
    assert "camera.tracked" == await select_avail_camera(hass, {"camera.tracked": {"device_tracker": "device_tracker.cam1"}}, "camera.tracked")


async def test_no_select_unavail_primary_camera() -> None:
    hass = Mock()
    hass.states.get.return_value = "not_home"
    assert await select_avail_camera(hass, {"camera.tracked": {"camera":"camera.tracked",
                                                               "device_tracker": "device_tracker.cam1"}}, 
                                     "camera.tracked") is None


async def test_select_avail_alt_camera() -> None:
    hass = Mock()
    hass.states.get.side_effect = lambda v: {
        "device_tracker.altcam2": "home"}.get(v, "not_home")
    assert await select_avail_camera(hass, {"camera.tracked":
                                            {"camera":"camera.tracked","device_tracker": "device_tracker.cam1",
                                             "alt_camera": ["camera.alt1", "camera.alt2", "camera.alt3"]},
                                            "camera.alt1": {"camera":"camera.alt1","device_tracker": "device_tracker.altcam1"},
                                            "camera.alt2": {"camera":"camera.alt2","device_tracker": "device_tracker.altcam2"},
                                            },
                                     "camera.tracked") == "camera.alt2"


async def test_select_untracked_alt_camera() -> None:
    hass = Mock()
    hass.states.get.side_effect = lambda v: {
        "device_tracker.alt2": "home"}.get(v, "not_home")
    assert await select_avail_camera(hass, {"camera.tracked":
                                            {"camera":"camera.tracked","device_tracker": "device_tracker.cam1",
                                             "alt_camera": ["camera.alt1", "camera.alt2", "camera.alt3"]},
                                            "camera.alt1": {"camera":"camera.alt1","device_tracker": "device_tracker.altcam1"},
                                            "camera.alt2": {"camera":"camera.alt2","device_tracker": "device_tracker.altcam2"},
                                            },
                                     "camera.tracked") == "camera.alt3"
