import pathlib
from unittest.mock import patch

import homeassistant.components.notify as notify
from homeassistant import config as hass_config
from homeassistant.const import SERVICE_RELOAD
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.supernotify import ATTR_DEFAULT, DOMAIN, PLATFORM_SCHEMA, SCENARIO_DEFAULT

FIXTURE = pathlib.Path(__file__).parent.joinpath(
    "..", "..", "examples", "maximal.yaml"
)


SIMPLE_CONFIG = {
    "name": DOMAIN,
    "platform": DOMAIN,
    "recipients": [
        {
            "person": "person.house_owner",
            "email": "test@testing.com",
            "phone_number": "+4497177848484"
        }
    ]
}


async def test_schema():
    assert PLATFORM_SCHEMA(SIMPLE_CONFIG)


async def test_reload(hass: HomeAssistant) -> None:
    hass.states.async_set("alarm_control_panel.home_alarm_control", {})
    hass.states.async_set("supernotify.delivery_priority", "high")

    assert await async_setup_component(
        hass,
        notify.DOMAIN,
        {
            notify.DOMAIN: [SIMPLE_CONFIG]
        }
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
    uut = hass.data["notify_services"][DOMAIN][0]
    assert len(uut.context.recipients) == 2

    assert "html_email" in uut.context.deliveries
    assert "backup_mail" in uut.context.deliveries
    assert "backup_mail" not in uut.context.delivery_by_scenario[SCENARIO_DEFAULT]
    assert "text_message" in uut.context.deliveries
    assert "alexa_announce" in uut.context.deliveries
    assert "mobile_push" in uut.context.deliveries
    assert "alexa_show" in uut.context.deliveries
    assert "play_chimes" in uut.context.deliveries
    assert "doorbell_chime_alexa" in uut.context.deliveries
    assert "sleigh_bells" in uut.context.deliveries
    assert "upstairs_siren" in uut.context.deliveries
    assert "expensive_api_call" in uut.context.deliveries
    assert "expensive_api_call" not in uut.context.delivery_by_scenario[SCENARIO_DEFAULT]

    assert len(uut.context.deliveries) == 11


async def test_call_service(hass: HomeAssistant) -> None:

    assert await async_setup_component(
        hass,
        notify.DOMAIN,
        {
            notify.DOMAIN: [SIMPLE_CONFIG]
        }
    )

    await hass.async_block_till_done()

    await hass.services.async_call(
        notify.DOMAIN,
        DOMAIN,
        {"title": "my title", "message": "unit test"},
        blocking=True,
    )


async def test_empty_config(hass: HomeAssistant) -> None:

    assert await async_setup_component(
        hass,
        notify.DOMAIN,
        {
            notify.DOMAIN: [
                {
                    "name": DOMAIN,
                    "platform": DOMAIN
                },
            ]
        },
    )

    await hass.async_block_till_done()

    assert hass.services.has_service(notify.DOMAIN, DOMAIN)
    await hass.services.async_call(
        notify.DOMAIN,
        DOMAIN,
        {"title": "my title", "message": "unit test"},
        blocking=True,
    )

async def test_call_supplemental_services(hass: HomeAssistant) -> None:

    assert await async_setup_component(
        hass,
        notify.DOMAIN,
        {
            notify.DOMAIN: [SIMPLE_CONFIG]
        }
    )

    await hass.async_block_till_done()

    response = await hass.services.async_call(
        "supernotify",
        "enquire_deliveries_by_scenario",
        None,
        blocking=True,
        return_response=True
    )
    assert response == {"DEFAULT":[]}