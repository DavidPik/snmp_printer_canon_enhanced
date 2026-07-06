"""SNMP client specialized for Canon MF754cdw / MF750C series."""

from __future__ import annotations

import logging
import time
from typing import Any

from pysnmp_lextudio.hlapi.asyncio import (
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    UsmUserData,
    bulkCmd,
    getCmd,
)

_LOGGER = logging.getLogger(__name__)

# Canon MF754cdw – verified OIDs
CANON_OID = {
    # System
    "sysDescr": "1.3.6.1.2.1.1.1.0",
    "sysName": "1.3.6.1.2.1.1.5.0",
    "sysLocation": "1.3.6.1.2.1.1.6.0",
    "sysContact": "1.3.6.1.2.1.1.4.0",
    "sysUptime": "1.3.6.1.2.1.1.3.0",
    # Device info
    "serialNumber": "1.3.6.1.2.1.43.5.1.1.17.1",
    "macAddress": "1.3.6.1.2.1.2.2.1.6.1",
    # Printer status (hrDeviceStatus)
    # 1=unknown, 2=running, 3=warning, 4=testing, 5=down
    "deviceStatus": "1.3.6.1.2.1.25.3.2.1.5.1",
    # Printer alerts (prtAlertDescription)
    "alertDescription": "1.3.6.1.2.1.43.18.1.1.8.1.1",
    # Page counts (Canon MF754cdw)
    "pageTotal": "1.3.6.1.2.1.43.10.2.1.4.1.1",
    "pageColor": "1.3.6.1.2.1.43.10.2.1.5.1.1",
    "pageMono": "1.3.6.1.2.1.43.10.2.1.6.1.1",
    # Supplies (standard Printer-MIB)
    "supplyDescription": "1.3.6.1.2.1.43.11.1.1.6.1",
    "supplyLevel": "1.3.6.1.2.1.43.11.1.1.9.1",
    "supplyMax": "1.3.6.1.2.1.43.11.1.1.8.1",
    "supplyClass": "1.3.6.1.2.1.43.11.1.1.5.1",
    "supplyType": "1.3.6.1.2.1.43.11.1.1.4.1",
    # Input trays
    "trayDescription": "1.3.6.1.2.1.43.8.2.1.18.1",
    "trayMaxCapacity": "1.3.6.1.2.1.43.8.2.1.9.1",
    "trayLevel": "1.3.6.1.2.1.43.8.2.1.11.1",
}

PRINTER_STATUS_MAP = {
    1: "unknown",
    2: "running",
    3: "warning",
    4: "testing",
    5: "down",
}


class SNMPClient:
    """Canon‑specialized SNMP client."""

    def __init__(
        self,
        host: str,
        port: int = 161,
        snmp_version: str = "2c",
        community: str = "public",
        username: str | None = None,
        auth_protocol: str | None = None,
        auth_key: str | None = None,
        priv_protocol: str | None = None,
        priv_key: str | None = None,
        timeout: float = 1.0,
        retries: int = 3,
    ):
        self.host = host
        self.port = port
        self.snmp_version = snmp_version
        self.community = community
        self.username = username
        self.auth_protocol = auth_protocol
        self.auth_key = auth_key
        self.priv_protocol = priv_protocol
        self.priv_key = priv_key
        self.timeout = timeout
        self.retries = retries

        self._engine = SnmpEngine()
        self._transport = None
        self._auth_data = self._get_auth_data()

        self._connection_state = "unknown"
        self._last_error_log_time = 0
        self._consecutive_failures = 0

    def _get_auth_data(self):
        """SNMP v1/v2c/v3 authentication."""
        if self.snmp_version == "3":
            return UsmUserData(
                self.username,
                authKey=self.auth_key,
                privKey=self.priv_key,
            )
        return CommunityData(self.community)

    async def _ensure_transport(self):
        if self._transport is None:
            self._transport = UdpTransportTarget(
                (self.host, self.port),
                timeout=self.timeout,
                retries=self.retries,
            )

    def _handle_error(self, msg: str):
        now = time.time()
        self._consecutive_failures += 1

        if self._connection_state in ("unknown", "online"):
            _LOGGER.error("Printer %s offline: %s", self.host, msg)
            self._connection_state = "offline"
            self._last_error_log_time = now
        else:
            if now - self._last_error_log_time > 30:
                _LOGGER.warning("Printer %s still offline: %s", self.host, msg)
                self._last_error_log_time = now

    def _mark_success(self):
        if self._connection_state == "offline":
            _LOGGER.info(
                "Printer %s is back online after %d failures",
                self.host,
                self._consecutive_failures,
            )
        self._connection_state = "online"
        self._consecutive_failures = 0

    async def _get(self, oid: str) -> Any:
        await self._ensure_transport()
        errorIndication, errorStatus, errorIndex, varBinds = await getCmd(
            self._engine,
            self._auth_data,
            self._transport,
            ContextData(),
            ObjectType(ObjectIdentity(oid)),
        )

        if errorIndication:
            self._handle_error(str(errorIndication))
            return None
        if errorStatus:
            self._handle_error(str(errorStatus.prettyPrint()))
            return None

        for vb in varBinds:
            self._mark_success()
            return vb[1].prettyPrint()

        return None

    async def _walk(self, oid: str) -> dict[str, str]:
        await self._ensure_transport()
        results = {}

        async for errorIndication, errorStatus, errorIndex, varBinds in bulkCmd(
            self._engine,
            self._auth_data,
            self._transport,
            ContextData(),
            0,
            25,
            ObjectType(ObjectIdentity(oid)),
            lexicographicMode=False,
        ):
            if errorIndication:
                self._handle_error(str(errorIndication))
                break
            if errorStatus:
                self._handle_error(str(errorStatus.prettyPrint()))
                break

            for vb in varBinds:
                full_oid = str(vb[0])
                if full_oid.startswith(oid + "."):
                    index = full_oid[len(oid) + 1 :]
                    results[index] = vb[1].prettyPrint()

        if results:
            self._mark_success()

        return results

    #
    # Canon MF754cdw – System Info
    #
    async def get_system_info(self) -> dict[str, Any]:
        return {
            "description": await self._get(CANON_OID["sysDescr"]),
            "name": await self._get(CANON_OID["sysName"]),
            "location": await self._get(CANON_OID["sysLocation"]),
            "contact": await self._get(CANON_OID["sysContact"]),
            "uptime": await self._get(CANON_OID["sysUptime"]),
        }

    #
    # Canon MF754cdw – Device Info
    #
    async def get_device_info(self) -> dict[str, Any]:
        status_raw = await self._get(CANON_OID["deviceStatus"])
        status = PRINTER_STATUS_MAP.get(int(status_raw) if status_raw else 1, "unknown")

        serial = await self._get(CANON_OID["serialNumber"])
        mac_raw = await self._get(CANON_OID["macAddress"])

        mac = None
        if mac_raw:
            try:
                mac_bytes = bytes.fromhex(mac_raw.replace(" ", "").replace("0x", ""))
                mac = ":".join(f"{b:02x}" for b in mac_bytes)
            except Exception:
                mac = mac_raw

        return {
            "state": status,
            "serial_number": serial,
            "mac_address": mac,
            "alerts": await self._get(CANON_OID["alertDescription"]),
            "page_counts": await self.get_page_counts(),
        }

    #
    # Canon MF754cdw – Page Counts
    #
    async def get_page_counts(self) -> dict[str, int | None]:
        total = await self._get(CANON_OID["pageTotal"])
        color = await self._get(CANON_OID["pageColor"])
        mono = await self._get(CANON_OID["pageMono"])

        return {
            "total": int(total) if total and total.isdigit() else None,
            "color": int(color) if color and color.isdigit() else None,
            "mono": int(mono) if mono and mono.isdigit() else None,
        }

    #
    # Canon MF754cdw – Supplies (toner + waste toner)
    #
    async def get_supplies(self) -> list[dict[str, Any]]:
        descriptions = await self._walk(CANON_OID["supplyDescription"])
        levels = await self._walk(CANON_OID["supplyLevel"])
        max_caps = await self._walk(CANON_OID["supplyMax"])

        supplies = []

        for index, desc in descriptions.items():
            level = levels.get(index)
            max_cap = max_caps.get(index)

            try:
                level = int(level) if level and level.isdigit() else None
                max_cap = int(max_cap) if max_cap and max_cap.isdigit() else None
            except Exception:
                level = None
                max_cap = None

            percentage = None
            if max_cap and level is not None and max_cap > 0:
                percentage = int((level / max_cap) * 100)

            supplies.append(
                {
                    "index": index,
                    "description": desc,
                    "level": level,
                    "max_capacity": max_cap,
                    "percentage": percentage,
                }
            )

        return supplies

    #
    # Canon MF754cdw – Input Trays
    #
    async def get_input_trays(self) -> list[dict[str, Any]]:
        descriptions = await self._walk(CANON_OID["trayDescription"])
        levels = await self._walk(CANON_OID["trayLevel"])
        max_caps = await self._walk(CANON_OID["trayMaxCapacity"])

        trays = []

        for index, desc in descriptions.items():
            level = levels.get(index)
            max_cap = max_caps.get(index)

            try:
                level = int(level) if level and level.isdigit() else None
                max_cap = int(max_cap) if max_cap and max_cap.isdigit() else None
            except Exception:
                level = None
                max_cap = None

            percentage = None
            if max_cap and level is not None and max_cap > 0:
                percentage = int((level / max_cap) * 100)

            trays.append(
                {
                    "index": index,
                    "description": desc,
                    "level": level,
                    "max_capacity": max_cap,
                    "percentage": percentage,
                }
            )

        return trays

    #
    # Canon MF754cdw – Unsupported features removed
    #
    async def get_cover_status(self) -> str:
        return "unknown"

    async def get_display_text(self) -> None:
        return None

    async def set_display_text(self, text: str) -> bool:
        return False

    async def get_printer_errors(self) -> str | None:
        return await self._get(CANON_OID["alertDescription"])

    #
    # Canon MF754cdw – Full data snapshot
    #
    async def get_all_data(self) -> dict[str, Any]:
        return {
            "system": await self.get_system_info(),
            "device": await self.get_device_info(),
            "supplies": await self.get_supplies(),
            "trays": await self.get_input_trays(),
        }
