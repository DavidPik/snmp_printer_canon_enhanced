"""SNMP Printer Canon MF754cdw sensors for Home Assistant.

This file implements a small set of sensors tailored for Canon MF754cdw
based on Printer-MIB OIDs.

Requires: pysnmp (asyncio) or adapt to your environment's SNMP helper.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from pysnmp.hlapi.asyncio import (
    getCmd,
    CommunityData,
    UdpTransportTarget,
    ContextData,
    ObjectType,
    ObjectIdentity,
)
from pysnmp.smi.rfc1902 import Integer, OctetString

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import (
    DEVICE_CLASS_PROBLEM,
    DEVICE_CLASS_TIMESTAMP,
    PERCENTAGE,
    COUNT,
)

from . import const

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = 60  # seconds


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up SNMP Canon sensors from a config entry."""
    host = entry.data.get("host")
    community = entry.data.get("community", "public")
    port = entry.data.get("port", 161)

    entities: list[Entity] = []

    # Supply sensors (toner levels)
    entities.append(
        CanonSupplySensor(
            hass,
            entry,
            name="Canon Toner Black",
            oid=const.OID_TONER_BLACK,
            color="black",
            unit=PERCENTAGE,
            host=host,
            community=community,
            port=port,
        )
    )
    entities.append(
        CanonSupplySensor(
            hass,
            entry,
            name="Canon Toner Cyan",
            oid=const.OID_TONER_CYAN,
            color="cyan",
            unit=PERCENTAGE,
            host=host,
            community=community,
            port=port,
        )
    )
    entities.append(
        CanonSupplySensor(
            hass,
            entry,
            name="Canon Toner Magenta",
            oid=const.OID_TONER_MAGENTA,
            color="magenta",
            unit=PERCENTAGE,
            host=host,
            community=community,
            port=port,
        )
    )
    entities.append(
        CanonSupplySensor(
            hass,
            entry,
            name="Canon Toner Yellow",
            oid=const.OID_TONER_YELLOW,
            color="yellow",
            unit=PERCENTAGE,
            host=host,
            community=community,
            port=port,
        )
    )

    # Toner max capacities (optional, used to compute percent if device returns absolute values)
    entities.append(
        CanonNumericSensor(
            hass,
            entry,
            name="Canon Toner Black Max",
            oid=const.OID_TONER_BLACK_MAX,
            unit="pages",
            host=host,
            community=community,
            port=port,
        )
    )
    entities.append(
        CanonNumericSensor(
            hass,
            entry,
            name="Canon Toner Cyan Max",
            oid=const.OID_TONER_CYAN_MAX,
            unit="pages",
            host=host,
            community=community,
            port=port,
        )
    )
    entities.append(
        CanonNumericSensor(
            hass,
            entry,
            name="Canon Toner Magenta Max",
            oid=const.OID_TONER_MAGENTA_MAX,
            unit="pages",
            host=host,
            community=community,
            port=port,
        )
    )
    entities.append(
        CanonNumericSensor(
            hass,
            entry,
            name="Canon Toner Yellow Max",
            oid=const.OID_TONER_YELLOW_MAX,
            unit="pages",
            host=host,
            community=community,
            port=port,
        )
    )

    # Waste toner (some devices return percent or absolute)
    entities.append(
        CanonSupplySensor(
            hass,
            entry,
            name="Canon Waste Toner",
            oid=const.OID_WASTE_TONER,
            color="grey",
            unit=PERCENTAGE,
            host=host,
            community=community,
            port=port,
        )
    )

    # Page counter
    entities.append(
        CanonNumericSensor(
            hass,
            entry,
            name="Canon Page Count",
            oid=const.OID_PAGE_COUNT,
            unit=COUNT,
            host=host,
            community=community,
            port=port,
        )
    )

    # Device status
    entities.append(
        CanonStatusSensor(
            hass,
            entry,
            name="Canon Device Status",
            oid=const.OID_DEVICE_STATUS,
            host=host,
            community=community,
            port=port,
        )
    )

    # Tray statuses
    entities.append(
        CanonTraySensor(
            hass,
            entry,
            name="Canon Multi Purpose Tray Status",
            oid=const.OID_TRAY_MP,
            host=host,
            community=community,
            port=port,
        )
    )
    entities.append(
        CanonTraySensor(
            hass,
            entry,
            name="Canon Tray 1 Status",
            oid=const.OID_TRAY_1,
            host=host,
            community=community,
            port=port,
        )
    )

    async_add_entities(entities, update_before_add=True)


class BaseSNMPSensor(Entity):
    """Base SNMP sensor."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, name: str, oid: str, host: str, community: str, port: int):
        self.hass = hass
        self._entry = entry
        self._name = name
        self._oid = oid
        self._host = host
        self._community = community
        self._port = port
        self._state = None
        self._attributes: dict[str, Any] = {}
        self._available = True

    @property
    def name(self) -> str:
        return self._name

    @property
    def available(self) -> bool:
        return self._available

    @property
    def extra_state_attributes(self) -> dict:
        return self._attributes

    async def async_update(self) -> None:
        """Fetch new state via SNMP GET."""
        try:
            value = await self._snmp_get(self._oid)
            self._process_value(value)
            self._available = True
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.debug("SNMP GET failed for %s (%s): %s", self._name, self._oid, exc)
            self._available = False

    async def _snmp_get(self, oid: str):
        """Perform SNMP GET and return raw value."""
        # Build SNMP GET
        target = UdpTransportTarget((self._host, self._port), timeout=2, retries=1)
        community = CommunityData(self._community, mpModel=1)  # SNMPv2c
        obj = ObjectType(ObjectIdentity(oid))

        # Execute async getCmd
        iterator = getCmd(community, target, ContextData(), obj)
        error_indication, error_status, error_index, var_binds = await iterator
        if error_indication:
            raise RuntimeError(f"SNMP error: {error_indication}")
        if error_status:
            raise RuntimeError(f"SNMP error status: {error_status.prettyPrint()} at {error_index}")
        # var_binds is a list of (ObjectIdentity, value)
        for _, val in var_binds:
            # Convert pysnmp types to python native
            if isinstance(val, (Integer,)):
                return int(val)
            if isinstance(val, (OctetString,)):
                return str(val.prettyPrint())
            # fallback
            return val.prettyPrint()
        raise RuntimeError("No SNMP value returned")

    def _process_value(self, value: Any) -> None:
        """Process raw SNMP value into sensor state. Override in subclasses."""
        self._state = value


class CanonNumericSensor(BaseSNMPSensor):
    """Numeric sensor for counts and capacities."""

    def __init__(self, hass, entry, name, oid, unit=None, host=None, community=None, port=161):
        super().__init__(hass, entry, name, oid, host, community, port)
        self._unit = unit

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return self._unit

    def _process_value(self, value: Any) -> None:
        try:
            self._state = int(value)
        except Exception:
            self._state = value


class CanonSupplySensor(BaseSNMPSensor):
    """Supply sensor for toners and waste."""

    def __init__(self, hass, entry, name, oid, color=None, unit=None, host=None, community=None, port=161):
        super().__init__(hass, entry, name, oid, host, community, port)
        self._color = color
        self._unit = unit or PERCENTAGE

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return self._unit

    @property
    def icon(self):
        # simple icon mapping
        if self._color == "cyan":
            return "mdi:water"
        if self._color == "magenta":
            return "mdi:flower"
        if self._color == "yellow":
            return "mdi:brightness-5"
        if self._color == "black":
            return "mdi:circle"
        return "mdi:printer"

    def _process_value(self, value: Any) -> None:
        # Canon often returns percentage directly; sometimes absolute value
        try:
            val = int(value)
            # clamp
            if val < 0:
                val = 0
            if val > 10000 and val > 100:  # heuristic: if very large, treat as pages
                # leave as-is (pages)
                self._state = val
                self._attributes["value_type"] = "absolute"
            else:
                # treat as percent
                if val > 100:
                    # some devices return 0-255 scale; normalize to 0-100
                    if val <= 255:
                        val = round(val / 255 * 100)
                self._state = val
                self._attributes["value_type"] = "percent"
        except Exception:
            self._state = value


class CanonStatusSensor(BaseSNMPSensor):
    """Device status sensor."""

    def __init__(self, hass, entry, name, oid, host=None, community=None, port=161):
        super().__init__(hass, entry, name, oid, host, community, port)

    @property
    def icon(self):
        return "mdi:printer-alert"

    @property
    def state(self):
        # map common Printer-MIB states
        if self._state is None:
            return None
        try:
            s = int(self._state)
            # typical mapping: 1=other,2=unknown,3=idle,4=printing,5=warmup (varies)
            if s == 3:
                return "idle"
            if s == 4:
                return "printing"
            if s == 5:
                return "warmup"
            if s == 2:
                return "unknown"
            return f"state_{s}"
        except Exception:
            return str(self._state)


class CanonTraySensor(BaseSNMPSensor):
    """Tray status sensor."""

    def __init__(self, hass, entry, name, oid, host=None, community=None, port=161):
        super().__init__(hass, entry, name, oid, host, community, port)

    @property
    def icon(self):
        return "mdi:tray"

    @property
    def state(self):
        # Canon may return textual status or numeric code
        if self._state is None:
            return None
        try:
            val = int(self._state)
            # map common codes (device dependent)
            # 1 = other, 2 = unknown, 3 = available, 4 = not available, 5 = jammed
            if val == 3:
                return "available"
            if val == 4:
                return "not_available"
            if val == 5:
                return "jammed"
            return f"code_{val}"
        except Exception:
            return str(self._state)
