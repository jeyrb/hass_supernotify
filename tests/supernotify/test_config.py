import pytest
from unittest.mock import AsyncMock, Mock, patch
from homeassistant import config as conf_util
import pytest

from homeassistant import config_entries
import homeassistant.components.notify as notify
from homeassistant.components.supernotify import DOMAIN
from homeassistant.const import SERVICE_RELOAD
from tests.common import MockConfigEntry
from homeassistant.setup import async_setup_component
from homeassistant.core import HomeAssistant
from tests.common import get_fixture_path
from homeassistant import config as hass_config
import pathlib

FIXTURE = pathlib.Path(__file__).parent.joinpath(
    "fixtures", "configuration.yaml"
)


async def test_reload(hass: HomeAssistant) -> None:

    assert await async_setup_component(
        hass,
        notify.DOMAIN,
        {
            notify.DOMAIN: [
                {
                    "name": DOMAIN,
                    "platform": DOMAIN,
                    "recipients": [
                        {
                            'person': 'person.house_owner',
                            'email' : 'test@testing.com',
                            'mobile': {
                                'number': '+4497177848484',
                                'devices': [
                                    'mobile_app.owner_phone'
                                ]

                            }

                        },
                    ]
                },
            ]
        },
    )

    await hass.async_block_till_done()

    assert hass.services.has_service(notify.DOMAIN, DOMAIN)

    with patch.object(hass_config, "YAML_CONFIG_FILE", FIXTURE):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_RELOAD,
            {},
            blocking=True,
        )
        await hass.async_block_till_done()

    assert not hass.services.has_service(notify.DOMAIN, DOMAIN)
    uut = hass.data['notify_services']['supernotify'][0]
    assert len(uut.recipients) == 2
    assert len(uut.alexa_devices) == 5
    await hass.services.async_call(
            notify.DOMAIN,
            'supernotifier_reloaded',
            {'title':'my title','message':'unit test'},
            blocking=True,
        )
   

    