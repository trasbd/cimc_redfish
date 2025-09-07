from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN  # noqa: TID252
from ..helpers import normalize_name  # pyright: ignore[reportMissingImports]


class CimcTemperatureSensor(CoordinatorEntity, SensorEntity):
    """A single CIMC temperature sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, coordinator, entry_id: str, device: dict[str, Any], temp: dict[str, Any]
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._host = device.get("host")
        self._device = device
        self._temp_id = str(temp.get("member_id") or temp.get("name"))
        self._odata = temp.get("odata_id")
        base_name = normalize_name(temp.get("name") or f"Temperature {self._temp_id}")
        self._attr_name = f"CIMC {self._host} {base_name}"
        unique = f"{self._host}:{self._odata or self._temp_id}"
        self._attr_unique_id = unique.replace("/", "_")

    @property
    def device_info(self) -> DeviceInfo:
        ident = (DOMAIN, self._device.get("ident") or self._host)
        return DeviceInfo(
            identifiers={ident},
            name=f"CIMC {self._host}",
            manufacturer=self._device.get("manufacturer") or "Cisco",
            model=self._device.get("model") or "C-Series",
            serial_number=self._device.get("serial"),
        )

    @property
    def native_value(self) -> int | float | None:
        for t in self.coordinator.data.get("temperatures", []) or []:
            tid = str(t.get("member_id") or t.get("name"))
            if tid == self._temp_id:
                return t.get("celsius")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        for t in self.coordinator.data.get("temperatures", []) or []:
            tid = str(t.get("member_id") or t.get("name"))
            if tid == self._temp_id:
                return {
                    "name": t.get("name"),
                    "state": t.get("state"),
                    "health": t.get("health"),
                    "context": t.get("context"),
                    "lower_noncrit": t.get("lower_noncrit"),
                    "lower_crit": t.get("lower_crit"),
                    "upper_noncrit": t.get("upper_noncrit"),
                    "upper_crit": t.get("upper_crit"),
                    "sensor_number": t.get("sensor_number"),
                    "odata_id": t.get("odata_id"),
                }
        return {}
