"""Button platform for IKEA OBEGRÄNSAD LED Control."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
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
    """Set up the IKEA OBEGRÄNSAD LED button platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    buttons = [
        IkeaLedRotateLeftButton(coordinator, entry),
        IkeaLedRotateRightButton(coordinator, entry),
    ]
    # Add persist plugin button for easier UI access
    buttons.append(IkeaLedPersistPluginButton(coordinator, entry))
    
    async_add_entities(buttons)


class IkeaLedBaseButton(CoordinatorEntity[IkeaLedCoordinator], ButtonEntity):
    """Base class for IKEA OBEGRÄNSAD LED buttons."""

    def __init__(
        self,
        coordinator: IkeaLedCoordinator,
        entry: ConfigEntry,
        button_type: str,
        name: str,
        icon: str | None = None,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._entry = entry
        self._button_type = button_type
        self._attr_unique_id = f"{entry.entry_id}_{button_type}"
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


class IkeaLedRotateLeftButton(IkeaLedBaseButton):
    """Button to rotate display left."""

    def __init__(self, coordinator: IkeaLedCoordinator, entry: ConfigEntry) -> None:
        """Initialize the rotate left button."""
        super().__init__(
            coordinator,
            entry,
            "rotate_left",
            "Rotate Left",
            "mdi:rotate-left"
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        try:
            await self.hass.async_add_executor_job(
                self.coordinator.set_rotation, "left"
            )
            # Gentle refresh to ensure UI updates
            await self.coordinator.async_refresh_after_command()
        except Exception as ex:
            _LOGGER.error("Failed to rotate left: %s", ex)


class IkeaLedRotateRightButton(IkeaLedBaseButton):
    """Button to rotate display right."""

    def __init__(self, coordinator: IkeaLedCoordinator, entry: ConfigEntry) -> None:
        """Initialize the rotate right button."""
        super().__init__(
            coordinator,
            entry,
            "rotate_right",
            "Rotate Right",
            "mdi:rotate-right"
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        try:
            await self.hass.async_add_executor_job(
                self.coordinator.set_rotation, "right"
            )
            # Gentle refresh to ensure UI updates
            await self.coordinator.async_refresh_after_command()
        except Exception as ex:
            _LOGGER.error("Failed to rotate right: %s", ex)


class IkeaLedPersistPluginButton(IkeaLedBaseButton):
    """Button to persist the currently active plugin on device."""

    def __init__(self, coordinator: IkeaLedCoordinator, entry: ConfigEntry) -> None:
        super().__init__(
            coordinator,
            entry,
            "persist_plugin",
            "Persist Plugin",
            "mdi:content-save"
        )

    async def async_press(self) -> None:
        try:
            await self.hass.async_add_executor_job(
                self.coordinator.persist_plugin
            )
            # Gentle refresh
            await self.coordinator.async_refresh_after_command()
        except Exception as ex:
            _LOGGER.error("Failed to persist plugin: %s", ex)