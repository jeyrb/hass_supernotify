# mypy: disable-error-code="name-defined"

import copy
import logging
import time
import typing
from pathlib import Path
from typing import Any

from . import ATTR_TIMESTAMP, CONF_MESSAGE, CONF_TITLE, PRIORITY_MEDIUM

_LOGGER = logging.getLogger(__name__)


class Envelope:
    """Wrap a notification with a specific set of targets and service data possibly customized for those targets"""

    def __init__(
        self,
        delivery_name: str,
        notification: "Notification | None" = None,  # noqa: F821 # type: ignore
        targets: list | None = None,
        data: dict | None = None,
    ) -> None:
        self.targets: list = targets or []
        self.delivery_name: str = delivery_name
        self._notification = notification
        self.notification_id = None
        self.media = None
        self.action_groups = None
        self.priority = PRIORITY_MEDIUM
        self.message: str | None = None
        self.title: str | None = None
        self.message_html: str | None = None
        self.data: dict = {}
        self.actions: list = []
        delivery_config_data: dict = {}
        if notification:
            self.notification_id = notification.id
            self.media = notification.media
            self.action_groups = notification.action_groups
            self.actions = notification.actions
            self.priority = notification.priority
            self.message = notification.message(delivery_name)
            self.message_html = notification.message_html
            self.title = notification.title(delivery_name)
            delivery_config_data = notification.delivery_data(delivery_name)

        if data:
            self.data = copy.deepcopy(delivery_config_data) if delivery_config_data else {}
            self.data |= data
        else:
            self.data = delivery_config_data

        self.delivered: int = 0
        self.errored: int = 0
        self.skipped: int = 0
        self.calls: list = []
        self.failed_calls: list = []
        self.delivery_error: list[str] | None = None

    async def grab_image(self) -> Path | None:
        """Grab an image from a camera, snapshot URL, MQTT Image etc"""
        if self._notification:
            return await self._notification.grab_image(self.delivery_name)
        return None

    def core_service_data(self) -> dict:
        """Build the core set of `service_data` dict to pass to underlying notify service"""
        data: dict = {}
        # message is mandatory for notify platform
        data[CONF_MESSAGE] = self.message or ""
        timestamp = self.data.get(ATTR_TIMESTAMP)
        if timestamp:
            data[CONF_MESSAGE] = f"{data[CONF_MESSAGE]} [{time.strftime(timestamp, time.localtime())}]"
        if self.title:
            data[CONF_TITLE] = self.title
        return data

    def contents(self, minimal: bool = True) -> dict[str, typing.Any]:
        exclude_attrs = ["_notification"]
        if minimal:
            exclude_attrs.extend("resolved")
        return {k: v for k, v in self.__dict__.items() if k not in exclude_attrs}

    def __eq__(self, other: Any | None) -> bool:
        """Specialized equality check for subset of attributesfl"""
        if other is None or not isinstance(other, Envelope):
            return False
        return (
            self.targets == other.targets
            and self.delivery_name == other.delivery_name
            and self.data == other.data
            and self.notification_id == other.notification_id
        )
