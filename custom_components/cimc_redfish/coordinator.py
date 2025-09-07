"""Legacy-TLS session adapter and minimal Redfish client for Cisco CIMC.

This module provides:
- `_LegacyTLSAdapter`: a `requests` adapter that relaxes OpenSSL 3 defaults so
  we can talk to older CIMC images (weak ciphers / TLS <= 1.2).
- `CimcRedfishClient`: a very small synchronous Redfish client used by the
  coordinator to fetch fan telemetry and basic device info.
"""

from contextlib import suppress
import ssl
from typing import Any

import requests
from requests.adapters import HTTPAdapter
import urllib3
from urllib3.exceptions import InsecureRequestWarning


class _LegacyTLSAdapter(HTTPAdapter):
    """Allow legacy TLS and weaker ciphers for older CIMC builds."""

    def __init__(self, verify_ssl: bool, tls_min: str, *args, **kwargs)->None:
        # Set fields BEFORE calling super().__init__(), because that calls init_poolmanager().
        self._verify_ssl = verify_ssl
        self._tls_min = tls_min
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.minimum_version = {
            "1.0": ssl.TLSVersion.TLSv1,
            "1.1": ssl.TLSVersion.TLSv1_1,
            "1.2": ssl.TLSVersion.TLSv1_2,
        }.get(self._tls_min, ssl.TLSVersion.TLSv1)



        # Relax OpenSSL 3 defaults for legacy servers
        with suppress(ssl.SSLError, ValueError):  # some builds raise ValueError here
            ctx.set_ciphers("DEFAULT:@SECLEVEL=1")

        flag = getattr(ssl, "OP_LEGACY_SERVER_CONNECT", 0)
        if flag:
            ctx.options |= flag

        if not self._verify_ssl:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE


        pool_kwargs["ssl_context"] = ctx
        return super().init_poolmanager(connections, maxsize, block=block, **pool_kwargs)

class CimcRedfishClient:
    """Very small Redfish client, synchronous (used via executor)."""

    def __init__(self, host: str, username: str, password: str, verify_ssl: bool, tls_min: str) -> None:
        """Initialize client with endpoint, credentials, and TLS/verify options."""
        self.base = f"https://{host}"
        self.auth = (username, password)
        self.verify = verify_ssl
        self.tls_min = tls_min
        self._session: requests.Session | None = None
        self._chassis_path: str | None = None
        self._host = host

        if not self.verify:
            # Hide “Unverified HTTPS request …” only for this process
            urllib3.disable_warnings(InsecureRequestWarning)

    def _session_obj(self) -> requests.Session:
        if self._session is None:
            s = requests.Session()
            s.mount("https://", _LegacyTLSAdapter(self.verify, self.tls_min))
            self._session = s
        return self._session

    def _pick_chassis(self) -> str:
        s = self._session_obj()
        r = s.get(f"{self.base}/redfish/v1/Chassis", auth=self.auth, verify=self.verify, timeout=10)
        r.raise_for_status()
        members = r.json().get("Members") or []
        if not members:
            raise RuntimeError("No Redfish chassis members found.")
        return members[0]["@odata.id"]  # e.g. "/redfish/v1/Chassis/1"

    def _ensure_chassis(self) -> str:
        if not self._chassis_path:
            self._chassis_path = self._pick_chassis()
        return self._chassis_path

    def _fetch_if_link(self, item: Any) -> dict[str, Any]:
        # If Thermal.Fans contains links (dicts with @odata.id only), fetch them
        if isinstance(item, dict) and ("Reading" in item or "ReadingRPM" in item or "Status" in item):
            return item
        if isinstance(item, dict):
            oid = item.get("@odata.id")
            if oid:
                s = self._session_obj()
                r = s.get(f"{self.base}{oid}", auth=self.auth, verify=self.verify, timeout=10)
                r.raise_for_status()
                return r.json()
        return item if isinstance(item, dict) else {}

    @staticmethod
    def _num(v):
        if v in (None, "", "N/A"):
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            try:
                return float(v)
            except (ValueError, TypeError):
                return None

    def fetch_temperatures(self) -> list[dict[str, Any]]:
        """Return temperature sensors."""
        chassis_path = self._ensure_chassis()
        s = self._session_obj()

        r = s.get(f"{self.base}{chassis_path}/Thermal", auth=self.auth, verify=self.verify, timeout=10)
        r.raise_for_status()
        thermal = r.json()

        temps_raw = thermal.get("Temperatures") or []
        temps_objs = [self._fetch_if_link(it) for it in temps_raw]

        temps: list[dict[str, Any]] = []
        for t in temps_objs:
            status = t.get("Status") or {}
            mid = t.get("MemberID")
            try:
                member_id = int(mid) if mid is not None else None
            except (TypeError, ValueError):
                member_id = mid

            temps.append({
                "name": t.get("Name") or f"Temp {member_id}",
                "context": t.get("PhysicalContext"),
                "member_id": member_id,
                "celsius": self._num(t.get("ReadingCelsius")),
                "state": status.get("State"),
                "health": status.get("Health"),
                "lower_noncrit": self._num(t.get("LowerThresholdNonCritical")),
                "lower_crit": self._num(t.get("LowerThresholdCritical")),
                "upper_noncrit": self._num(t.get("UpperThresholdNonCritical")),
                "upper_crit": self._num(t.get("UpperThresholdCritical")),
                "sensor_number": self._num(t.get("SensorNumber")),
                "odata_id": t.get("@odata.id"),
            })
        return temps


    # coordinator.py — inside CimcRedfishClient
    def fetch_power(self) -> dict[str, Any]:
        """Return overall power, PSUs (power+voltage), and voltage rails."""
        chassis_path = self._ensure_chassis()
        s = self._session_obj()
        r = s.get(f"{self.base}{chassis_path}/Power", auth=self.auth, verify=self.verify, timeout=10)
        r.raise_for_status()
        pw = r.json() or {}

        # Overall power + metrics
        pc = pw.get("PowerControl") or {}
        consumed = self._num(pc.get("PowerConsumedWatts"))
        pm = pc.get("PowerMetric") or {}
        power = {
            "consumed_watts": self._num(consumed),
            "min_watts": self._num(pm.get("MinConsumedWatts")),
            "avg_watts": self._num(pm.get("AverageConsumedWatts")),
            "max_watts": self._num(pm.get("MaxConsumedWatts")),
            "interval_min": self._num(pm.get("IntervalInMin")),
        }

        # Voltages rails
        rails_raw = pw.get("Voltages") or []
        rails: list[dict[str, Any]] = []
        for v in rails_raw:
            status = v.get("Status") or {}
            mid = v.get("MemberID")
            try:
                member_id = int(mid) if mid is not None else None
            except (TypeError, ValueError):
                member_id = mid
            rails.append({
                "member_id": member_id,
                "name": v.get("Name"),
                "context": v.get("PhysicalContext"),
                "volts": self._num(v.get("ReadingVolts")),
                "lower_noncrit": self._num(v.get("LowerThresholdNonCritical")),
                "lower_crit": self._num(v.get("LowerThresholdCritical")),
                "upper_noncrit": self._num(v.get("UpperThresholdNonCritical")),
                "upper_crit": self._num(v.get("UpperThresholdCritical")),
                "state": status.get("State") or status.get("state"),
                "health": status.get("Health") or status.get("health"),
                "sensor_number": self._num(v.get("SensorNumber")),
                "odata_id": v.get("@odata.id"),
            })

        # PSUs + stitch matched rail voltage by MemberID where PhysicalContext == PowerSupply
        psus_raw = pw.get("PowerSupplies") or []
        rails_by_mid = {str(r["member_id"]): r for r in rails if r.get("context") == "PowerSupply" and r.get("member_id") is not None}
        psus: list[dict[str, Any]] = []
        for psu in psus_raw:
            mid = psu.get("MemberID")
            try:
                member_id = int(mid) if mid is not None else None
            except (TypeError, ValueError):
                member_id = mid
            status = psu.get("Status") or {}
            rail = rails_by_mid.get(str(member_id), {})
            psus.append({
                "member_id": member_id,
                "name": psu.get("Name") or f"PSU {member_id}",
                "state": (status.get("State") or status.get("state")),
                "last_power": self._num(psu.get("LastPowerOutputWatts")),
                "line_input_volts": self._num(psu.get("LineInputVoltage")),
                "serial": psu.get("SerialNumber"),
                "model": psu.get("Model"),
                "part_number": psu.get("PartNumber"),
                "spare_part_number": psu.get("SparePartNumber"),
                "odata_id": psu.get("@odata.id"),
                "voltage": rail.get("volts"),
                "voltage_odata_id": rail.get("odata_id"),
            })

        return {"power": power, "psus": psus, "voltages": rails}

    def fetch_all(self) -> dict[str, Any]:
        out = self.fetch_fans()
        with suppress(Exception):
            out.update(self.fetch_power())
        with suppress(Exception):
            out["temperatures"] = self.fetch_temperatures()
        return out



    def fetch_fans(self) -> dict[str, Any]:
        """Return a dict with fan list and device info."""
        chassis_path = self._ensure_chassis()
        s = self._session_obj()

        # Fetch Thermal
        r = s.get(f"{self.base}{chassis_path}/Thermal", auth=self.auth, verify=self.verify, timeout=10)
        r.raise_for_status()
        thermal = r.json()

        fans_raw = thermal.get("Fans") or []
        fans_objs = [self._fetch_if_link(it) for it in fans_raw]

        fans: list[dict[str, Any]] = []
        for f in fans_objs:
            status = f.get("Status") or {}
            rpm_val = f.get("Reading") or f.get("ReadingRPM")
            rpm = self._num(rpm_val)
            if rpm is None:
                rpm = rpm_val

            mid = f.get("MemberID")
            try:
                member_id = int(mid) if mid is not None else None
            except (TypeError, ValueError):
                member_id = mid

            fans.append({
                "name": f.get("Name") or f.get("FanName") or "Fan",
                "context": f.get("PhysicalContext"),
                "member_id": member_id,
                "rpm": rpm,
                "units": f.get("ReadingUnits") or ("RPM" if f.get("ReadingRPM") is not None else ""),
                "state": status.get("State"),
                "health": status.get("Health"),
                "lower_noncrit": self._num(f.get("LowerThresholdNonCritical")),
                "lower_crit": self._num(f.get("LowerThresholdCritical")),
                "upper_noncrit": self._num(f.get("UpperThresholdNonCritical")),
                "upper_crit": self._num(f.get("UpperThresholdCritical")),
                "odata_id": f.get("@odata.id"),
            })

        # Try to grab some basic device info from chassis
        try:
            rc = s.get(f"{self.base}{chassis_path}", auth=self.auth, verify=self.verify, timeout=10)
            rc.raise_for_status()
            chassis = rc.json()
            vendor = chassis.get("Manufacturer") or "Cisco"
            model = chassis.get("Model") or "C-Series"
            serial = chassis.get("SerialNumber")
        except (requests.RequestException, ValueError, KeyError, TypeError):
            # Narrow exceptions instead of a blind 'except Exception'
            vendor = "Cisco"
            model = "C-Series"
            serial = None

        return {
            "fans": fans,
            "device": {
                "host": self._host,
                "manufacturer": vendor,
                "model": model,
                "serial": serial,
                "ident": f"{self._host}",
            }
        }
