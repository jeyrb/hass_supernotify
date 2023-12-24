"""The tests for the notify smtp platform."""
from pathlib import Path
import re
from unittest.mock import patch

import pytest

from homeassistant import config as hass_config
import homeassistant.components.notify as notify
from custom_components.supernotify import DOMAIN
from custom_components.supernotify import SuperNotificationService
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.setup import async_setup_component

from tests.common import get_fixture_path


async def test_load_notify(hass: HomeAssistant) -> None:
    """Verify we can reload the notify service."""

    assert await async_setup_component(
        hass,
        DOMAIN,
        {
           'alexa_targets':(), 
           'alexa_show_targets':(), 
           'sms_targets':(), 
           'apple_targets':(),
           'mobile_actions':()
        },
    )
    await hass.async_block_till_done()

    assert hass.services.has_service(notify.DOMAIN, DOMAIN)
