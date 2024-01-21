from homeassistant.core import HomeAssistant
from custom_components.supernotify import CONF_DELIVERY, CONF_DELIVERY_SELECTION, CONF_SCENARIOS, DELIVERY_SELECTION_EXPLICIT, DELIVERY_SELECTION_IMPLICIT
from custom_components.supernotify.notification import Notification
from unittest.mock import Mock
from pytest_unordered import unordered


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
    assert uut.message == 'testing 123'
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
