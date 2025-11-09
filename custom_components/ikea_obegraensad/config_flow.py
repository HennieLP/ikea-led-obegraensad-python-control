"""Config flow for IKEA OBEGRÄNSAD LED Control integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, description={"suggested_value": "192.168.5.60"}): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for IKEA OBEGRÄNSAD LED Control."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            host = user_input[CONF_HOST]
            
            # Test connection
            try:
                await self._test_connection(host)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                # Use a serializable error code for the UI
                errors["base"] = "cannot_connect"
            else:
                # Check if already configured
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(
                    title=f"IKEA OBEGRÄNSAD LED ({host})",
                    data={CONF_HOST: host},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def _test_connection(self, host: str) -> bool:
        """Test if we can connect to the device."""
        try:
            # Import the coordinator to test connection
            from .coordinator import IkeaLedCoordinator
            
            # Create a temporary coordinator for testing
            test_coordinator = IkeaLedCoordinator(self.hass, host)
            
            # Give it time to establish WebSocket connection
            await asyncio.sleep(3)
            
            # Try to get initial data: use async_refresh to avoid ConfigEntryError
            await test_coordinator.async_refresh()
            
            # Check if we got valid data
            if not test_coordinator.data or not isinstance(test_coordinator.data, dict):
                _LOGGER.warning("Device at %s returned invalid data: %s", host, test_coordinator.data)
                raise CannotConnect
            
            # Verify we have expected fields in the response
            required_fields = ["brightness"]  # Minimum required field
            if not any(field in test_coordinator.data for field in required_fields):
                _LOGGER.warning("Device at %s returned unexpected data format: %s", host, test_coordinator.data)
                raise CannotConnect
                
            _LOGGER.info("Successfully connected to IKEA LED device at %s", host)
            
            # Clean up test coordinator
            await test_coordinator.async_shutdown()
            
            return True
            
        except ConnectionError as ex:
            _LOGGER.error("Network connection failed for device at %s: %s", host, ex)
            raise CannotConnect from ex
        except TimeoutError as ex:
            _LOGGER.error("Connection timeout for device at %s: %s", host, ex)
            raise CannotConnect from ex
        except Exception as ex:
            _LOGGER.exception("Error connecting to IKEA LED device at %s", host)
            raise CannotConnect from ex


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""