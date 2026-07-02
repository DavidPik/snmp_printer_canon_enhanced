"""Canon MF754cdw SNMP Printer integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
)
from .snmp_client import SNMPClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]
STORAGE_VERSION = 1
STORAGE_KEY = "snmp_printer_canon_enhanced_cached_data"


async def check_web_interface(host: str, hass: HomeAssistant) -> bool:
    """Check if the printer's web interface is reachable."""
    session = async_get_clientsession(hass)

    # Try HTTP
    try:
        async with asyncio.timeout(3):
            async with session.get(f"http://{host}", allow_redirects=True) as response:
                if response.status < 500:
                    return True
    except Exception:
        pass

    # Try HTTPS
    try:
        async with asyncio.timeout(3):
            async with session.get(
                f"https://{host}", allow_redirects=True, ssl=False
            ) as response:
                if response.status < 500:
                    return True
    except Exception:
        pass

    return False


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Canon MF754cdw SNMP Printer."""
    hass.data.setdefault(DOMAIN, {})

    # Create SNMP client (Canon MF754cdw uses SNMPv2c only)
    snmp_client = SNMPClient(
        host=entry.data[CONF_HOST],
        port=entry.data.get("port", 161),
        snmp_version="2c",
        community=entry.data.get("community", "public"),
    )

    # Update interval
    update_interval = entry.options.get(
        CONF_UPDATE_INTERVAL,
        entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
    )

    # Cache storage
    store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry.entry_id}")
    cached_data = await store.async_load() or {}

    #
    # Data update function
    #
    async def async_update_data():
        try:
            system_info = await snmp_client.get_system_info()
            device_info = await snmp_client.get_device_info()

            data = {
                "info": {**system_info, **device_info},
                "status": {"state": device_info.get("state")},
                "page_counts": device_info.get("page_counts", {}),
                "supplies": await snmp_client.get_supplies(),
                "input_trays": await snmp_client.get_input_trays(),
                "errors": device_info.get("alerts"),
                "web_interface_available": await check_web_interface(
                    entry.data[CONF_HOST], hass
                ),
            }

            # Save cache
            cache_data = {
                "data": data,
                "timestamp": datetime.now().isoformat(),
                "host": entry.data[CONF_HOST],
            }
            await store.async_save(cache_data)

            data["is_online"] = True
            return data

        except Exception as err:
            error_msg = str(err).lower()
            is_connection_error = any(
                keyword in error_msg
                for keyword in [
                    "timeout",
                    "unreachable",
                    "no route",
                    "connection",
                    "network",
                    "host",
                    "refused",
                    "failed",
                    "no response",
                ]
            )

            if cached_data.get("data") and is_connection_error:
                _LOGGER.warning(
                    "Canon printer %s offline (%s), using cached data from %s",
                    entry.data[CONF_HOST],
                    err,
                    cached_data.get("timestamp", "unknown"),
                )

                cached_printer_data = cached_data["data"].copy()
                cached_printer_data["is_online"] = False
                cached_printer_data["offline_since"] = cached_data.get("timestamp")

                return cached_printer_data

            raise UpdateFailed(f"Error fetching Canon printer data: {err}") from err

    #
    # Coordinator
    #
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"snmp_printer_canon_enhanced_{entry.data[CONF_HOST]}",
        update_method=async_update_data,
        update_interval=timedelta(seconds=update_interval),
    )

    await coordinator.async_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "client": snmp_client,
        "store": store,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
