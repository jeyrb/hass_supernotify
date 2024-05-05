from collections.abc import Generator
from ssl import SSLContext
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import homeassistant.components.notify as notify
import pytest
from homeassistant.components.notify import BaseNotificationService
from homeassistant.core import HomeAssistant, callback
from pytest_httpserver import HTTPServer

from custom_components.supernotify.configuration import SupernotificationConfiguration


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
    hass = Mock()
    hass.states = Mock()
    hass.config.internal_url = "http://127.0.0.1:28123"
    hass.config.external_url = "https://my.home"
    hass.services.async_call = AsyncMock()
    hass.data = {}
    hass.data["device_registry"] = Mock()
    hass.data["entity_registry"] = Mock()
    hass.config_entries = Mock()
    hass.config_entries._entries = {}
    hass.config_entries._domain_index = {}

    return hass


@pytest.fixture()
def mock_notify(hass: HomeAssistant) -> MockService:
    mock_service: MockService = MockService()
    hass.services.async_register(notify.DOMAIN, "mock", mock_service, supports_response=False)
    return mock_service


@pytest.fixture()
async def superconfig() -> SupernotificationConfiguration:
    context = SupernotificationConfiguration()
    await context.initialize()
    return context


@pytest.fixture()
@pytest.mark.enable_socket()
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
