import copy
import logging
import time
import typing

from . import (ATTR_TIMESTAMP, CONF_MESSAGE, CONF_TITLE, PRIORITY_MEDIUM)

_LOGGER = logging.getLogger(__name__)


class Envelope:
    """
    Wrap a notification with a specific set of targets and service data possibly customized for those targets
    """

    def __init__(self, delivery_name: str, notification=None, targets=None, data=None):
        self.targets = targets or []
        self.delivery_name: str = delivery_name
        self._notification = notification
        if notification:
            self.notification_id = notification.id
            self.media = notification.media
            self.actions = notification.actions
            self.priority = notification.priority
            self.message = notification.message(delivery_name)
            self.message_html = notification.message_html
            self.title = notification.title(delivery_name)
            delivery_config_data = notification.delivery_data(delivery_name)
        else:
            self.notification_id = None
            self.media = None
            self.actions = []
            self.priority = PRIORITY_MEDIUM
            self.message: typing.Optional[str] = None
            self.title: typing.Optional[str] = None
            self.message_html: typing.Optional[str] = None
            delivery_config_data = None
        if data:
            self.data = copy.deepcopy(delivery_config_data) if delivery_config_data else {}
            self.data |= data
        else:
            self.data = delivery_config_data

        self.delivered = 0
        self.errored = 0
        self.skipped = 0
        self.calls = []
        self.failed_calls = []
        self.delivery_error = None

    def grab_image(self):
        """Grab an image from a camera, snapshot URL, MQTT Image etc"""
        if self._notification:
            return self._notification.grab_image(self.delivery_name)
        else:
            return None

    def core_service_data(self):
        """Build the core set of `service_data` dict to pass to underlying notify service"""
        data: dict = {}
        # message is mandatory for notify platform
        data[CONF_MESSAGE] = self.message or ""
        if self.data.get(ATTR_TIMESTAMP):
            data[CONF_MESSAGE] = "%s [%s]" % (
                data[CONF_MESSAGE],
                time.strftime(self.data.get(ATTR_TIMESTAMP), time.localtime()),
            )
        if self.title:
            data[CONF_TITLE] = self.title
        return data

    def contents(self, minimal: bool = True) -> dict[str, typing.Any]:
        exclude_attrs = ["_notification"]
        if minimal:
            exclude_attrs.extend("resolved")
        sanitized = {k: v for k, v in self.__dict__.items() if k not in exclude_attrs}
        return sanitized

    def __eq__(self, other):
        if not isinstance(other, Envelope):
            return False
        return (
            self.targets == other.targets
            and self.delivery_name == other.delivery_name
            and self.data == other.data
            and self.notification_id == other.notification_id
        )

