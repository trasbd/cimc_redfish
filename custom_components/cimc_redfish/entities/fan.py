from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import REVOLUTIONS_PER_MINUTE
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from ..helpers import normalize_name  # pyright: ignore[reportMissingImports]


class CimcFanSensor(CoordinatorEntity, SensorEntity):
    """A single CIMC fan RPM sensor."""

    _attr_native_unit_of_measurement = REVOLUTIONS_PER_MINUTE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator,
        entry_id: str,
        device: dict[str, Any],
        fan: dict[str, Any],
    ) -> None:
        """Initialize the sensor with device metadata and a fan descriptor."""
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._host = device.get("host")
        self._device = device
        self._fan_id = str(fan.get("member_id") or fan.get("name"))
        self._odata = fan.get("odata_id")
        base_name = normalize_name(fan.get("name") or f"Fan {self._fan_id}")
        self._attr_name = f"CIMC {self._host} {base_name}"
        # unique: host + odata id (if available) + member id fallback
        unique = f"{self._host}:{self._odata or self._fan_id}"
        self._attr_unique_id = unique.replace("/", "_")

    @property
    def device_info(self) -> DeviceInfo:
        """Return the parent device information for registry grouping."""
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
        """Return the current RPM for this fan, or None if unavailable."""
        fans = self.coordinator.data.get("fans", []) or []
        for f in fans:
            fid = str(f.get("member_id") or f.get("name"))
            if fid == self._fan_id:
                return f.get("rpm")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional telemetry and thresholds for this fan."""
        fans = self.coordinator.data.get("fans", []) or []
        for f in fans:
            fid = str(f.get("member_id") or f.get("name"))
            if fid == self._fan_id:
                return {
                    "name": f.get("name"),
                    "state": f.get("state"),
                    "health": f.get("health"),
                    "context": f.get("context"),
                    "lower_noncrit": f.get("lower_noncrit"),
                    "lower_crit": f.get("lower_crit"),
                    "upper_noncrit": f.get("upper_noncrit"),
                    "upper_crit": f.get("upper_crit"),
                    "odata_id": f.get("odata_id"),
                }
        return {}
