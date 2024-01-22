from homeassistant.core import HomeAssistant
import pytest
from pytest_httpserver import BlockingHTTPServer
from custom_components.supernotify import ATTR_MEDIA_SNAPSHOT_URL, CONF_DELIVERY, CONF_DELIVERY_SELECTION, CONF_MEDIA, CONF_SCENARIOS, DELIVERY_SELECTION_EXPLICIT, DELIVERY_SELECTION_IMPLICIT
from custom_components.supernotify.notification import Notification
from unittest.mock import Mock
from pytest_unordered import unordered
import os.path
import tempfile
import io


async def test_simple_create(hass: HomeAssistant) -> None:
    context = Mock()
    context.scenarios = {}
    context.deliveries = {"plain_email": {}, "mobile": {}, "chime": {}}
    context.delivery_by_scenario = {"DEFAULT": ["plain_email", "mobile"]}
    uut = Notification(context, "testing 123")
    await uut.intialize()
    assert uut.enabled_scenarios == []
    assert uut.requested_scenarios == []
    assert uut.target == []
    assert uut.message("plain_email") == 'testing 123'
    assert uut.priority == 'medium'
    assert uut.delivery_overrides == {}
    assert uut.delivery_selection == DELIVERY_SELECTION_IMPLICIT
    assert uut.recipients_override is None
    assert uut.selected_delivery_names == unordered(['plain_email', 'mobile'])


async def test_explicit_delivery(hass: HomeAssistant) -> None:
    context = Mock()
    context.scenarios = {}
    context.delivery_by_scenario = {"DEFAULT": ["plain_email", "mobile"]}
    context.deliveries = {"plain_email": {}, "mobile": {}, "chime": {}}
    uut = Notification(context, "testing 123", service_data={
        CONF_DELIVERY_SELECTION: DELIVERY_SELECTION_EXPLICIT,
        CONF_DELIVERY: "mobile"}
    )
    await uut.intialize()
    assert uut.delivery_selection == DELIVERY_SELECTION_EXPLICIT
    assert uut.selected_delivery_names == ["mobile"]


async def test_scenario_delivery(hass: HomeAssistant) -> None:
    context = Mock()
    context.scenarios = {}
    context.delivery_by_scenario = {"DEFAULT": [
        "plain_email", "mobile"], "Alarm": ["chime"]}
    context.deliveries = {"plain_email": {}, "mobile": {}, "chime": {}}
    uut = Notification(context, "testing 123", service_data={
        CONF_SCENARIOS: "Alarm"
    })
    await uut.intialize()
    assert uut.selected_delivery_names == ["chime"]


@pytest.mark.enable_socket
async def test_snapshot_url(hass: HomeAssistant, httpserver_ipv4: BlockingHTTPServer) -> None:
    context = Mock()
    context.hass = hass
    context.scenarios = {}
    context.deliveries = {}
    context.delivery_by_scenario = {}
    context.media_path = tempfile.mkdtemp()
    uut = Notification(context, "testing 123", service_data={
        CONF_MEDIA: {
            ATTR_MEDIA_SNAPSHOT_URL: httpserver_ipv4.url_for("/snapshot_image")}
    })
    await uut.intialize()
    original_image_path = os.path.join(
        "tests", "supernotify", "fixtures", "media", "example_image.png")
    original_image = io.FileIO(original_image_path, "rb").readall()
    httpserver_ipv4.expect_request(
        "/snapshot_image").respond_with_data(original_image, content_type="image/png")
    retrieved_image_path = await uut.grab_image()
    assert retrieved_image_path is not None
    retrieved_image = io.FileIO(retrieved_image_path, "rb").readall()
    assert retrieved_image == original_image
