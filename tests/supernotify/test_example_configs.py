
import os
import os.path

import homeassistant.components.notify as notify
import pytest
import yaml
from homeassistant.const import CONF_NAME, CONF_PLATFORM, CONF_ENABLED
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_unordered import unordered

from custom_components.supernotify import CONF_DELIVERY, CONF_NOTIFY, CONF_SELECTION, SELECTION_DEFAULT

EXAMPLES_ROOT = "examples"

examples = os.listdir(EXAMPLES_ROOT)


@pytest.mark.parametrize("config_name", examples)
async def test_examples(hass: HomeAssistant, config_name) -> None:

    with open(os.path.join(EXAMPLES_ROOT, config_name), "r") as f:
        config = yaml.safe_load(f)
    uut_config = config[CONF_NOTIFY][0]
    service_name = uut_config[CONF_NAME]
    platform = uut_config[CONF_PLATFORM]
    assert await async_setup_component(
        hass,
        notify.DOMAIN,
        config
    )
    await hass.async_block_till_done()

    assert hass.services.has_service(notify.DOMAIN, service_name)
    services = await hass.services.async_call(platform,
                                              "enquire_deliveries_by_scenario",
                                              blocking=True,
                                              return_response=True)
    expected_defaults = [d for d, dc in uut_config.get(
        CONF_DELIVERY, {}).items() if dc.get(CONF_ENABLED, True)
        and SELECTION_DEFAULT in dc.get(CONF_SELECTION, [SELECTION_DEFAULT])]  # noqa: F821
    assert services["DEFAULT"] == unordered(expected_defaults)
