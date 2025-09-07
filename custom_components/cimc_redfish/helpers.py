import re


def normalize_name(raw: str | None) -> str:
    """Return a prettier display name for CIMC objects."""
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
