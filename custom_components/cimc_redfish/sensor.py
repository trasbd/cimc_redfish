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
    for f in coordinator.data.get("fans", []) or []:
        entities.append(CimcFanSensor(coordinator, entry.entry_id, device, f))

    # PSUs (voltage + power if present)
    for psu in coordinator.data.get("psus", []) or []:
        if psu.get("voltage") is not None:
            entities.append(CimcPsuVoltageSensor(coordinator, entry.entry_id, device, psu))
        if psu.get("last_power") is not None:
            entities.append(CimcPsuPowerSensor(coordinator, entry.entry_id, device, psu))

    # Temperatures
    for t in coordinator.data.get("temperatures", []) or []:
        entities.append(CimcTemperatureSensor(coordinator, entry.entry_id, device, t))

    if entities:
        async_add_entities(entities)
