"""Home Assistant platform setup for Cisco CIMC Redfish sensors.

This module wires the integration's coordinator data into entity classes
so they can be registered with Home Assistant. It supports:

- Fan RPM sensors (from Thermal.Fans[]).
- Power supply sensors:
  * Voltage sensors (if PSU exposes a voltage reading).
  * Power sensors (if PSU exposes last power output).
- Temperature sensors (from Thermal.Temperatures[]).

Entities are constructed from the coordinator's cached telemetry and
registered during config entry setup.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entities.fan import CimcFanSensor
from .entities.psu import CimcPsuPowerSensor, CimcPsuVoltageSensor
from .entities.temperature import CimcTemperatureSensor


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from the integration’s coordinator data."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    device: dict[str, Any] = coordinator.data.get("device", {}) or {}

    entities: list[SensorEntity] = []

    # Fans
    fans = [
        CimcFanSensor(coordinator, entry.entry_id, device, f)
        for f in (coordinator.data.get("fans") or [])
    ]

    # PSUs (voltage + power if present)
    psus = [
        sensor
        for psu in (coordinator.data.get("psus") or [])
        for sensor in (
            [CimcPsuVoltageSensor(coordinator, entry.entry_id, device, psu)]
            if psu.get("voltage") is not None
            else []
        ) + (
            [CimcPsuPowerSensor(coordinator, entry.entry_id, device, psu)]
            if psu.get("last_power") is not None
            else []
        )
    ]

    # Temperatures
    temps = [
        CimcTemperatureSensor(coordinator, entry.entry_id, device, t)
        for t in (coordinator.data.get("temperatures") or [])
    ]

    entities: list[SensorEntity] = fans + psus + temps
    if entities:
        async_add_entities(entities)
