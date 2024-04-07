from homeassistant.core import HomeAssistant
from custom_components.supernotify import (
    ATTR_DATA,
    ATTR_MEDIA,
    ATTR_MEDIA_CAMERA_DELAY,
    ATTR_MEDIA_CAMERA_ENTITY_ID,
    ATTR_MEDIA_SNAPSHOT_URL,
    CONF_DELIVERY,
    CONF_DELIVERY_SELECTION,
    CONF_MEDIA,
    CONF_PERSON,
    CONF_RECIPIENTS,
    CONF_SCENARIOS,
    DELIVERY_SELECTION_EXPLICIT,
    DELIVERY_SELECTION_IMPLICIT,
)
from custom_components.supernotify.configuration import SupernotificationConfiguration
from custom_components.supernotify.methods.email import EmailDeliveryMethod
from custom_components.supernotify.methods.generic import GenericDeliveryMethod
from custom_components.supernotify.notification import Notification
from custom_components.supernotify.envelope import Envelope
from custom_components.supernotify.scenario import Scenario
from unittest.mock import Mock, patch
from pytest_unordered import unordered


from homeassistant.const import CONF_SERVICE, CONF_EMAIL, CONF_ENTITIES

from custom_components.supernotify import (
    CONF_METHOD,
    CONF_TARGET,
    METHOD_EMAIL,
    METHOD_GENERIC,
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
    assert uut.message("plain_email") == "testing 123"
    assert uut.priority == "medium"
    assert uut.delivery_overrides == {}
    assert uut.delivery_selection == DELIVERY_SELECTION_IMPLICIT
    assert uut.recipients_override is None
    assert uut.selected_delivery_names == unordered(["plain_email", "mobile"])


async def test_explicit_delivery(hass: HomeAssistant) -> None:
    context = Mock()
    context.scenarios = {}
    context.delivery_by_scenario = {"DEFAULT": ["plain_email", "mobile"]}
    context.deliveries = {"plain_email": {}, "mobile": {}, "chime": {}}
    uut = Notification(
        context, "testing 123", service_data={CONF_DELIVERY_SELECTION: DELIVERY_SELECTION_EXPLICIT, CONF_DELIVERY: "mobile"}
    )
    await uut.initialize()
    assert uut.delivery_selection == DELIVERY_SELECTION_EXPLICIT
    assert uut.selected_delivery_names == ["mobile"]


async def test_scenario_delivery(hass: HomeAssistant) -> None:
    context = Mock()
    context.scenarios = {}
    context.delivery_by_scenario = {"DEFAULT": ["plain_email", "mobile"], "Alarm": ["chime"]}
    context.deliveries = {"plain_email": {}, "mobile": {}, "chime": {}}
    uut = Notification(context, "testing 123", service_data={CONF_SCENARIOS: "Alarm"})
    await uut.initialize()
    assert uut.selected_delivery_names == unordered("plain_email", "mobile", "chime")


async def test_explicit_list_of_deliveries(hass: HomeAssistant) -> None:
    context = Mock()
    context.scenarios = {}
    context.delivery_by_scenario = {"DEFAULT": ["plain_email", "mobile"], "Alarm": ["chime"]}
    context.deliveries = {"plain_email": {}, "mobile": {}, "chime": {}}
    uut = Notification(context, "testing 123", service_data={CONF_DELIVERY: "mobile"})
    await uut.initialize()
    assert uut.selected_delivery_names == ["mobile"]


async def test_generate_recipients_from_entities(mock_hass, superconfig) -> None:

    delivery = {
        "chatty": {
            CONF_METHOD: METHOD_GENERIC,
            CONF_SERVICE: "custom.tweak",
            CONF_ENTITIES: ["custom.light_1", "custom.switch_2"],
        }
    }
    superconfig.deliveries = delivery
    uut = Notification(superconfig, "testing 123")
    generic = GenericDeliveryMethod(mock_hass, superconfig, delivery)
    await generic.initialize()
    recipients = uut.generate_recipients("chatty", generic)
    assert recipients == [{"target": "custom.light_1"}, {"target": "custom.switch_2"}]

async def test_generate_recipients_from_recipients(mock_hass, superconfig) -> None:

    delivery = {
        "chatty": {
            CONF_METHOD: METHOD_GENERIC,
            CONF_SERVICE: "custom.tweak",
            CONF_RECIPIENTS: ["custom.light_1", "custom.switch_2"],
        }
    }
    superconfig.deliveries = delivery
    uut = Notification(superconfig, "testing 123")
    generic = GenericDeliveryMethod(mock_hass, superconfig, delivery)
    await generic.initialize()
    recipients = uut.generate_recipients("chatty", generic)
    assert recipients == ["custom.light_1","custom.switch_2"]

async def test_explicit_recipients_only_restricts_people_targets(hass: HomeAssistant, superconfig) -> None:

    delivery = {
        "chatty": {CONF_METHOD: METHOD_GENERIC, CONF_SERVICE: "notify.slackity", CONF_TARGET: ["chan1", "chan2"]},
        "mail": {CONF_METHOD: METHOD_EMAIL, CONF_SERVICE: "notify.smtp"},
    }
    superconfig.people = {"person.bob": {CONF_EMAIL: "bob@test.com"}, "person.jane": {CONF_EMAIL: "jane@test.com"}}
    superconfig.deliveries = delivery
    uut = Notification(superconfig, "testing 123")
    generic = GenericDeliveryMethod(hass, superconfig, delivery)
    await generic.initialize()
    recipients = uut.generate_recipients("chatty", generic)
    assert recipients == [{"target": "chan1"}, {"target": "chan2"}]
    bundles = uut.generate_envelopes("chatty", generic, recipients)
    assert bundles == [Envelope("chatty", uut, targets=["chan1", "chan2"])]
    email = EmailDeliveryMethod(hass, superconfig, delivery)
    await email.initialize()
    recipients = uut.generate_recipients("mail", email)
    assert recipients == [{"email": "bob@test.com"}, {"email": "jane@test.com"}]
    bundles = uut.generate_envelopes("mail", email, recipients)
    assert bundles == [Envelope("mail", uut, targets=["bob@test.com", "jane@test.com"])]


async def test_filter_recipients(mock_hass) -> None:
    hass_states = {"person.new_home_owner": Mock(state="not_home"), "person.bidey_in": Mock(state="home")}
    mock_hass.states.get = hass_states.get
    context = SupernotificationConfiguration(
        mock_hass, recipients=[{CONF_PERSON: "person.new_home_owner"}, {CONF_PERSON: "person.bidey_in"}]
    )
    await context.initialize()
    uut = Notification(context, "testing 123")

    assert len(uut.filter_people_by_occupancy("all_in")) == 0
    assert len(uut.filter_people_by_occupancy("all_out")) == 0
    assert len(uut.filter_people_by_occupancy("any_in")) == 2
    assert len(uut.filter_people_by_occupancy("any_out")) == 2
    assert len(uut.filter_people_by_occupancy("only_in")) == 1
    assert len(uut.filter_people_by_occupancy("only_out")) == 1

    assert {r["person"] for r in uut.filter_people_by_occupancy("only_out")} == {"person.new_home_owner"}
    assert {r["person"] for r in uut.filter_people_by_occupancy("only_in")} == {"person.bidey_in"}


async def test_build_targets_for_simple_case(hass: HomeAssistant, superconfig) -> None:

    method = GenericDeliveryMethod(hass, superconfig, {})
    await method.initialize()
    uut = Notification(superconfig, "testing 123")
    recipients = uut.generate_recipients("", method)
    bundles = uut.generate_envelopes("", method, recipients)
    assert bundles == [Envelope("", uut)]


async def test_dict_of_delivery_tuning_does_not_restrict_deliveries(hass: HomeAssistant) -> None:
    context = Mock()
    context.scenarios = {}
    context.delivery_by_scenario = {"DEFAULT": ["plain_email", "mobile"], "Alarm": ["chime"]}
    context.deliveries = {"plain_email": {}, "mobile": {}, "chime": {}}
    uut = Notification(context, "testing 123", service_data={CONF_DELIVERY: {"mobile": {}}})
    await uut.initialize()
    assert uut.selected_delivery_names == unordered("plain_email", "mobile")


async def test_snapshot_url(hass: HomeAssistant) -> None:
    context = Mock()
    context.hass = hass
    context.scenarios = {}
    context.deliveries = {}
    context.delivery_by_scenario = {}
    context.hass_internal_url = "http://hass-dev"
    context.media_path = "/nosuchpath"
    uut = Notification(context, "testing 123", service_data={CONF_MEDIA: {ATTR_MEDIA_SNAPSHOT_URL: "/my_local_image"}})
    await uut.initialize()
    original_image_path = "/tmp/image_a.jpg"
    with patch(
        "custom_components.supernotify.notification.snapshot_from_url", return_value=original_image_path
    ) as mock_snapshot:
        retrieved_image_path = await uut.grab_image("example")
        assert retrieved_image_path == original_image_path
        assert mock_snapshot.called
        mock_snapshot.reset_mock()
        retrieved_image_path = await uut.grab_image("example")
        assert retrieved_image_path == original_image_path
        # notification caches image for multiple deliveries
        assert mock_snapshot.assert_not_called

async def test_camera_entity(hass: HomeAssistant) -> None:
    context = Mock()
    context.hass = hass
    context.scenarios = {}
    context.deliveries = {}
    context.cameras = {}
    context.delivery_by_scenario = {}
    context.hass_internal_url = "http://hass-dev"
    context.media_path = "/nosuchpath"
    uut = Notification(context, "testing 123", service_data={CONF_MEDIA: {ATTR_MEDIA_CAMERA_ENTITY_ID: "camera.lobby"}})
    await uut.initialize()
    original_image_path = "/tmp/image_a.jpg"
    with patch(
        "custom_components.supernotify.notification.snap_camera", return_value=original_image_path
    ) as mock_snap_cam:
        retrieved_image_path = await uut.grab_image("example")
        assert retrieved_image_path == original_image_path
        assert mock_snap_cam.called
        mock_snap_cam.reset_mock()
        retrieved_image_path = await uut.grab_image("example")
        assert retrieved_image_path == original_image_path
        # notification caches image for multiple deliveries
        assert mock_snap_cam.assert_not_called



async def test_merge(mock_hass):
    context = Mock()
    context.scenarios = {
        "Alarm": Scenario("Alarm", {"media": {"jpeg_args": {"quality": 30}, "snapshot_url": "/bar/789"}}, mock_hass)
    }
    context.delivery_by_scenario = {"DEFAULT": ["plain_email", "mobile"], "Alarm": ["chime"]}
    context.deliveries = {"plain_email": {}, "mobile": {}, "chime": {}}
    uut = Notification(
        context,
        "testing 123",
        service_data={CONF_SCENARIOS: "Alarm", ATTR_MEDIA: {ATTR_MEDIA_CAMERA_DELAY: 11, ATTR_MEDIA_SNAPSHOT_URL: "/foo/123"}},
    )
    await uut.initialize()
    assert uut.merge(ATTR_MEDIA, "plain_email") == {
        "jpeg_args": {"quality": 30},
        "camera_delay": 11,
        "snapshot_url": "/foo/123",
    }
    assert uut.merge(ATTR_DATA, "plain_email") == {}
