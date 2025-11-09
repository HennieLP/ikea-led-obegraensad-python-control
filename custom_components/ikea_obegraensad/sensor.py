"""Sensor platform for IKEA OBEGRÄNSAD LED Control."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import IkeaLedCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the IKEA OBEGRÄNSAD LED sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    sensors = [
        IkeaLedRotationSensor(coordinator, entry),
        IkeaLedActivePluginSensor(coordinator, entry),
        IkeaLedScheduleStatusSensor(coordinator, entry),
        IkeaLedBrightnessSensor(coordinator, entry),
    ]
    
    async_add_entities(sensors)


class IkeaLedBaseSensor(CoordinatorEntity[IkeaLedCoordinator], SensorEntity):
    """Base class for IKEA OBEGRÄNSAD LED sensors."""

    def __init__(
        self,
        coordinator: IkeaLedCoordinator,
        entry: ConfigEntry,
        sensor_type: str,
        name: str,
        icon: str | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._sensor_type = sensor_type
        self._attr_unique_id = f"{entry.entry_id}_{sensor_type}"
        self._attr_name = f"IKEA OBEGRÄNSAD {name}"
        if icon:
            self._attr_icon = icon

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name="IKEA OBEGRÄNSAD LED",
            manufacturer="IKEA (Modified)",
            model="OBEGRÄNSAD",
            configuration_url=f"http://{self.coordinator.host}",
        )


class IkeaLedRotationSensor(IkeaLedBaseSensor):
    """Sensor for current rotation value."""

    def __init__(self, coordinator: IkeaLedCoordinator, entry: ConfigEntry) -> None:
        """Initialize the rotation sensor."""
        super().__init__(
            coordinator, 
            entry, 
            "rotation", 
            "Rotation",
            "mdi:rotate-3d-variant"
        )
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        """Return the current rotation value."""
        if not self.coordinator.data:
            return None
        return (90 * self.coordinator.data.get("rotation")) % 360

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return "°"


class IkeaLedActivePluginSensor(IkeaLedBaseSensor):
    """Sensor for current active plugin."""

    def __init__(self, coordinator: IkeaLedCoordinator, entry: ConfigEntry) -> None:
        """Initialize the active plugin sensor."""
        super().__init__(
            coordinator,
            entry,
            "active_plugin",
            "Active Plugin",
            "mdi:puzzle"
        )

    @property
    def native_value(self) -> str | None:
        """Return the current active plugin name."""
        if not self.coordinator.data:
            return None
            
        plugin_id = self.coordinator.data.get("plugin")
        if plugin_id is None:
            return None
            
        # Find the plugin name from available plugins
        plugins = self.coordinator.data.get("plugins", [])
        for plugin in plugins:
            if plugin.get("id") == plugin_id:
                return plugin.get("name", f"Plugin {plugin_id}")
                
        return f"Plugin {plugin_id}"

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return None
        attrs = {
            "plugin_id": self.coordinator.data.get("plugin"),
            "available_plugins": [
                {"id": plugin.get("id"), "name": plugin.get("name", "Unknown")}
                for plugin in self.coordinator.data.get("plugins", [])
            ],
        }

        # Include persisted plugin id if the device reports it
        persisted = self.coordinator.data.get("persistPlugin")
        if persisted is not None:
            attrs["persisted_plugin_id"] = persisted

        return attrs


class IkeaLedScheduleStatusSensor(IkeaLedBaseSensor):
    """Sensor for schedule status."""

    def __init__(self, coordinator: IkeaLedCoordinator, entry: ConfigEntry) -> None:
        """Initialize the schedule status sensor."""
        super().__init__(
            coordinator,
            entry,
            "schedule_status",
            "Schedule Status",
            "mdi:calendar-clock"
        )
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = ["active", "inactive"]

    @property
    def native_value(self) -> str | None:
        """Return the current schedule status."""
        if not self.coordinator.data:
            return None
            
        schedule_active = self.coordinator.data.get("scheduleActive", False)
        return "active" if schedule_active else "inactive"

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return None
            
        return {
            "schedule": self.coordinator.data.get("schedule", [])
        }


class IkeaLedBrightnessSensor(IkeaLedBaseSensor):
    """Sensor for current brightness value."""

    def __init__(self, coordinator: IkeaLedCoordinator, entry: ConfigEntry) -> None:
        """Initialize the brightness sensor."""
        super().__init__(
            coordinator,
            entry,
            "brightness",
            "Brightness",
            "mdi:brightness-6"
        )
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        """Return the current brightness value."""
        if not self.coordinator.data:
            return None
        brightness_raw = self.coordinator.data.get("brightness")
        return round((brightness_raw / 255) * 100, 1)

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return "%"

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return None
            
        brightness = self.coordinator.data.get("brightness", 0)
        return {
            "brightness_percent": round((brightness / 255) * 100, 1),
            "brightness_raw": brightness,
        }