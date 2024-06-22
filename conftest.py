import logging
from collections.abc import Generator
from pathlib import Path
from ssl import SSLContext
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.components.notify.const import DOMAIN
from homeassistant.components.notify.legacy import BaseNotificationService
from homeassistant.config_entries import ConfigEntries
from homeassistant.const import ATTR_STATE
from homeassistant.core import EventBus, HomeAssistant, ServiceRegistry, StateMachine, SupportsResponse, callback
from homeassistant.helpers.device_registry import DeviceRegistry
from homeassistant.helpers.entity_registry import EntityRegistry
from pytest_httpserver import HTTPServer

from custom_components.supernotify import CONF_PERSON
from custom_components.supernotify.configuration import SupernotificationConfiguration

loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
for logger in loggers:
    logger.setLevel(logging.INFO)


class MockableHomeAssistant(HomeAssistant):
    config: ConfigEntries = Mock(spec=ConfigEntries)
    services: ServiceRegistry = AsyncMock(spec=ServiceRegistry)
    bus: EventBus = Mock(spec=EventBus)


class MockService(BaseNotificationService):
    """A test class for notification services."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls = []

    @callback
    async def async_send_message(self, message="", title=None, target=None, **kwargs):
        self.calls.append([message, title, target, kwargs])


@pytest.fixture()
def mock_hass() -> HomeAssistant:
    hass = Mock(spec=MockableHomeAssistant)
    hass.states = Mock(StateMachine)
    hass.services = Mock(ServiceRegistry)
    hass.config.internal_url = "http://127.0.0.1:28123"
    hass.config.external_url = "https://my.home"
    hass.data = {}
    hass.data["device_registry"] = Mock(spec=DeviceRegistry)
    hass.data["entity_registry"] = Mock(spec=EntityRegistry)
    hass.config_entries._entries = {}
    hass.config_entries._domain_index = {}
    return hass


@pytest.fixture()
def mock_context(mock_hass: HomeAssistant) -> SupernotificationConfiguration:
    context = Mock(spec=SupernotificationConfiguration)
    context.hass = mock_hass
    context.scenarios = {}
    context.deliveries = {}
    context.cameras = {}
    context.snoozes = {}
    context.delivery_by_scenario = {}
    context.method_defaults = {}
    context.hass_internal_url = "http://hass-dev"
    context.media_path = Path("/nosuchpath")
    context.template_path = Path("/templates_here")
    context.people = {
        "person.new_home_owner": {CONF_PERSON: "person.new_home_owner"},
        "person.bidey_in": {CONF_PERSON: "person.bidey_in"},
    }
    context.people_state.return_value = [
        {CONF_PERSON: "person.new_home_owner", ATTR_STATE: "not_home"},
        {CONF_PERSON: "person.bidey_in", ATTR_STATE: "home"},
    ]

    return context


@pytest.fixture()
def mock_notify(hass: HomeAssistant) -> MockService:
    mock_service: MockService = MockService()
    hass.services.async_register(DOMAIN, "mock", mock_service, supports_response=SupportsResponse.NONE)  # type: ignore
    return mock_service


@pytest.fixture()
async def superconfig() -> SupernotificationConfiguration:
    context = SupernotificationConfiguration()
    await context.initialize()
    return context


@pytest.fixture()
def local_server(httpserver_ssl_context: SSLContext | None, socket_enabled: Any) -> Generator[HTTPServer, None, None]:
    """pytest-socket will fail at fixture creation time, before test that uses it"""
    server = HTTPServer(host="127.0.0.1", port=0, ssl_context=httpserver_ssl_context)
    server.start()
    yield server
    server.clear()
    if server.is_running():
        server.stop()


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: Any) -> None:
    """Enable custom integrations in all tests."""
    return


# This fixture is used to prevent HomeAssistant from attempting to create and dismiss persistent
# notifications. These calls would fail without this fixture since the persistent_notification
# integration is never loaded during a test.


@pytest.fixture(name="skip_notifications", autouse=True)
def skip_notifications_fixture():
    """Skip notification calls."""
    with (
        patch("homeassistant.components.persistent_notification.async_create"),
        patch("homeassistant.components.persistent_notification.async_dismiss"),
    ):
        yield
