import logging
import time
from abc import abstractmethod
from traceback import format_exception

from homeassistant.components.notify import ATTR_TARGET
from homeassistant.const import (CONF_CONDITION, CONF_DEFAULT, CONF_METHOD,
                                 CONF_NAME, CONF_SERVICE)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import condition
from homeassistant.helpers import config_validation as cv

from . import CONF_OPTIONS, CONF_TARGETS_REQUIRED, RESERVED_DELIVERY_NAMES
from .configuration import SupernotificationConfiguration
from .notification import Envelope

_LOGGER = logging.getLogger(__name__)


class DeliveryMethod:
    method = None
    default_service = None

    @abstractmethod
    def __init__(self, hass: HomeAssistant, context: SupernotificationConfiguration, deliveries: dict = None):
        self.hass = hass
        self.context = context
        self.default_delivery = None
        self.method_deliveries = (
            {d: dc for d, dc in deliveries.items() if dc.get(CONF_METHOD) == self.method} if deliveries else {}
        )

    async def initialize(self):
        """
        Async post-construction initialization
        """
        assert self.method is not None
        self.valid_deliveries = await self.validate_deliveries()

    def validate_service(self, service):
        """Override in subclass if delivery method has fixed service or doesn't require one"""
        return service is not None and service.startswith("notify.")

    async def validate_deliveries(self):
        """
        Validate list of deliveries at startup for this method
        """
        valid_deliveries = {}
        for d, dc in self.method_deliveries.items():
            # don't care about ENABLED here since disabled deliveries can be overridden
            if d in RESERVED_DELIVERY_NAMES:
                _LOGGER.warning("SUPERNOTIFY Delivery uses reserved word %s", d)
                continue
            if not self.validate_service(dc.get(CONF_SERVICE)):
                _LOGGER.warning("SUPERNOTIFY Invalid service definition for delivery %s (%s)", d, dc.get(CONF_SERVICE))
                continue
            delivery_condition = dc.get(CONF_CONDITION)
            if delivery_condition:
                if not await condition.async_validate_condition_config(self.hass, delivery_condition):
                    _LOGGER.warning("SUPERNOTIFY Invalid delivery condition for %s: %s", d, delivery_condition)
                    continue

            valid_deliveries[d] = dc
            dc[CONF_NAME] = d

            if dc.get(CONF_DEFAULT):
                if self.default_delivery:
                    _LOGGER.warning("SUPERNOTIFY Multiple default deliveries, skipping %s", d)
                else:
                    self.default_delivery = dc

        if not self.default_delivery:
            method_definition = self.context.method_defaults.get(self.method)
            if method_definition:
                _LOGGER.info("SUPERNOTIFY Building default delivery for %s from method %s", self.method, method_definition)
                self.default_delivery = method_definition

        if self.default_service is None and self.default_delivery:
            self.default_service = self.default_delivery.get(CONF_SERVICE)

        _LOGGER.debug(
            "SUPERNOTIFY Validated method %s, default delivery %s, default services %s, valid deliveries: %s",
            self.method,
            self.default_delivery,
            self.default_service,
            valid_deliveries,
        )
        return valid_deliveries

    @abstractmethod
    async def deliver(self, envelope: Envelope) -> None:
        """
        Delivery implementation

        Args:
            envelope (Envelope): envelope to be delivered
        """
        pass

    def select_target(self, target: str):
        """Confirm if target appropriate for this delivery method

        Args:
            target (str): Target, typically an entity ID, or an email address, phone number
        """
        return True

    def recipient_target(self, recipient: str) -> list:
        """Pick out delivery appropriate target from a person (recipient) config"""
        return []

    def delivery_config(self, delivery_name):
        return self.context.deliveries.get(delivery_name) or self.default_delivery or {}

    def combined_message(self, envelope, default_title_only=True):
        config = self.delivery_config(envelope.delivery_name)
        if config.get(CONF_OPTIONS, {}).get("title_only", default_title_only) and envelope.title:
            return envelope.title
        else:
            if envelope.title:
                return "{} {}".format(envelope.title, envelope.message)
            else:
                return envelope.message

    def set_service_data(self, service_data, key, data):
        if data is not None:
            service_data[key] = data
        return service_data

    async def evaluate_delivery_conditions(self, delivery_config):
        if CONF_CONDITION not in delivery_config:
            return True
        else:
            try:
                conditions = cv.CONDITION_SCHEMA(delivery_config.get(CONF_CONDITION))
                test = await condition.async_from_config(self.hass, conditions)
                return test(self.hass)
            except Exception as e:
                _LOGGER.error("SUPERNOTIFY Condition eval failed: %s", e)
                raise

    async def call_service(self, envelope, qualified_service=None, service_data=None) -> bool:
        service_data = service_data or {}
        config = self.delivery_config(envelope.delivery_name)
        try:
            qualified_service = qualified_service or config.get(CONF_SERVICE) or self.default_service
            if qualified_service and (service_data.get(ATTR_TARGET) or not config.get(CONF_TARGETS_REQUIRED, False)):
                domain, service = qualified_service.split(".", 1)
                start_time = time.time()
                await self.hass.services.async_call(domain, service, service_data=service_data)
                envelope.calls.append((domain, service, service_data, time.time() - start_time))
                envelope.delivered = 1
            else:
                _LOGGER.debug(
                    "SUPERNOTIFY skipping service call for service %s, targets %s",
                    qualified_service,
                    service_data.get(ATTR_TARGET),
                )
                envelope.skipped = 1
            return True
        except Exception as e:
            envelope.failed_calls.append((domain, service, service_data, str(e), time.time() - start_time))
            _LOGGER.error("SUPERNOTIFY Failed to notify via %s, data=%s : %s", self.method, service_data, e)
            envelope.errored += 1
            envelope.delivery_error = format_exception(e)
            return False

    def abs_url(self, fragment, prefer_external=True):
        base_url = self.context.hass_external_url if prefer_external else self.context.hass_internal_url
        if fragment:
            if fragment.startswith("http"):
                return fragment
            elif fragment.startswith("/"):
                return base_url + fragment
            else:
                return base_url + "/" + fragment
