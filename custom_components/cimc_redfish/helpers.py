"""Helper utilities for Cisco CIMC Redfish integration.

Currently provides:
- `normalize_name`: Converts raw Redfish hardware identifiers into
  human-readable display names for use in Home Assistant entities.

These transformations make CIMC telemetry more user-friendly by expanding
common abbreviations (e.g., FAN1 → "Fan 1", PSU2_TEMP → "PSU 2 Temperature"),
removing redundant tokens, and replacing underscores with spaces.
"""

import re


def normalize_name(raw: str | None) -> str:
    """Normalize and humanize CIMC hardware identifiers into a display-friendly name.

    This helper converts raw Redfish object names (e.g., `"FAN1_TACH1"`,
    `"RISER2_OUTLETTMP"`, `"PSU1_TEMP"`) into cleaner strings suitable for
    entity display in Home Assistant.

    Transformations include:
    - Expanding common tokens (`FAN1` → `"Fan 1"`, `RISER2` → `"Riser 2"`, `PSU1` → `"PSU 1"`).
    - Replacing underscores with spaces.
    - Converting technical abbreviations:
      * `TACH` → `"Tach"`,
      * `TEMP`/`TMP` → `"Temperature"`,
      * `FP` → `"Front Panel"`,
      * `PCH` → `"Chipset"`,
      * `OUTLETTMP` → `"Outlet Temperature"`, etc.
    - Removing redundant tokens like `"SENSOR"` and `"SENS"`.

    Args:
        raw: The raw CIMC identifier string, or None.

    Returns:
        A cleaned, human-readable name string (empty string if input is None/empty).
    """
    if not raw:
        return ""

    name = raw

    name = re.sub(r"FAN(\d+)", r"Fan \1", name, flags=re.IGNORECASE)
    name = re.sub(r"RISER(\d+)", r"Riser \1", name, flags=re.IGNORECASE)
    name = re.sub(r"PSU(\d+)", r"PSU \1", name, flags=re.IGNORECASE)

    name = name.replace("_", " ")

    name = name.replace("OUTLETTMP", "Outlet Temperature")

    name = name.replace("OUTLET", "Outlet")
    name = name.replace("TACH", " Tach ")
    name = name.replace("FP", "Front Panel")
    name = name.replace("TEMP", "Temperature")
    name = name.replace("TMP", "Temperature")
    name = name.replace("INLET", "Inlet")
    name = name.replace("OUTLET", "Outlet")
    name = name.replace("PCH", "Chipset")

    name = name.replace("SENSOR", "")
    name = name.replace("SENS", "")

    return name.strip()
