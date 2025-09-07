"""Home Assistant integration setup for Cisco CIMC via Redfish.

This module registers the config entry, creates a DataUpdateCoordinator that
polls telemetry from the CIMC Redfish API, and forwards platforms.
"""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_TLS_MIN,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import CimcRedfishClient

type HassConfigEntry = ConfigEntry


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: HassConfigEntry) -> bool:
    """Set up CIMC Redfish from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    host = entry.data[CONF_HOST]
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    verify_ssl = entry.data.get(CONF_VERIFY_SSL, False)
    tls_min = entry.data.get(CONF_TLS_MIN, "1.0")

    client = CimcRedfishClient(
        host=host,
        username=username,
        password=password,
        verify_ssl=verify_ssl,
        tls_min=tls_min,
    )

    async def _async_update():
        return await hass.async_add_executor_job(client.fetch_all)

    interval = timedelta(
        seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )
    coordinator = DataUpdateCoordinator(
        hass,
        logger=_LOGGER,
        name=f"CIMC Redfish ({host})",
        update_method=_async_update,
        update_interval=interval,
    )

    # Initial fetch to validate connection & seed data
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as exc:
        raise ConfigEntryNotReady(str(exc)) from exc

    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _update_listener(updated_entry: HassConfigEntry):
        # just update the interval; credentials rarely change outside reauth
        coordinator.update_interval = timedelta(
            seconds=updated_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        await coordinator.async_request_refresh()

    entry.async_on_unload(entry.add_update_listener(_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HassConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
