"""Config flow for ZKAccess C3."""

from __future__ import annotations

import contextlib
import logging
from typing import Any

import voluptuous as vol
from c3 import C3
from c3.consts import C3_PORT_DEFAULT

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_AUX_ON_DURATION,
    CONF_UNLOCK_DURATION,
    DEFAULT_AUX_ON_DURATION,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_UNLOCK_DURATION,
    DOMAIN,
    MAX_OUTPUT_DURATION,
    MAX_POLL_INTERVAL,
    MIN_OUTPUT_DURATION,
    MIN_POLL_INTERVAL,
)
from .coordinator import _no_c3_debug_logging

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=C3_PORT_DEFAULT): cv.port,
        vol.Optional(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
        vol.Optional(CONF_NAME): cv.string,
    }
)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidPassword(HomeAssistantError):
    """Error to indicate the password cannot be used by the panel protocol."""


def _probe_panel(host: str, port: int, password: str) -> str | None:
    """Connect to the panel, return its serial number and close the session."""
    if not password.isascii():
        raise InvalidPassword
    panel = C3(host, port)
    try:
        with _no_c3_debug_logging():
            if not panel.connect(password):
                raise CannotConnect
        return panel.serial_number
    except (OSError, ValueError) as err:
        raise CannotConnect from err
    finally:
        with contextlib.suppress(Exception):
            panel.disconnect()


def _number(minimum: int, maximum: int) -> vol.All:
    return vol.All(
        NumberSelector(
            NumberSelectorConfig(
                min=minimum,
                max=maximum,
                step=1,
                mode=NumberSelectorMode.BOX,
                unit_of_measurement="s",
            )
        ),
        vol.Coerce(int),
        vol.Range(min=minimum, max=maximum),
    )


class C3OptionsFlow(OptionsFlow):
    """Handle configuration options for the C3 panel."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=options.get(CONF_SCAN_INTERVAL, DEFAULT_POLL_INTERVAL),
                    ): _number(MIN_POLL_INTERVAL, MAX_POLL_INTERVAL),
                    vol.Optional(
                        CONF_UNLOCK_DURATION,
                        default=options.get(
                            CONF_UNLOCK_DURATION, DEFAULT_UNLOCK_DURATION
                        ),
                    ): _number(MIN_OUTPUT_DURATION, MAX_OUTPUT_DURATION),
                    vol.Optional(
                        CONF_AUX_ON_DURATION,
                        default=options.get(
                            CONF_AUX_ON_DURATION, DEFAULT_AUX_ON_DURATION
                        ),
                    ): _number(MIN_OUTPUT_DURATION, MAX_OUTPUT_DURATION),
                }
            ),
        )


class C3ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for C3."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> C3OptionsFlow:
        """Get the options flow."""
        return C3OptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host: str = user_input[CONF_HOST].strip()
            port: int = user_input.get(CONF_PORT, C3_PORT_DEFAULT)
            password: str = user_input.get(CONF_PASSWORD) or ""
            self._async_abort_entries_match({CONF_HOST: host, CONF_PORT: port})
            try:
                serial = await self.hass.async_add_executor_job(
                    _probe_panel, host, port, password
                )
            except InvalidPassword:
                errors[CONF_PASSWORD] = "invalid_password"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                if serial:
                    await self.async_set_unique_id(serial)
                    self._abort_if_unique_id_configured(
                        updates={CONF_HOST: host, CONF_PORT: port}
                    )
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME) or "ZKAccess C3",
                    data={CONF_HOST: host, CONF_PORT: port, CONF_PASSWORD: password},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA,
                {k: v for k, v in (user_input or {}).items() if k != CONF_PASSWORD},
            ),
            errors=errors,
        )
