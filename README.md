# Cisco CIMC Redfish – Home Assistant Integration

This is a custom [Home Assistant](https://www.home-assistant.io/) integration for monitoring **Cisco C-Series servers** via the **CIMC Redfish API**.  
It provides sensors for fans, power supplies, voltages, power consumption, and temperatures.

---

## Features

- **Fan sensors** – expose per-fan RPM, health, and thresholds.
- **PSU sensors** – report line input voltage, last output power, and detailed rail telemetry.
- **Power metrics** – total consumed watts plus min/avg/max over an interval.
- **Temperature sensors** – CPU, riser, inlet/outlet, PSU, and other system board readings.
- **Config flow** – add via the Home Assistant UI, no YAML required.
- **Options flow** – adjust polling interval in seconds.
- Works with CIMC firmware that supports **Redfish**.

---

## Installation

1. Copy this folder to your Home Assistant `custom_components` directory:

   ```
   custom_components/cimc_redfish/
   ```

2. Restart Home Assistant.

3. In the UI, go to **Settings → Devices & Services → Add Integration**, search for  
   **Cisco CIMC Redfish**, and enter:
   - Host or IP
   - Username and Password
   - TLS minimum version (default: 1.0)
   - Whether to verify SSL certificates

---

## Configuration

- **Scan interval**: configurable via Options; defaults to **30 seconds**.  
- **TLS/SSL**: some older CIMC firmware only supports weak ciphers/TLS 1.0.  
  You can disable certificate verification or lower TLS minimum if needed.

---

## Example Sensors

- `sensor.cimc_fan1_rpm` – Fan speed in RPM
- `sensor.cimc_psu1_voltage` – PSU output voltage
- `sensor.cimc_psu1_power` – PSU output power in watts
- `sensor.cimc_power_consumed_watts` – overall system consumption
- `sensor.cimc_cpu_temp` – CPU temperature in °C

---

## Troubleshooting

- **403 Forbidden** → check user role; read-only accounts may not see Redfish.
- **Not supported** → your CIMC firmware may not expose Redfish endpoints.
- **SSL errors** → try disabling verification or lowering TLS minimum version.
- Check Home Assistant logs for detailed error messages.

---

## Disclaimer

This is a community-developed integration and is **not affiliated with Cisco**.  
Use at your own risk.
