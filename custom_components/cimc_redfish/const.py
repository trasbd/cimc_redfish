"""Constants used by CIMC Redfish."""

DOMAIN = "cimc_redfish"

PLATFORMS = ["sensor"]

CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_VERIFY_SSL = "verify_ssl"
CONF_TLS_MIN = "tls_min"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_VERIFY_SSL = False
DEFAULT_TLS_MIN = "1.0"  # "1.0", "1.1", "1.2"
DEFAULT_SCAN_INTERVAL = 30  # seconds

ATTR_FANS = "fans"
