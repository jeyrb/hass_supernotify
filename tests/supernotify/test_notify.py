from unittest.mock import Mock
from homeassistant.components.supernotify import CONF_OVERRIDE_BASE, CONF_OVERRIDE_REPLACE

from homeassistant.components.supernotify.notify import SuperNotificationService

DELIVERY = {
    "email": {"method": "email","service": "notify.smtp"},
    "text": {"method": "sms","service": "notify.sms"},
    "chime": {"method": "chime", "entities": ["switch.bell_1", "script.siren_2"]},
    "alexa": {"method":"alexa", "service":"notify.alexa"}
}

RECIPIENTS = [
    {"person": "person.new_home_owner",
        "email": "me@tester.net",
        "mobile": {
            "number": "+447989408889",
            "apple_devices": [
                "mobile_app.new_iphone"
            ]
        }
     },
    {
        "person": "person.bidey_in",
        "mobile": {
            "number": "+4489393013834"
        }
    }
]


async def test_on_notify_sms() -> None:
    """Test on_notify_sms."""
    hass = Mock()
    uut = SuperNotificationService(
        hass, deliveries=DELIVERY, recipients=RECIPIENTS)
    # Call with no target
    uut.on_notify_sms("title", "message")
    hass.services.call.assert_called_with("notify", "sms", service_data={
                                          "message": "title message", "data": {}, "target": ["+447989408889", "+4489393013834"]})

    hass.reset_mock()
    # Call with target
    target = ["+440900876534", "person.new_home_owner"]
    uut.on_notify_sms("title", "message", target=target)
    hass.services.call.assert_called_with("notify", "sms", service_data={
                                          "message": "title message", "data": {}, "target": ["+440900876534", "+447989408889"]})


async def test_on_notify_chime() -> None:
    """Test on_notify_chime."""
    hass = Mock()
    uut = SuperNotificationService(
        hass, deliveries=DELIVERY, recipients=RECIPIENTS)
    uut.on_notify_chime(config=DELIVERY["chime"])
    hass.services.call.assert_any_call("script", "turn_on", service_data={
                                       "entity_id": "script.siren_2"})
    hass.services.call.assert_any_call("switch", "turn_on", service_data={
                                       "entity_id": "switch.bell_1"})


async def test_on_notify_apple_push() -> None:
    """Test on_notify_apple_push."""
    hass = Mock()
    uut = SuperNotificationService(
        hass, deliveries=DELIVERY, recipients=RECIPIENTS)
    uut.on_notify_apple("testing", "hello there")
    hass.services.call.assert_called_with("notify", "mobile_app.new_iphone",
                                          service_data={"title": "testing", 
                                                        "message": "hello there", 
                                                        "data": {"actions": [], "push": {"interruption-level": "active"}, "group": "general-appd"}})

async def test_on_notify_email() -> None:
    """Test on_notify_email."""
    hass = Mock()
    uut = SuperNotificationService(
        hass, deliveries=DELIVERY, recipients=RECIPIENTS)
    uut.on_notify_email("hello there",title="testing")
    hass.services.call.assert_called_with("notify", "smtp",
                                          target=['me@tester.net'], 
                                          service_data={'title': 'testing', 'message': 'hello there', 'data': {}})

async def test_on_notify_alexa() -> None:
    """Test on_notify_alexa."""
    hass = Mock()
    uut = SuperNotificationService(
        hass, deliveries=DELIVERY, recipients=RECIPIENTS)
    uut.on_notify_alexa("hello there")
    hass.services.call.assert_called_with("notify", "alexa",
                                          service_data={'message': 'hello there', 'data': {'type': 'announce'}, 'target': []})

async def test_on_notify_media() -> None:
    """Test on_notify_media_player """
    hass = Mock()
    uut = SuperNotificationService(
        hass, deliveries=DELIVERY, recipients=RECIPIENTS,
        overrides={'image_url':{CONF_OVERRIDE_BASE:'http://10.10.10.10/ftp',CONF_OVERRIDE_REPLACE:"https://myserver"}})
    uut.on_notify_media_player("hello there",snapshot_url="http://10.10.10.10/ftp/pic.jpeg",target=["media_player.kitchen"])
    hass.services.call.assert_called_with("media_player", "play_media",
                                           service_data={'message': 'hello there', 
                                                         'data': {'media_content_id': 'https://myserver/pic.jpeg', 'media_content_type': 'image'}, 'target': ['media_player.kitchen']})

    
async def test_filter_recipients() -> None:
    """Test filter_recipients."""
    hass = Mock()
    hass.states = Mock()
    uut = SuperNotificationService(
        hass, deliveries=DELIVERY, recipients=RECIPIENTS)
    # Mock hass states
    hass_states = {"person.new_home_owner": Mock(state="not_home"),
                   "person.bidey_in": Mock(state="home")}
    hass.states.get = hass_states.get

    assert len(uut.filter_recipients("all_in")) == 0
    assert len(uut.filter_recipients("all_out")) == 0
    assert len(uut.filter_recipients("any_in")) == 2
    assert len(uut.filter_recipients("any_out")) == 2

    assert {r["person"] for r in uut.filter_recipients(
        "only_out")} == {"person.new_home_owner"}
    assert {r["person"]
            for r in uut.filter_recipients("only_in")} == {"person.bidey_in"}
