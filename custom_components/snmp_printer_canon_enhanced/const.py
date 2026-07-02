"""Constants for the Canon MF754cdw SNMP Printer integration."""

from typing import Final

#
# Basic integration metadata
#
DOMAIN: Final = "snmp_printer_canon_enhanced"

# Configuration keys
CONF_UPDATE_INTERVAL: Final = "update_interval"
CONF_SNMP_VERSION: Final = "snmp_version"
CONF_COMMUNITY: Final = "community"

# Defaults
DEFAULT_PORT: Final = 161
DEFAULT_COMMUNITY: Final = "public"
DEFAULT_UPDATE_INTERVAL: Final = 60
DEFAULT_SNMP_VERSION: Final = "2c"

# Error logging throttling
DEFAULT_ERROR_LOG_INTERVAL: Final = 300  # seconds


#
# Canon MF754cdw – Verified SNMP OIDs
# These OIDs are used directly by snmp_client.py
#

# System information (MIB-II)
OID_SYS_DESCR: Final = "1.3.6.1.2.1.1.1.0"
OID_SYS_NAME: Final = "1.3.6.1.2.1.1.5.0"
OID_SYS_LOCATION: Final = "1.3.6.1.2.1.1.6.0"
OID_SYS_CONTACT: Final = "1.3.6.1.2.1.1.4.0"
OID_SYS_UPTIME: Final = "1.3.6.1.2.1.1.3.0"

# Device info
OID_SERIAL_NUMBER: Final = "1.3.6.1.2.1.43.5.1.1.17.1"
OID_MAC_ADDRESS: Final = "1.3.6.1.2.1.2.2.1.6.1"

# Device status (hrDeviceStatus)
# 1=unknown, 2=running, 3=warning, 4=testing, 5=down
OID_DEVICE_STATUS: Final = "1.3.6.1.2.1.25.3.2.1.5.1"

# Printer alerts (prtAlertDescription)
OID_ALERT_DESCRIPTION: Final = "1.3.6.1.2.1.43.18.1.1.8.1.1"


#
# Page counts (Canon MF754cdw)
#
OID_PAGE_TOTAL: Final = "1.3.6.1.2.1.43.10.2.1.4.1.1"
OID_PAGE_COLOR: Final = "1.3.6.1.2.1.43.10.2.1.5.1.1"
OID_PAGE_MONO: Final = "1.3.6.1.2.1.43.10.2.1.6.1.1"


#
# Supplies (toner + waste toner)
# Canon MF754cdw uses standard Printer-MIB supplies tables
#
OID_SUPPLY_DESCRIPTION: Final = "1.3.6.1.2.1.43.11.1.1.6.1"
OID_SUPPLY_LEVEL: Final = "1.3.6.1.2.1.43.11.1.1.9.1"
OID_SUPPLY_MAX_CAPACITY: Final = "1.3.6.1.2.1.43.11.1.1.8.1"


#
# Input trays (paper trays)
#
OID_TRAY_DESCRIPTION: Final = "1.3.6.1.2.1.43.8.2.1.18.1"
OID_TRAY_MAX_CAPACITY: Final = "1.3.6.1.2.1.43.8.2.1.9.1"
OID_TRAY_LEVEL: Final = "1.3.6.1.2.1.43.8.2.1.11.1"


#
# Canon MF754cdw – Status mapping
#
PRINTER_STATUS_MAP = {
    1: "unknown",
    2: "running",
    3: "warning",
    4: "testing",
    5: "down",
}
