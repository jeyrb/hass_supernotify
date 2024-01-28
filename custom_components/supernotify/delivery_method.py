import copy
import logging
from abc import abstractmethod
from homeassistant.const import (
    CONF_CONDITION,
    CONF_DEFAULT,
    CONF_METHOD,
    CONF_NAME,
    CONF_SERVICE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import condition
from homeassistant.helpers import config_validation as cv


from . import (
    CONF_PRIORITY,
    RESERVED_DELIVERY_NAMES,
)
from .notification import Notification
from .configuration import SupernotificationConfiguration

_LOGGER = logging.getLogger(__name__)


class DeliveryMethod:
    @abstractmethod
    def __init__(self,
                 hass: HomeAssistant,
                 context: SupernotificationConfiguration,
                 deliveries: dict):
        self.hass = hass
        self.context = context
        self.default_delivery = None
        self.method_deliveries = {d: dc for d, dc in deliveries.items(
        ) if dc.get(CONF_METHOD) == self.method} if deliveries else {}

    async def initialize(self):
        assert self.method is not None
        self.valid_deliveries = await self.validate_deliveries()

    def validate_service(self, service):
        ''' Override in subclass if delivery method has fixed service or doesn't require one'''
        return service is not None and service.startswith("notify.")

    async def validate_deliveries(self):
        """
        Validate list of deliveries at startup for this method

        Args:
            deliveries (dict): Dict of delivery name -> delivery configuration
        """
        valid_deliveries = {}
        for d, dc in self.method_deliveries.items():
            # don't care about ENABLED here since disabled deliveries can be overridden
            if d in RESERVED_DELIVERY_NAMES:
                _LOGGER.warning(
                    "SUPERNOTIFY Delivery uses reserved word %s", d)
                continue
            if not self.validate_service(dc.get(CONF_SERVICE)):
                _LOGGER.warning(
                    "SUPERNOTIFY Invalid service definition for delivery %s (%s)", d, dc.get(CONF_SERVICE))
                continue
            delivery_condition = dc.get(CONF_CONDITION)
            if delivery_condition:
                if not await condition.async_validate_condition_config(self.hass, delivery_condition):
                    _LOGGER.warning(
                        "SUPERNOTIFY Invalid delivery condition for %s: %s", d, delivery_condition)
                    continue

            valid_deliveries[d] = dc
            dc[CONF_NAME] = d

            if dc.get(CONF_DEFAULT):
                if self.default_delivery:
                    _LOGGER.warning(
                        "SUPERNOTIFY Multiple default deliveries, skipping %s", d)
                else:
                    self.default_delivery = dc

        if not self.default_delivery:
            method_definition = self.context.method_defaults.get(self.method)
            if method_definition:
                _LOGGER.info(
                    "SUPERNOTIFY Building default delivery for %s from method %s", self.method, method_definition)
                self.default_delivery = method_definition

        return valid_deliveries

    async def deliver(self,
                      notification: Notification,
                      delivery: str = None) -> bool:
        """
        Deliver a notification

        Args:
            message (_type_, optional): Message to send. Defaults to None, e.g for methods like chime 
            delivery_config (_type_, optional): Delivery Configuration. Defaults to None.
        """
        delivery_config = self.context.deliveries.get(
            delivery) or self.default_delivery or {}
        data = notification.delivery_data(delivery_config.get(CONF_NAME))

        delivery_priorities = delivery_config.get(CONF_PRIORITY) or ()
        if notification.priority and delivery_priorities and notification.priority not in delivery_priorities:
            _LOGGER.debug(
                "SUPERNOTIFY Skipping delivery for %s based on priority (%s)", self.method, notification.priority)
            return False
        if not await self.evaluate_delivery_conditions(delivery_config):
            _LOGGER.debug(
                "SUPERNOTIFY Skipping delivery for %s based on conditions", self.method)
            return False

        target_bundles = notification.build_targets(delivery_config, self)
        deliveries = 0
        for targets, custom_data in target_bundles:
            if custom_data:
                target_data = copy.deepcopy(data) if data else {}
                target_data |= custom_data
            else:
                target_data = data
            success = await self._delivery_impl(notification,
                                                delivery,
                                                targets=targets,
                                                data=target_data)
            if success:
                deliveries += 1
        return deliveries > 0

    @abstractmethod
    async def _delivery_impl(message=None, title=None,
                             targets=None, priority=None,
                             scenarios=None, data=None, config=None) -> bool:
        return False

    def select_target(self, target):
        ''' Confirm if target appropriate for this delivery method '''
        return True

    def recipient_target(self, recipient):
        ''' Pick out delivery appropriate target from a person (recipient) config'''
        return []

    async def evaluate_delivery_conditions(self, delivery_config):
        if CONF_CONDITION not in delivery_config:
            return True
        else:
            try:
                conditions = cv.CONDITION_SCHEMA(
                    delivery_config.get(CONF_CONDITION))
                test = await condition.async_from_config(self.hass, conditions)
                return test(self.hass)
            except Exception as e:
                _LOGGER.error("SUPERNOTIFY Condition eval failed: %s", e)
                raise

    async def call_service(self, qualified_service, service_data={}):
        try:
            domain, service = qualified_service.split(".", 1)
            await self.hass.services.async_call(
                domain, service,
                service_data=service_data)
            return True
        except Exception as e:
            _LOGGER.error(
                "SUPERNOTIFY Failed to notify via %s: %s", self.method, e)
            
    def abs_url(self, fragment):
        if fragment:
            if fragment.startswith("http"):
                return fragment
            elif fragment.startswith("/"):
                return self.context.hass_url + fragment
            else:
                return self.context.hass_url + "/" + fragment
