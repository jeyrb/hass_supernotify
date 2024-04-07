from unittest.mock import patch, Mock, AsyncMock
from homeassistant.core import HomeAssistant

import pytest
from pytest_httpserver import HTTPServer

from custom_components.supernotify.configuration import SupernotificationConfiguration


@pytest.fixture
def mock_hass() -> HomeAssistant:
    hass = Mock()
    hass.states = Mock()
    hass.services.async_call = AsyncMock()
    hass.data = {}
    hass.data["device_registry"] = Mock()
    hass.data["entity_registry"] = Mock()
    return hass


@pytest.fixture
async def superconfig() -> SupernotificationConfiguration:
    context = SupernotificationConfiguration()
    await context.initialize()
    return context


@pytest.fixture
@pytest.mark.enable_socket
def local_server(httpserver_ssl_context: None, socket_enabled):
    """pytest-socket will fail at fixture creation time, before test that uses it"""
    server = HTTPServer(host="127.0.0.1", port=0, ssl_context=httpserver_ssl_context)
    server.start()
    yield server
    server.clear()
    if server.is_running():
        server.stop()


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations in all tests."""
    yield


# This fixture is used to prevent HomeAssistant from attempting to create and dismiss persistent
# notifications. These calls would fail without this fixture since the persistent_notification
# integration is never loaded during a test.


@pytest.fixture(name="skip_notifications", autouse=True)
def skip_notifications_fixture():
    """Skip notification calls."""
    with patch("homeassistant.components.persistent_notification.async_create"), patch(
        "homeassistant.components.persistent_notification.async_dismiss"
    ):
        yield
