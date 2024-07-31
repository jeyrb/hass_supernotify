"""Config flow for SuperNotify integration."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import voluptuous as vol
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaCommonFlowHandler,
    SchemaConfigFlowHandler,
    SchemaFlowError,
    SchemaFlowFormStep,
)
from homeassistant.helpers.typing import UNDEFINED

from custom_components.supernotify import (
    CONF_ARCHIVE_PATH,
    CONF_MEDIA_PATH,
    CONF_TEMPLATE_PATH,
    DOMAIN,
    MEDIA_DIR,
    TEMPLATE_DIR,
)

PATH_SCHEMA = vol.Schema({
    vol.Required(CONF_TEMPLATE_PATH, default=cast(str, TEMPLATE_DIR)): str,
    vol.Required(CONF_MEDIA_PATH, default=cast(str, MEDIA_DIR)): str,
    vol.Optional(CONF_ARCHIVE_PATH): str,
})


async def validate_paths(handler: SchemaCommonFlowHandler, user_input: dict[str, Any]) -> dict[str, Any]:  # noqa: ARG001
    """Validate the provided paths."""
    for key in PATH_SCHEMA.schema:
        path = user_input.get(key.schema)
        if not path and isinstance(key, vol.Required):
            raise SchemaFlowError(f"{key.schema} is required")
        if path and not Path(path).exists():
            try:
                Path(path).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise SchemaFlowError(f"Unable to create directory {path} with error {e}") from e
    return user_input


CONFIG_FLOW: dict[str, SchemaFlowFormStep] = {"user": SchemaFlowFormStep(PATH_SCHEMA, validate_paths, None, UNDEFINED, None)}

OPTIONS_FLOW: dict[str, SchemaFlowFormStep] = {}


class SupernotifyConfigFlowHandler(SchemaConfigFlowHandler, domain=DOMAIN):
    """Handle a config flow for Scrape."""

    config_flow = CONFIG_FLOW
    options_flow = OPTIONS_FLOW

    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        """Return config entry title."""
        return cast(str, options["name"]) if "name" in options else ""
