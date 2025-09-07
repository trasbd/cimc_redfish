"""Config flow for Cisco CIMC Redfish integration.

Defines the UI flow for adding the integration and setting options like
polling interval. Validates connectivity to the CIMC Redfish endpoint
during setup.
"""

from __future__ import annotations

import contextlib
import logging

import requests
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_TLS_MIN,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TLS_MIN,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)
from .coordinator import CimcRedfishClient

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
        vol.Optional(CONF_TLS_MIN, default=DEFAULT_TLS_MIN): vol.In(
            ["1.0", "1.1", "1.2"]
        ),
    }
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            int, vol.Range(min=5, max=3600)
        ),
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial CIMC Redfish config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Prompt for host/credentials, validate them, and create an entry."""
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=USER_SCHEMA)

        host = user_input[CONF_HOST]
        await self.async_set_unique_id(host)
        self._abort_if_unique_id_configured()

        ok, err = await self._async_validate(self.hass, user_input)
        if not ok:
            return self.async_show_form(
                step_id="user",
                data_schema=USER_SCHEMA,
                errors={"base": err or "cannot_connect"},
            )

        return self.async_create_entry(title=f"CIMC {host}", data=user_input)

    async def _async_validate(
        self, hass: HomeAssistant, data: dict
    ) -> tuple[bool, str | None]:
        """Validate credentials and connectivity to CIMC Redfish."""
        client = CimcRedfishClient(
            host=data[CONF_HOST],
            username=data[CONF_USERNAME],
            password=data[CONF_PASSWORD],
            verify_ssl=data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
            tls_min=data.get(CONF_TLS_MIN, DEFAULT_TLS_MIN),
        )
        try:
            res = await hass.async_add_executor_job(client.fetch_fans)
            if not isinstance(res, dict) or "fans" not in res:
                _LOGGER.debug("Unexpected response during validation: %r", res)
                return False, "cannot_connect"
            return True, None  # noqa: TRY300

        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else None
            body = ""
            with contextlib.suppress(Exception):
                body = e.response.text[:300] if e.response is not None else ""
            _LOGGER.warning(
                "HTTP error talking to CIMC: %s %s | body=%r", code, e, body
            )

            if code == 401:
                return False, "invalid_auth"
            if code in (403,):
                return False, "forbidden"
            if code in (404, 405):
                # Likely no Redfish on this firmware/box
                return False, "not_supported"
            return False, "cannot_connect"

        except requests.exceptions.SSLError as e:
            _LOGGER.warning("TLS/SSL error talking to CIMC: %s", e)
            return False, "ssl_error"

        except requests.exceptions.ConnectTimeout as e:
            _LOGGER.warning("Timeout talking to CIMC: %s", e)
            return False, "timeout"

        except requests.exceptions.ConnectionError as e:
            _LOGGER.warning("Connection error to CIMC: %s", e)
            return False, "cannot_connect"

        except Exception:
            _LOGGER.exception("Unexpected error during CIMC validation")
            return False, "unknown"

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return the options flow handler for this integration."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle CIMC Redfish options (e.g. polling interval)."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow with existing entry."""
        self._entry = entry

    async def async_step_init(self, user_input=None):
        """Show options form and save updated settings."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self._entry.options
        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): vol.All(int, vol.Range(min=5, max=3600))
            }
        )
        return self.async_show_form(step_id="init", data_schema=data_schema)
