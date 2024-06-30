"""Supernotify service, extending BaseNotificationService"""

import datetime as dt
import json
import logging
from dataclasses import asdict
from typing import Any

from cachetools import TTLCache
from homeassistant.components.notify.legacy import BaseNotificationService
from homeassistant.const import CONF_CONDITION, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, HomeAssistant, ServiceCall, SupportsResponse, callback
from homeassistant.helpers import condition
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.json import ExtendedJSONEncoder
from homeassistant.helpers.reload import async_setup_reload_service
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from custom_components.supernotify.archive import ARCHIVE_PURGE_MIN_INTERVAL
from custom_components.supernotify.scenario import Scenario

from . import (
    ATTR_ACTION,
    ATTR_DATA,
    ATTR_DUPE_POLICY_MTSLP,
    ATTR_DUPE_POLICY_NONE,
    ATTR_USER_ID,
    CONF_ACTION_GROUPS,
    CONF_ACTIONS,
    CONF_ARCHIVE,
    CONF_CAMERAS,
    CONF_DELIVERY,
    CONF_DUPE_CHECK,
    CONF_DUPE_POLICY,
    CONF_HOUSEKEEPING,
    CONF_HOUSEKEEPING_TIME,
    CONF_LINKS,
    CONF_MEDIA_PATH,
    CONF_METHODS,
    CONF_PERSON,
    CONF_RECIPIENTS,
    CONF_SCENARIOS,
    CONF_SIZE,
    CONF_TEMPLATE_PATH,
    CONF_TTL,
    DOMAIN,
    PLATFORM_SCHEMA,
    PLATFORMS,
    PRIORITY_MEDIUM,
    PRIORITY_VALUES,
    CommandType,
    ConditionVariables,
    GlobalTargetType,
    QualifiedTargetType,
    RecipientType,
    TargetType,
)
from .configuration import SupernotificationConfiguration
from .methods.alexa_media_player import AlexaMediaPlayerDeliveryMethod
from .methods.chime import ChimeDeliveryMethod
from .methods.email import EmailDeliveryMethod
from .methods.generic import GenericDeliveryMethod
from .methods.media_player_image import MediaPlayerImageDeliveryMethod
from .methods.mobile_push import MobilePushDeliveryMethod
from .methods.persistent import PersistentDeliveryMethod
from .methods.sms import SMSDeliveryMethod
from .notification import Notification

_LOGGER = logging.getLogger(__name__)

SNOOZE_TIME = 60 * 60  # TODO: move to configuration

METHODS: list[type] = [
    EmailDeliveryMethod,
    SMSDeliveryMethod,
    AlexaMediaPlayerDeliveryMethod,
    MobilePushDeliveryMethod,
    MediaPlayerImageDeliveryMethod,
    ChimeDeliveryMethod,
    PersistentDeliveryMethod,
    GenericDeliveryMethod,
]


async def async_get_service(
    hass: HomeAssistant,
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None = None,
) -> "SuperNotificationService":
    _ = PLATFORM_SCHEMA  # schema must be imported even if not used for HA platform detection
    _ = discovery_info
    for delivery in config.get(CONF_DELIVERY, {}).values():
        if delivery and CONF_CONDITION in delivery:
            try:
                await condition.async_validate_condition_config(hass, delivery[CONF_CONDITION])
            except Exception as e:
                _LOGGER.error("SUPERNOTIFY delivery %s fails condition: %s", delivery[CONF_CONDITION], e)
                raise

    hass.states.async_set(
        f"{DOMAIN}.configured",
        "True",
        {
            CONF_DELIVERY: config.get(CONF_DELIVERY, {}),
            CONF_LINKS: config.get(CONF_LINKS, ()),
            CONF_TEMPLATE_PATH: config.get(CONF_TEMPLATE_PATH),
            CONF_MEDIA_PATH: config.get(CONF_MEDIA_PATH),
            CONF_ARCHIVE: config.get(CONF_ARCHIVE, {}),
            CONF_RECIPIENTS: config.get(CONF_RECIPIENTS, ()),
            CONF_ACTIONS: config.get(CONF_ACTIONS, {}),
            CONF_SCENARIOS: list(config.get(CONF_SCENARIOS, {}).keys()),
            CONF_METHODS: config.get(CONF_METHODS, {}),
            CONF_CAMERAS: config.get(CONF_CAMERAS, {}),
            CONF_DUPE_CHECK: config.get(CONF_DUPE_CHECK, {}),
        },
    )
    hass.states.async_set(f"{DOMAIN}.failures", "0")
    hass.states.async_set(f"{DOMAIN}.sent", "0")

    await async_setup_reload_service(hass, DOMAIN, PLATFORMS)
    service = SuperNotificationService(
        hass,
        deliveries=config[CONF_DELIVERY],
        template_path=config[CONF_TEMPLATE_PATH],
        media_path=config[CONF_MEDIA_PATH],
        archive=config[CONF_ARCHIVE],
        housekeeping=config[CONF_HOUSEKEEPING],
        recipients=config[CONF_RECIPIENTS],
        mobile_actions=config[CONF_ACTION_GROUPS],
        scenarios=config[CONF_SCENARIOS],
        links=config[CONF_LINKS],
        method_defaults=config[CONF_METHODS],
        cameras=config[CONF_CAMERAS],
        dupe_check=config[CONF_DUPE_CHECK],
    )
    await service.initialize()

    def supplemental_service_enquire_deliveries_by_scenario(_call: ServiceCall) -> dict:
        return service.enquire_deliveries_by_scenario()

    def supplemental_service_enquire_last_notification(_call: ServiceCall) -> dict:
        return service.last_notification.contents() if service.last_notification else {}

    async def supplemental_service_enquire_active_scenarios(call: ServiceCall) -> dict:
        trace = call.data.get("trace", False)
        return {"scenarios": await service.enquire_active_scenarios(trace)}

    async def supplemental_service_enquire_occupancy(_call: ServiceCall) -> dict:
        return {"scenarios": await service.enquire_occupancy()}

    async def supplemental_service_enquire_snoozes(_call: ServiceCall) -> dict:
        return {"snoozes": service.enquire_snoozes()}

    async def supplemental_service_clear_snoozes(_call: ServiceCall) -> dict:
        return {"cleared": service.clear_snoozes()}

    async def supplemental_service_enquire_people(_call: ServiceCall) -> dict:
        return {"people": service.enquire_people()}

    async def supplemental_service_purge_archive(call: ServiceCall) -> dict[str, Any]:
        days = call.data.get("days")
        if service.context.archive is None:
            return {"error": "No archive configured"}
        return {
            "purged": service.context.archive.cleanup(days=days, force=True),
            "remaining": service.context.archive.size(),
            "interval": ARCHIVE_PURGE_MIN_INTERVAL,
            "days": service.context.archive.archive_days if days is None else days,
        }

    hass.services.async_register(
        DOMAIN,
        "enquire_deliveries_by_scenario",
        supplemental_service_enquire_deliveries_by_scenario,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        "enquire_last_notification",
        supplemental_service_enquire_last_notification,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        "enquire_active_scenarios",
        supplemental_service_enquire_active_scenarios,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        "enquire_occupancy",
        supplemental_service_enquire_occupancy,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        "enquire_people",
        supplemental_service_enquire_people,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        "enquire_snoozes",
        supplemental_service_enquire_snoozes,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        "clear_snoozes",
        supplemental_service_clear_snoozes,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        "purge_archive",
        supplemental_service_purge_archive,
        supports_response=SupportsResponse.ONLY,
    )

    return service


class SuperNotificationService(BaseNotificationService):
    """Implement SuperNotification service."""

    def __init__(
        self,
        hass: HomeAssistant,
        deliveries: dict[str, dict] | None = None,
        template_path: str | None = None,
        media_path: str | None = None,
        archive: dict | None = None,
        housekeeping: dict | None = None,
        recipients: list | None = None,
        mobile_actions: dict | None = None,
        scenarios: dict[str, dict] | None = None,
        links: list | None = None,
        method_defaults: dict | None = None,
        cameras: list[dict] | None = None,
        dupe_check: dict | None = None,
    ) -> None:
        """Initialize the service."""
        self.hass: HomeAssistant = hass
        self.last_notification: Notification | None = None
        self.failures: int = 0
        self.housekeeping: dict = housekeeping or {}
        self.sent: int = 0
        self.context = SupernotificationConfiguration(
            hass,
            deliveries,
            links or [],
            recipients or [],
            mobile_actions,
            template_path,
            media_path,
            archive,
            scenarios,
            method_defaults or {},
            cameras,
        )
        self.unsubscribes: list = []
        self.dupe_check_config: dict[str, Any] = dupe_check or {}
        self.last_purge: dt.datetime | None = None
        self.notification_cache: TTLCache = TTLCache(
            maxsize=self.dupe_check_config.get(CONF_SIZE, 100), ttl=self.dupe_check_config.get(CONF_TTL, 120)
        )

        self.unsubscribes.append(self.hass.bus.async_listen("mobile_app_notification_action", self.on_mobile_action))
        housekeeping_schedule = self.housekeeping.get(CONF_HOUSEKEEPING_TIME)
        if housekeeping_schedule:
            _LOGGER.info("SUPERNOTIFY setting up housekeeping schedule at: %s", housekeeping_schedule)
            self.unsubscribes.append(
                async_track_time_change(
                    self.hass,
                    self.async_nightly_tasks,
                    hour=housekeeping_schedule.hour,
                    minute=housekeeping_schedule.minute,
                    second=housekeeping_schedule.second,
                )
            )

        self.unsubscribes.append(hass.bus.async_listen(EVENT_HOMEASSISTANT_STOP, self.async_shutdown))

    async def initialize(self) -> None:
        await self.context.initialize()
        await self.context.register_delivery_methods(delivery_method_classes=METHODS)
        self.expose_entities()

    async def async_shutdown(self, event: Event) -> None:
        _LOGGER.info("SUPERNOTIFY shutting down, %s", event)
        self.shutdown()

    def shutdown(self) -> None:
        for unsub in self.unsubscribes:
            if unsub:
                try:
                    _LOGGER.debug("SUPERNOTIFY unsubscribing: %s", unsub)
                    unsub()
                except Exception as e:
                    _LOGGER.error("SUPERNOTIFY failed to unsubscribe: %s", e)
        _LOGGER.info("SUPERNOTIFY shut down")

    def expose_entities(self) -> None:
        for scenario in self.context.scenarios.values():
            self.hass.states.async_set(f"{DOMAIN}.scenario_{scenario.name}", "", scenario.attributes(include_condition=False))
        for method in self.context.methods.values():
            self.hass.states.async_set(
                f"{DOMAIN}.method_{method.method}", str(len(method.valid_deliveries) > 0), method.attributes()
            )
        for delivery_name, delivery in self.context._deliveries.items():
            self.hass.states.async_set(
                f"{DOMAIN}.delivery_{delivery_name}", str(delivery_name in self.context.deliveries), delivery
            )

    def dupe_check(self, notification: Notification) -> bool:
        policy = self.dupe_check_config.get(CONF_DUPE_POLICY, ATTR_DUPE_POLICY_MTSLP)
        if policy == ATTR_DUPE_POLICY_NONE:
            return False
        notification_hash = notification.hash()
        if notification.priority in PRIORITY_VALUES:
            same_or_higher_priority = PRIORITY_VALUES[PRIORITY_VALUES.index(notification.priority) :]
        else:
            same_or_higher_priority = [notification.priority]
        dupe = False
        if any((notification_hash, p) in self.notification_cache for p in same_or_higher_priority):
            _LOGGER.debug("SUPERNOTIFY Detected dupe notification")
            dupe = True
        self.notification_cache[(notification_hash, notification.priority)] = notification.id
        return dupe

    async def async_send_message(
        self, message: str = "", title: str | None = None, target: list | str | None = None, **kwargs
    ) -> None:
        """Send a message via chosen method."""
        data = kwargs.get(ATTR_DATA, {})
        notification = None
        _LOGGER.debug("Message: %s, target: %s, data: %s", message, target, data)

        try:
            notification = Notification(self.context, message, title, target, data)
            await notification.initialize()
            if self.dupe_check(notification):
                notification.suppress()
            else:
                if await notification.deliver():
                    self.sent += 1
                    self.hass.states.async_set(f"{DOMAIN}.sent", str(self.sent))
                else:
                    _LOGGER.warning("SUPERNOTIFY Failed to deliver %s, error count %s", notification.id, notification.errored)

            self.last_notification = notification
            self.context.archive.archive(notification)

            _LOGGER.debug(
                "SUPERNOTIFY %s deliveries, %s errors, %s skipped",
                notification.delivered,
                notification.errored,
                notification.skipped,
            )
        except Exception as err:
            _LOGGER.error("SUPERNOTIFY Failed to send message %s: %s", message, err)
            self.failures += 1
            self.hass.states.async_set(f"{DOMAIN}.failures", str(self.failures))

    def enquire_deliveries_by_scenario(self) -> dict[str, list[Scenario]]:
        return self.context.delivery_by_scenario

    async def enquire_occupancy(self) -> dict[str, list]:
        return self.context.determine_occupancy()

    async def enquire_active_scenarios(self, trace: bool) -> list[str] | dict:
        occupiers = self.context.determine_occupancy()
        cvars = ConditionVariables([], [], PRIORITY_MEDIUM, occupiers)

        def safe_json(v: Any) -> Any:
            return json.loads(json.dumps(v, cls=ExtendedJSONEncoder))

        if trace:
            results = {"ENABLED": [], "DISABLED": [], "VARS": asdict(cvars)}
            for s in self.context.scenarios.values():
                if await s.trace(cvars):
                    results["ENABLED"].append(safe_json(s.attributes(include_trace=True)))  # type: ignore
                else:
                    results["DISABLED"].append(safe_json(s.attributes(include_trace=True)))  # type: ignore
            return results

        return [s.name for s in self.context.scenarios.values() if await s.evaluate(cvars)]

    def enquire_snoozes(self) -> list[dict[str, Any]]:
        return [s.export() for s in self.context.snoozes.values()]

    def clear_snoozes(self) -> int:
        cleared = len(self.context.snoozes)
        self.context.snoozes.clear()
        return cleared

    def enquire_people(self) -> list[dict]:
        return list(self.context.people.values())

    @callback
    def on_mobile_action(self, event: Event) -> None:
        """Listen for mobile actions relevant to snooze and silence notifications

        Example Action:
        event_type: mobile_app_notification_action
        data:
            foo: a
        origin: REMOTE
        time_fired: "2024-04-20T13:14:09.360708+00:00"
        context:
            id: 01HVXT93JGWEDW0KE57Z0X6Z1K
            parent_id: null
            user_id: e9dbae1a5abf44dbbad52ff85501bb17
        """
        event_name = event.data.get(ATTR_ACTION)
        if event_name is None or not event_name.startswith("SUPERNOTIFY_"):
            return  # event not intended for here
        try:
            cmd: CommandType
            target_type: TargetType | None = None
            target: str | None = None
            snooze_for: int = SNOOZE_TIME
            recipient_type: RecipientType | None = None

            _LOGGER.debug(
                "SUPERNOTIFY Mobile Action: %s, %s, %s, %s", event.origin, event.time_fired, event.data, event.context
            )
            event_parts: list[str] = event_name.split("_")
            if len(event_parts) < 4:
                _LOGGER.warning("SUPERNOTIFY Malformed mobile event action %s", event_name)
                return
            cmd = CommandType[event_parts[1]]
            recipient_type = RecipientType[event_parts[2]]
            if event_parts[3] in QualifiedTargetType and len(event_parts) > 4:
                target_type = QualifiedTargetType[event_parts[3]]
                target = event_parts[4]
                snooze_for = int(event_parts[-1]) if len(event_parts) == 6 else SNOOZE_TIME
            elif event_parts[3] in GlobalTargetType and len(event_parts) >= 4:
                target_type = GlobalTargetType[event_parts[3]]
                snooze_for = int(event_parts[-1]) if len(event_parts) == 5 else SNOOZE_TIME

            if cmd is None or target_type is None or recipient_type is None:
                _LOGGER.warning("SUPERNOTIFY Invalid mobile event name %s", event_name)
                return

        except KeyError as ke:
            _LOGGER.warning("SUPERNOTIFY Unknown enum in event %s: %s", event, ke)
            return
        except Exception as e:
            _LOGGER.warning("SUPERNOTIFY Unable to analyze event %s: %s", event, e)
            return

        try:
            recipient: str | None = None
            if recipient_type == RecipientType.USER:
                people = [
                    p.get(CONF_PERSON)
                    for p in self.context.people.values()
                    if p.get(ATTR_USER_ID) == event.context.user_id and event.context.user_id is not None and p.get(CONF_PERSON)
                ]
                if people:
                    recipient = people[0]
                    _LOGGER.debug("SUPERNOTIFY mobile action from %s mapped to %s", event.context.user_id, recipient)
                else:
                    _LOGGER.warning("SUPERNOTIFY Unable to find person for action from %s", event.context.user_id)
                    return

            self.context.register_snooze(cmd, target_type, target, recipient_type, recipient, snooze_for)

        except Exception as e:
            _LOGGER.warning("SUPERNOTIFY Unable to handle event %s: %s", event, e)

    @callback
    def async_nightly_tasks(self, now: dt.datetime) -> None:
        _LOGGER.info("SUPERNOTIFY Housekeeping starting as scheduled at %s", now)
        self.context.archive.cleanup()
        self.context.purge_snoozes()
        _LOGGER.info("SUPERNOTIFY Housekeeping completed")
