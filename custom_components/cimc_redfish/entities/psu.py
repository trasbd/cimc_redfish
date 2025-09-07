from __future__ import annotations
from typing import Any
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfElectricPotential, UnitOfPower
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from ..const import DOMAIN
from ..helpers import normalize_name  # pyright: ignore[reportMissingImports]


def _psu_base(device: dict[str, Any], psu: dict[str, Any]) -> tuple[str, str, str]:
    host = device.get("host")
    name = psu.get("name") or f"PSU {psu.get('member_id')}"
    uid_base = (psu.get("odata_id") or f"psu:{psu.get('member_id') or name}").replace("/", "_")
    return host, name, uid_base


class _CimcPsuBase(CoordinatorEntity, SensorEntity):
    """Shared DeviceInfo for PSU sensors."""

    def __init__(self, coordinator, device: dict[str, Any]) -> None:
        super().__init__(coordinator)
        self._device = device
        self._host = device.get("host")

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


class CimcPsuVoltageSensor(_CimcPsuBase):
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry_id: str, device: dict[str, Any], psu: dict[str, Any]) -> None:
        super().__init__(coordinator, device)
        self._id = str(psu.get("member_id") or psu.get("name"))
        host, name, uid = _psu_base(device, psu)
        name = normalize_name(name)
        self._attr_name = f"{name} Voltage"
        self._attr_unique_id = f"{host}:{uid}:voltage"

    @property
    def native_value(self):
        for p in self.coordinator.data.get("psus", []) or []:
            if str(p.get("member_id") or p.get("name")) == self._id:
                return p.get("voltage")
        return None

    @property
    def extra_state_attributes(self):
        # Stitch attributes from PSU row + the matched rail thresholds
        for p in self.coordinator.data.get("psus", []) or []:
            if str(p.get("member_id") or p.get("name")) == self._id:
                # Find the matched rail record by odata_id, if present
                rail_oid = p.get("voltage_odata_id")
                rail = None
                for r in self.coordinator.data.get("voltages", []) or []:
                    if r.get("odata_id") == rail_oid or str(r.get("member_id")) == str(p.get("member_id")):
                        rail = r
                        break

                attrs = {
                    "state": p.get("state"),
                    "serial": p.get("serial"),
                    "model": p.get("model"),
                    "psu_odata_id": p.get("odata_id"),
                    "rail_odata_id": p.get("voltage_odata_id"),
                    "line_input_volts": p.get("line_input_volts"),
                }
                if rail:
                    attrs.update({
                        "context": rail.get("context"),
                        "sensor_number": rail.get("sensor_number"),
                        "lower_noncrit": rail.get("lower_noncrit"),
                        "lower_crit": rail.get("lower_crit"),
                        "upper_noncrit": rail.get("upper_noncrit"),
                        "upper_crit": rail.get("upper_crit"),
                        "rail_name": rail.get("name"),
                    })
                return attrs
        return {}


class CimcPsuPowerSensor(_CimcPsuBase):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry_id: str, device: dict[str, Any], psu: dict[str, Any]) -> None:
        super().__init__(coordinator, device)
        self._id = str(psu.get("member_id") or psu.get("name"))
        host, name, uid = _psu_base(device, psu)
        name = normalize_name(name)
        self._attr_name = f"{name} Power"
        self._attr_unique_id = f"{host}:{uid}:power"

    @property
    def native_value(self):
        for p in self.coordinator.data.get("psus", []) or []:
            if str(p.get("member_id") or p.get("name")) == self._id:
                # From PowerSupplies[].LastPowerOutputWatts
                return p.get("last_power")
        return None

    @property
    def extra_state_attributes(self):
        """Include overall PowerMetric (min/avg/max/interval) as convenience attributes."""
        power = self.coordinator.data.get("power") or {}
        for p in self.coordinator.data.get("psus", []) or []:
            if str(p.get("member_id") or p.get("name")) == self._id:
                return {
                    "state": p.get("state"),
                    "line_input_volts": p.get("line_input_volts"),
                    "serial": p.get("serial"),
                    "model": p.get("model"),
                    "psu_odata_id": p.get("odata_id"),
                    # Overall metrics from PowerControl.PowerMetric
                    "power_consumed_watts": power.get("consumed_watts"),
                    "power_min_watts": power.get("min_watts"),
                    "power_avg_watts": power.get("avg_watts"),
                    "power_max_watts": power.get("max_watts"),
                    "power_interval_min": power.get("interval_min"),
                }
        return {}
