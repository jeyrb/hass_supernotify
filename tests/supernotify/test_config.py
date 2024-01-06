import pathlib
from unittest.mock import patch

from homeassistant import config as hass_config
import homeassistant.components.notify as notify
from homeassistant.components.supernotify import DOMAIN
from homeassistant.const import SERVICE_RELOAD
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

FIXTURE = pathlib.Path(__file__).parent.joinpath(
    "fixtures", "configuration.yaml"
)


async def test_reload(hass: HomeAssistant) -> None:
    hass.states.async_set("alarm_control_panel.home_alarm_control", {})
    hass.states.async_set("input_select.supernotify_priority","high")


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
                            "person": "person.house_owner",
                            "email" : "test@testing.com",
                            "mobile": {
                                "phone_number": "+4497177848484",
                                "devices": [
                                    "mobile_app.owner_phone"
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
    uut = hass.data["notify_services"]["supernotify"][0]
    assert len(uut.recipients) == 2

    assert "html_email" in uut.deliveries
    assert "text_message" in uut.deliveries
    assert "alexa_announce" in uut.deliveries
    assert "apple_push" in uut.deliveries
    assert "alexa_show" in uut.deliveries
    assert "play_chimes" in uut.deliveries

    assert len(uut.deliveries) == 6

    await hass.services.async_call(
            notify.DOMAIN,
            "supernotifier_reloaded",
            {"title":"my title","message":"unit test"},
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
            {"title":"my title","message":"unit test"},
            blocking=True,
        )


