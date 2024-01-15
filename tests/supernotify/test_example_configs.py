
import os
import os.path

import homeassistant.components.notify as notify
import pytest
import yaml
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.supernotify import CONF_NOTIFY

EXAMPLES_ROOT = "examples"

examples = os.listdir(EXAMPLES_ROOT)


@pytest.mark.parametrize("config_name", examples)
async def test_examples(hass: HomeAssistant, config_name) -> None:

    with open(os.path.join(EXAMPLES_ROOT, config_name), "r") as f:
        config = yaml.safe_load(f)
    service_name = config[CONF_NOTIFY][0][CONF_NAME]
    assert await async_setup_component(
        hass,
        notify.DOMAIN,
        config
    )
    await hass.async_block_till_done()

    assert hass.services.has_service(notify.DOMAIN, service_name)

    hass.services.async_remove(notify.DOMAIN, service_name)
