from unittest.mock import Mock

from custom_components.supernotify import CONF_PERSON
from custom_components.supernotify.common import DeliveryMethod, SuperNotificationContext

class DummyDeliveryMethod(DeliveryMethod):
    def __init__(self, *args, **kwargs):
        super().__init__("dummy", False, *args, **kwargs)

    def _delivery_impl(self, **kwargs):
        pass


async def test_filter_recipients() -> None:
    hass = Mock()
    context = SuperNotificationContext(recipients=[{CONF_PERSON: "person.new_home_owner"},
                                                   {CONF_PERSON: "person.bidey_in"}])
    uut = DummyDeliveryMethod(hass, context, {})
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
