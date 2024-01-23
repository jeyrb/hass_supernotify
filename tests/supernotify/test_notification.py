from homeassistant.core import HomeAssistant
import pytest
from pytest_httpserver import BlockingHTTPServer
from custom_components.supernotify import ATTR_MEDIA_SNAPSHOT_URL, CONF_DELIVERY, CONF_DELIVERY_SELECTION, CONF_MEDIA, CONF_SCENARIOS, DELIVERY_SELECTION_EXPLICIT, DELIVERY_SELECTION_IMPLICIT
from custom_components.supernotify.configuration import SupernotificationConfiguration
from custom_components.supernotify.methods.email import EmailDeliveryMethod
from custom_components.supernotify.methods.generic import GenericDeliveryMethod
from custom_components.supernotify.notification import Notification
from unittest.mock import Mock
from pytest_unordered import unordered
import os.path
import tempfile
import io

from homeassistant.const import (
    CONF_SERVICE, CONF_NAME, CONF_EMAIL
)
from homeassistant.core import HomeAssistant

from custom_components.supernotify import (
    CONF_METHOD,
    CONF_SELECTION,
    CONF_TARGET,
    METHOD_ALEXA,
    METHOD_CHIME,
    METHOD_EMAIL,
    METHOD_GENERIC,
    METHOD_PERSISTENT,
    METHOD_SMS,
    SELECTION_BY_SCENARIO,
)

async def test_simple_create(hass: HomeAssistant) -> None:
    context = Mock()
    context.scenarios = {}
    context.deliveries = {"plain_email": {}, "mobile": {}, "chime": {}}
    context.delivery_by_scenario = {"DEFAULT": ["plain_email", "mobile"]}
    uut = Notification(context, "testing 123")
    await uut.initialize()
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
    await uut.initialize()
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
    await uut.initialize()
    assert uut.selected_delivery_names == unordered(
        "plain_email", "mobile", "chime")


async def test_explicit_list_of_deliveries(hass: HomeAssistant) -> None:
    context = Mock()
    context.scenarios = {}
    context.delivery_by_scenario = {"DEFAULT": [
        "plain_email", "mobile"], "Alarm": ["chime"]}
    context.deliveries = {"plain_email": {}, "mobile": {}, "chime": {}}
    uut = Notification(context, "testing 123", service_data={
        CONF_DELIVERY: "mobile"
    })
    await uut.initialize()
    assert uut.selected_delivery_names == ["mobile"]

async def test_explicit_recipients_only_restricts_people_targets(hass: HomeAssistant) -> None:
    context = SupernotificationConfiguration()
    await context.initialize()
    delivery = {"chatty": {CONF_METHOD: METHOD_GENERIC,
                           CONF_SERVICE: "notify.slackity",
                           CONF_TARGET: ["chan1", "chan2"]},
                "mail": {CONF_METHOD: METHOD_EMAIL,
                         CONF_SERVICE: "notify.smtp"}}
    context.people = {"person.bob": {CONF_EMAIL: "bob@test.com"},
                      "person.jane": {CONF_EMAIL: "jane@test.com"}}
    uut = Notification(context, "testing 123")
    generic = GenericDeliveryMethod(hass, context, delivery)
    await generic.initialize()
    bundles = uut.build_targets(delivery["chatty"], generic)
    assert bundles == [(["chan1", "chan2"], None)]
    email = EmailDeliveryMethod(hass, context, delivery)
    await email.initialize()
    bundles = uut.build_targets(delivery["mail"], email)
    assert bundles == [(["bob@test.com", "jane@test.com"], None)]
    
async def test_build_targets_for_simple_case(hass: HomeAssistant) -> None:
    context = SupernotificationConfiguration()
    await context.initialize()
    method = GenericDeliveryMethod(hass, context, {})
    await method.initialize()
    uut = Notification(context, "testing 123")
    bundles = uut.build_targets({}, method)
    assert bundles == [([], None)]

async def test_dict_of_delivery_tuning_does_not_restrict_deliveries(hass: HomeAssistant) -> None:
    context = Mock()
    context.scenarios = {}
    context.delivery_by_scenario = {"DEFAULT": [
        "plain_email", "mobile"], "Alarm": ["chime"]}
    context.deliveries = {"plain_email": {}, "mobile": {}, "chime": {}}
    uut = Notification(context, "testing 123", service_data={
        CONF_DELIVERY: {"mobile": {}}
    })
    await uut.initialize()
    assert uut.selected_delivery_names == unordered(
        "plain_email", "mobile")


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
    await uut.initialize()
    original_image_path = os.path.join(
        "tests", "supernotify", "fixtures", "media", "example_image.png")
    original_image = io.FileIO(original_image_path, "rb").readall()
    httpserver_ipv4.expect_request(
        "/snapshot_image").respond_with_data(original_image, content_type="image/png")
    retrieved_image_path = await uut.grab_image()
    assert retrieved_image_path is not None
    retrieved_image = io.FileIO(retrieved_image_path, "rb").readall()
    assert retrieved_image == original_image
