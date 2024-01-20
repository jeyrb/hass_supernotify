from unittest.mock import Mock

from custom_components.supernotify import CONF_DATA, CONF_PERSON, CONF_RECIPIENTS
from custom_components.supernotify.common import SuperNotificationContext
from custom_components.supernotify.delivery_method import DeliveryMethod
from custom_components.supernotify.notification import Notification

class DummyDeliveryMethod(DeliveryMethod):
    def __init__(self, *args, **kwargs):
        super().__init__("dummy", False, *args, **kwargs)
        self.test_calls = []

    def recipient_target(self, recipient):
        return [recipient.get(CONF_PERSON).replace('person.', '')] if recipient else []

    async def _delivery_impl(self, message, title, targets, priority,
                             scenarios, data, config):
        self.test_calls.append([message, title, targets, priority,
                                scenarios, data, config])


async def test_filter_recipients() -> None:
    hass = Mock()
    context = SuperNotificationContext(recipients=[{CONF_PERSON: "person.new_home_owner"},
                                                   {CONF_PERSON: "person.bidey_in"}])
    uut = DummyDeliveryMethod(hass, context, {})
    hass_states = {"person.new_home_owner": Mock(state="not_home"),
                   "person.bidey_in": Mock(state="home")}
    hass.states.get = hass_states.get

    assert len(uut.filter_recipients_by_occupancy("all_in")) == 0
    assert len(uut.filter_recipients_by_occupancy("all_out")) == 0
    assert len(uut.filter_recipients_by_occupancy("any_in")) == 2
    assert len(uut.filter_recipients_by_occupancy("any_out")) == 2
    assert len(uut.filter_recipients_by_occupancy("only_in")) == 1
    assert len(uut.filter_recipients_by_occupancy("only_out")) == 1

    assert {r["person"] for r in uut.filter_recipients_by_occupancy(
        "only_out")} == {"person.new_home_owner"}
    assert {r["person"]
            for r in uut.filter_recipients_by_occupancy("only_in")} == {"person.bidey_in"}


async def test_default_recipients() -> None:
    hass = Mock()
    context = SuperNotificationContext(recipients=[{CONF_PERSON: "person.new_home_owner"},
                                                   {CONF_PERSON: "person.bidey_in"}])
    uut = DummyDeliveryMethod(hass, context, {})
    await uut.deliver(Notification(context))
    assert uut.test_calls == [
        [None, None, ['new_home_owner', 'bidey_in'], 'medium', {}, {}, {}]]


async def test_default_recipients_with_override() -> None:
    hass = Mock()
    context = SuperNotificationContext(recipients=[{CONF_PERSON: "person.new_home_owner"},
                                                   {CONF_PERSON: "person.bidey_in"}])
    uut = DummyDeliveryMethod(hass, context, {})
    await uut.deliver(Notification(context,None,
                                   service_data={CONF_RECIPIENTS:["person.new_home_owner"]}))
    assert uut.test_calls == [
        [None, None, ['new_home_owner'], 'medium', {}, {}, {}]]
