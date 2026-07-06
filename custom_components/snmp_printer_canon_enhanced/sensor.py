"""Support for Canon MF754cdw SNMP Printer sensors."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Canon MF754cdw sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []

    # Main status sensor
    entities.append(PrinterStatusSensor(coordinator, entry))

    # Page counts
    entities.append(PrinterPageCountSensor(coordinator, entry))

    # Error / alert sensor
    entities.append(PrinterErrorSensor(coordinator, entry))

    # Supplies (toner + waste toner)
    if coordinator.data and "supplies" in coordinator.data:
        for supply in coordinator.data["supplies"]:
            entities.append(PrinterSupplySensor(coordinator, entry, supply))

    # Input trays
    if coordinator.data and "input_trays" in coordinator.data:
        for tray in coordinator.data["input_trays"]:
            entities.append(PrinterTraySensor(coordinator, entry, tray))

    # Additional Canon MF754cdw sensors
    entities.append(PrinterWasteTonerSensor(coordinator, entry))
    entities.append(PrinterDrumLifeSensor(coordinator, entry))
    entities.append(PrinterFuserTemperatureSensor(coordinator, entry))
    entities.append(PrinterDuplexUnitSensor(coordinator, entry))
    entities.append(PrinterScannerStatusSensor(coordinator, entry))

    async_add_entities(entities, True)


class PrinterSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for Canon printer sensors."""

    def __init__(self, coordinator: DataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_has_entity_name = True

    @property
    def available(self) -> bool:
        return self.coordinator.data is not None

    @property
    def is_printer_online(self) -> bool:
        if not self.coordinator.data:
            return False
        return self.coordinator.data.get("is_online", True)

    @property
    def device_info(self) -> DeviceInfo:
        data = self.coordinator.data or {}
        info = data.get("info", {})

        description = info.get("description", "")
        model = "Canon MF754cdw"
        manufacturer = "Canon"

        unique_id = info.get("serial_number", self._entry.data[CONF_HOST])

        device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            name=description,
            manufacturer=manufacturer,
            model=model,
        )

        if data.get("web_interface_available"):
            device_info["configuration_url"] = f"http://{self._entry.data[CONF_HOST]}"

        if info.get("serial_number"):
            device_info["serial_number"] = info["serial_number"]

        return device_info


class PrinterStatusSensor(PrinterSensorBase):
    """Printer status."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_translation_key = "status"
        unique_id = (
            coordinator.data.get("info", {}).get("serial_number", entry.data[CONF_HOST])
            if coordinator.data
            else entry.data[CONF_HOST]
        )
        self._attr_unique_id = f"{unique_id}_status"
        self._attr_icon = "mdi:printer"
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = ["running", "warning", "down", "unknown", "offline"]

    @property
    def native_value(self):
        if not self.coordinator.data:
            return "unknown"
        if not self.is_printer_online:
            return "offline"
        return self.coordinator.data.get("status", {}).get("state", "unknown")


class PrinterPageCountSensor(PrinterSensorBase):
    """Page count sensor."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_translation_key = "page_count"
        unique_id = (
            coordinator.data.get("info", {}).get("serial_number", entry.data[CONF_HOST])
            if coordinator.data
            else entry.data[CONF_HOST]
        )
        self._attr_unique_id = f"{unique_id}_page_count"
        self._attr_icon = "mdi:counter"
        self._attr_native_unit_of_measurement = "pages"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("page_counts", {}).get("total")

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
        pc = self.coordinator.data.get("page_counts", {})
        attrs = {}
        if pc.get("color") is not None:
            attrs["color_pages"] = pc.get("color")
        if pc.get("mono") is not None:
            attrs["mono_pages"] = pc.get("mono")
        return attrs


class PrinterErrorSensor(PrinterSensorBase):
    """Printer alert / error sensor."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_translation_key = "errors"
        unique_id = (
            coordinator.data.get("info", {}).get("serial_number", entry.data[CONF_HOST])
            if coordinator.data
            else entry.data[CONF_HOST]
        )
        self._attr_unique_id = f"{unique_id}_errors"
        self._attr_icon = "mdi:alert"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self):
        if not self.coordinator.data:
            return "none"
        return self.coordinator.data.get("errors") or "none"


class PrinterSupplySensor(PrinterSensorBase):
    """Canon toner / waste toner sensor."""

    def __init__(self, coordinator, entry, supply):
        super().__init__(coordinator, entry)
        self._supply = supply

        desc = supply.get("description", "Supply")
        unique_id = (
            coordinator.data.get("info", {}).get("serial_number", entry.data[CONF_HOST])
            if coordinator.data
            else entry.data[CONF_HOST]
        )

        self._attr_name = desc
        self._attr_unique_id = f"{unique_id}_supply_{supply.get('index')}"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:water"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        for s in self.coordinator.data.get("supplies", []):
            if s.get("index") == self._supply.get("index"):
                return s.get("percentage")
        return None

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
        for s in self.coordinator.data.get("supplies", []):
            if s.get("index") == self._supply.get("index"):
                return {
                    "description": s.get("description"),
                    "level": s.get("level"),
                    "max_capacity": s.get("max_capacity"),
                }
        return {}


class PrinterTraySensor(PrinterSensorBase):
    """Canon input tray sensor."""

    def __init__(self, coordinator, entry, tray):
        super().__init__(coordinator, entry)
        self._tray = tray

        desc = tray.get("description", f"Tray {tray.get('index')}")
        unique_id = (
            coordinator.data.get("info", {}).get("serial_number", entry.data[CONF_HOST])
            if coordinator.data
            else entry.data[CONF_HOST]
        )

        self._attr_name = desc
        self._attr_unique_id = f"{unique_id}_tray_{tray.get('index')}"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_icon = "mdi:tray"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        for t in self.coordinator.data.get("input_trays", []):
            if t.get("index") == self._tray.get("index"):
                return t.get("percentage")
        return None

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return {}
        for t in self.coordinator.data.get("input_trays", []):
            if t.get("index") == self._tray.get("index"):
                return {
                    "level": t.get("level"),
                    "max_capacity": t.get("max_capacity"),
                }
        return {}


#
# Additional Canon MF754cdw sensors
#


class PrinterWasteTonerSensor(PrinterSensorBase):
    """Waste toner level."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_name = "Waste Toner"
        self._attr_unique_id = f"{entry.data[CONF_HOST]}_waste_toner"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_icon = "mdi:delete"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        for s in self.coordinator.data.get("supplies", []):
            if "waste" in s.get("description", "").lower():
                return s.get("percentage")
        return None


class PrinterDrumLifeSensor(PrinterSensorBase):
    """Drum life sensor."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_name = "Drum Life"
        self._attr_unique_id = f"{entry.data[CONF_HOST]}_drum_life"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_icon = "mdi:circle-outline"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        for s in self.coordinator.data.get("supplies", []):
            if "drum" in s.get("description", "").lower():
                return s.get("percentage")
        return None


class PrinterFuserTemperatureSensor(PrinterSensorBase):
    """Fuser temperature (if available)."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_name = "Fuser Temperature"
        self._attr_unique_id = f"{entry.data[CONF_HOST]}_fuser_temp"
        self._attr_icon = "mdi:thermometer"
        self._attr_native_unit_of_measurement = "°C"

    @property
    def native_value(self):
        # Canon MF754cdw does not expose fuser temp via SNMP
        return None


class PrinterDuplexUnitSensor(PrinterSensorBase):
    """Duplex unit status."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_name = "Duplex Unit"
        self._attr_unique_id = f"{entry.data[CONF_HOST]}_duplex"
        self._attr_icon = "mdi:printer"

    @property
    def native_value(self):
        # Canon MF754cdw does not expose duplex unit via SNMP
        return None


class PrinterScannerStatusSensor(PrinterSensorBase):
    """Scanner status."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_name = "Scanner Status"
        self._attr_unique_id = f"{entry.data[CONF_HOST]}_scanner"
        self._attr_icon = "mdi:scanner"

    @property
    def native_value(self):
        # Canon MF754cdw does not expose scanner status via SNMP
        return None
