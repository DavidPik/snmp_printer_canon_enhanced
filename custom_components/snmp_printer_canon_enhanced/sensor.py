"""SNMP Printer Canon MF754cdw sensors for Home Assistant (no pysnmp).

Tento soubor vytváří senzory pro Canon MF754cdw.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import Entity
from homeassistant.const import PERCENTAGE, COUNT

# Pokusíme se importovat interní SNMP modul HA; pokud není, logujeme chybu.
try:
    from homeassistant.components import snmp  # type: ignore
except Exception:  # pragma: no cover - runtime fallback
    snmp = None  # type: ignore

from . import const

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = 60  # seconds


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Nastavení entit pro Canon MF754cdw z config entry."""
    host = entry.data.get("host")
    community = entry.data.get("community", "public")
    port = entry.data.get("port", 161)

    if snmp is None:
        _LOGGER.error("SNMP helper není dostupný v tomto Home Assistantu. Zkontroluj verzi HA nebo použij jinou metodu.")
        return

    entities: list[Entity] = []

    # Tonery (procenta / absolutní)
    entities.append(
        CanonSupplySensor(hass, entry, "Canon Toner Black", const.OID_TONER_BLACK, color="black", unit=PERCENTAGE, host=host, community=community, port=port)
    )
    entities.append(
        CanonSupplySensor(hass, entry, "Canon Toner Cyan", const.OID_TONER_CYAN, color="cyan", unit=PERCENTAGE, host=host, community=community, port=port)
    )
    entities.append(
        CanonSupplySensor(hass, entry, "Canon Toner Magenta", const.OID_TONER_MAGENTA, color="magenta", unit=PERCENTAGE, host=host, community=community, port=port)
    )
    entities.append(
        CanonSupplySensor(hass, entry, "Canon Toner Yellow", const.OID_TONER_YELLOW, color="yellow", unit=PERCENTAGE, host=host, community=community, port=port)
    )

    # Max kapacity tonerů (počet stran)
    entities.append(
        CanonNumericSensor(hass, entry, "Canon Toner Black Max", const.OID_TONER_BLACK_MAX, unit="pages", host=host, community=community, port=port)
    )
    entities.append(
        CanonNumericSensor(hass, entry, "Canon Toner Cyan Max", const.OID_TONER_CYAN_MAX, unit="pages", host=host, community=community, port=port)
    )
    entities.append(
        CanonNumericSensor(hass, entry, "Canon Toner Magenta Max", const.OID_TONER_MAGENTA_MAX, unit="pages", host=host, community=community, port=port)
    )
    entities.append(
        CanonNumericSensor(hass, entry, "Canon Toner Yellow Max", const.OID_TONER_YELLOW_MAX, unit="pages", host=host, community=community, port=port)
    )

    # Waste toner
    entities.append(
        CanonSupplySensor(hass, entry, "Canon Waste Toner", const.OID_WASTE_TONER, color="grey", unit=PERCENTAGE, host=host, community=community, port=port)
    )

    # Page counter
    entities.append(
        CanonNumericSensor(hass, entry, "Canon Page Count", const.OID_PAGE_COUNT, unit=COUNT, host=host, community=community, port=port)
    )

    # Device status
    entities.append(
        CanonStatusSensor(hass, entry, "Canon Device Status", const.OID_DEVICE_STATUS, host=host, community=community, port=port)
    )

    # Tray statuses
    entities.append(
        CanonTraySensor(hass, entry, "Canon Multi Purpose Tray Status", const.OID_TRAY_MP, host=host, community=community, port=port)
    )
    entities.append(
        CanonTraySensor(hass, entry, "Canon Tray 1 Status", const.OID_TRAY_1, host=host, community=community, port=port)
    )

    async_add_entities(entities, update_before_add=True)


class BaseSNMPSensor(Entity):
    """Základní SNMP senzor používající interní HA SNMP helper."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, name: str, oid: str, host: str, community: str, port: int):
        self.hass = hass
        self._entry = entry
        self._name = name
        self._oid = oid
        self._host = host
        self._community = community
        self._port = port
        self._state: Any = None
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
        """Načti hodnotu přes interní SNMP helper a zpracuj ji."""
        try:
            value = await self._snmp_get(self._oid)
            self._process_value(value)
            self._available = True
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.debug("SNMP GET selhalo pro %s (%s): %s", self._name, self._oid, exc)
            self._available = False

    async def _snmp_get(self, oid: str) -> Any:
        """Volání interního SNMP helperu Home Assistantu.

        Očekává se, že modul `homeassistant.components.snmp` poskytuje
        asynchronní funkci `async_get(hass, host, community, oid, port=161)`.
        Pokud má tvá verze HA jinou signaturu, uprav volání zde.
        """
        if snmp is None:
            raise RuntimeError("SNMP helper není dostupný v HA runtime")

        # Pokusíme se zavolat běžné wrappery; pokud signatura neodpovídá,
        # zachytíme chybu a vyhodíme srozumitelnou výjimku.
        try:
            # běžné volání: snmp.async_get(hass, host, community, oid, port=161)
            result = await snmp.async_get(self.hass, self._host, self._community, oid, port=self._port)
            # result může být dict nebo primitivní typ; normalizujeme
            if isinstance(result, dict) and "value" in result:
                return result["value"]
            return result
        except AttributeError:
            # fallback: některé verze mají snmp.async_get(hass, host, oid, community)
            try:
                result = await snmp.async_get(self.hass, self._host, oid, self._community)
                if isinstance(result, dict) and "value" in result:
                    return result["value"]
                return result
            except Exception as exc:
                raise RuntimeError(f"SNMP helper volání selhalo: {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"SNMP GET error: {exc}") from exc

    def _process_value(self, value: Any) -> None:
        """Základní zpracování hodnoty; přepsat v podtřídách."""
        self._state = value


class CanonNumericSensor(BaseSNMPSensor):
    """Číselný senzor pro počítadla a kapacity."""

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
            # pokud nelze převést, ponecháme původní hodnotu (text)
            self._state = value


class CanonSupplySensor(BaseSNMPSensor):
    """Senzor pro tonery a waste toner."""

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
        """Zpracování hodnoty toneru. Canon může vracet procenta, 0-255 nebo absolutní hodnoty."""
        try:
            val = int(value)
            # heuristika: pokud je hodnota v rozsahu 0-100, bereme jako procento
            if 0 <= val <= 100:
                self._state = val
                self._attributes["value_type"] = "percent"
                return

            # pokud je v rozsahu 0-255, normalizujeme na 0-100
            if 0 <= val <= 255:
                self._state = round(val / 255 * 100)
                self._attributes["value_type"] = "normalized_0_255"
                return

            # pokud je větší než 100 a v řádu stovek/tisíců, může jít o počet stran (absolute)
            if val > 100:
                self._state = val
                self._attributes["value_type"] = "absolute"
                return

            # fallback
            self._state = val
        except Exception:
            # textové nebo jiné hodnoty
            self._state = value


class CanonStatusSensor(BaseSNMPSensor):
    """Senzor stavu zařízení (Printer-MIB / hrDeviceStatus)."""

    @property
    def icon(self):
        return "mdi:printer-alert"

    @property
    def state(self):
        if self._state is None:
            return None
        try:
            s = int(self._state)
            # mapování podle běžných hodnot (může se lišit podle zařízení)
            # 1=other, 2=unknown, 3=idle, 4=printing, 5=warmup
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
    """Senzor stavu zásobníku."""

    @property
    def icon(self):
        return "mdi:tray"

    @property
    def state(self):
        if self._state is None:
            return None
        try:
            val = int(self._state)
            # běžné mapování (zařízení se liší)
            # 1=other,2=unknown,3=available,4=not available,5=jammed
            if val == 3:
                return "available"
            if val == 4:
                return "not_available"
            if val == 5:
                return "jammed"
            return f"code_{val}"
        except Exception:
            return str(self._state)
