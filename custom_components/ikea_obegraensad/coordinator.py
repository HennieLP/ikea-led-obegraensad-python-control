"""Data update coordinator for IKEA OBEGRÄNSAD LED Control."""
from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from datetime import timedelta
from typing import Any, Dict, Optional

import websockets
import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class IkeaLedCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching data from the IKEA OBEGRÄNSAD LED device."""

    def __init__(self, hass: HomeAssistant, host: str) -> None:
        """Initialize."""
        self.host = host
        self.base_url = f"http://{host}/api"
        self.ws_url = f"ws://{host}/ws"
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.ws_connected = False
        self._state = {
            "brightness": 0,
            "rotation": 0,
            "plugin": None,
            # persisted plugin id if device reports it
            "persistPlugin": None,
            "scheduleActive": False,
            "schedule": [],
            "plugins": []
        }
        self._ws_lock = threading.Lock()
        self._last_state = {}
        self._ws_thread = None
        self._monitor_thread = None
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),  # WebSocket provides real-time updates
        )
        
        # Start WebSocket and monitoring after coordinator is initialized
        self._start_websocket()
        self._start_monitoring()

    def _start_websocket(self):
        """Start the WebSocket connection in a background thread."""
        def run_async_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._websocket_loop())
        
        self._ws_thread = threading.Thread(target=run_async_loop, daemon=True)
        self._ws_thread.start()

    def _start_monitoring(self):
        """Start the state monitoring in a background thread."""
        def monitor_changes():
            while True:
                try:
                    with self._ws_lock:
                        current_state = dict(self._state)
                    
                    # Check for changes and trigger coordinator updates
                    changes_detected = False
                    for key, value in current_state.items():
                        if key not in self._last_state or self._last_state[key] != value:
                            if key in self._last_state:  # Don't log initial values
                                _LOGGER.debug("Change detected: %s changed from %s to %s", 
                                             key, self._last_state[key], value)
                                changes_detected = True
                            self._last_state[key] = value
                    
                    # Notify coordinator of changes
                    if changes_detected:
                        self.hass.loop.call_soon_threadsafe(
                            lambda: self.hass.async_create_task(self._on_websocket_change())
                        )
                    
                    time.sleep(0.5)  # Check every 500ms
                except Exception as ex:
                    _LOGGER.debug("Error in monitoring loop: %s", ex)
                    time.sleep(1)
        
        self._monitor_thread = threading.Thread(target=monitor_changes, daemon=True)
        self._monitor_thread.start()

    async def _websocket_loop(self):
        """Main WebSocket connection loop."""
        while True:
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    self.websocket = websocket
                    self.ws_connected = True
                    _LOGGER.debug("WebSocket connected to %s", self.ws_url)
                    
                    while True:
                        try:
                            message = await websocket.recv()
                            await self._handle_ws_message(message)
                        except websockets.ConnectionClosed:
                            break
            except Exception as ex:
                _LOGGER.debug("WebSocket connection error: %s", ex)
            finally:
                self.ws_connected = False
                self.websocket = None
            
            # Wait before reconnecting
            await asyncio.sleep(5)

    async def _handle_ws_message(self, message: str):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(message)
            with self._ws_lock:
                if "brightness" in data:
                    self._state["brightness"] = data["brightness"]
                if "rotation" in data:
                    self._state["rotation"] = data["rotation"]
                if "plugin" in data:
                    self._state["plugin"] = data["plugin"]
                if "scheduleActive" in data:
                    self._state["scheduleActive"] = data["scheduleActive"]
                if "schedule" in data:
                    self._state["schedule"] = data["schedule"]
                if "plugins" in data:
                    self._state["plugins"] = data["plugins"]
                if "persist-plugin" in data:
                    # firmware sends 'persist-plugin' (hyphen); store under persistPlugin
                    self._state["persistPlugin"] = data["persist-plugin"]
        except json.JSONDecodeError as ex:
            _LOGGER.warning("Error parsing WebSocket message: %s", ex)

    async def async_get_data(self) -> bytes | None:
        """Fetch raw render buffer from device via HTTP `GET /api/data`.

        Returns raw bytes on success, or None on failure.
        """
        url = f"{self.base_url}/data"
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(url, timeout=15) as resp:
                if resp.status == 200:
                    return await resp.read()
                _LOGGER.debug("GET %s returned status %s", url, resp.status)
                return None
        except Exception as ex:
            _LOGGER.debug("Failed to fetch data from %s: %s", url, ex)
            return None

    async def _send_ws_message(self, data: Dict[str, Any]):
        """Send a message through the WebSocket connection."""
        if not self.ws_connected or not self.websocket:
            raise ConnectionError("WebSocket connection is not available")
        
        try:
            await self.websocket.send(json.dumps(data))
        except websockets.ConnectionClosed:
            _LOGGER.debug("WebSocket connection closed while sending message")
            self.ws_connected = False
            raise
        except Exception as ex:
            _LOGGER.warning("Error sending WebSocket message: %s", ex)
            raise

    def _send_ws_command(self, data: Dict[str, Any]) -> None:
        """Helper method to send WebSocket commands."""
        if not self.ws_connected:
            raise ConnectionError("WebSocket connection is not available")
        
        # Create a new event loop for this thread
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._send_ws_message(data))
        finally:
            loop.close()

    async def _on_websocket_change(self) -> None:
        """Handle WebSocket state changes."""
        try:
            # Update the coordinator's data with current state
            with self._ws_lock:
                current_data = dict(self._state)
            
            self.data = current_data
            self.async_update_listeners()
            _LOGGER.debug("WebSocket change triggered HA update")
                
        except Exception as ex:
            _LOGGER.debug("Failed to handle WebSocket change: %s", ex)

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via WebSocket state."""
        try:
            # Return current state from WebSocket
            with self._ws_lock:
                current_state = dict(self._state)
            
            # Log WebSocket connection status
            ws_status = "connected" if self.ws_connected else "disconnected"
            _LOGGER.debug("Data update completed, WebSocket: %s", ws_status)
            
            return current_state
            
        except Exception as ex:
            _LOGGER.exception("Error fetching data from IKEA LED device")
            raise UpdateFailed(f"Error communicating with device at {self.host}: {ex}") from ex

    # LED Control Methods
    def set_brightness(self, brightness: int) -> None:
        """Set the brightness value (0-255)."""
        if not (0 <= brightness <= 255):
            raise ValueError("Brightness must be between 0 and 255")
        
        self._send_ws_command({
            "event": "brightness",
            "brightness": brightness
        })

    def set_plugin(self, plugin_id: int) -> None:
        """Set the active plugin."""
        self._send_ws_command({
            "event": "plugin",
            "plugin": plugin_id
        })

    def set_rotation(self, direction: str) -> None:
        """Rotate the display (direction should be 'left' or 'right')."""
        if direction not in ['left', 'right']:
            raise ValueError("Direction must be either 'left' or 'right'")
        
        self._send_ws_command({
            "event": "rotate",
            "direction": direction
        })

    def persist_plugin(self) -> None:
        """Persist the currently active plugin on the device.

        This triggers the device to save the active plugin as the persisted choice
        (handled by the firmware's pluginManager.persistActivePlugin()).
        """
        self._send_ws_command({
            "event": "persist-plugin"
        })

    # State Access Methods
    def get_brightness(self) -> int:
        """Get the current brightness value (0-255)."""
        with self._ws_lock:
            return self._state["brightness"]

    def get_rotation(self) -> int:
        """Get the current rotation value (0-3)."""
        with self._ws_lock:
            return self._state["rotation"]

    def get_active_plugin(self) -> Optional[int]:
        """Get the currently active plugin ID."""
        with self._ws_lock:
            return self._state["plugin"]

    def get_available_plugins(self) -> list:
        """Get list of available plugins."""
        with self._ws_lock:
            return self._state["plugins"]

    def get_schedule_state(self) -> bool:
        """Get whether the schedule is active."""
        with self._ws_lock:
            return self._state["scheduleActive"]

    def get_schedule(self) -> list:
        """Get the current schedule."""
        with self._ws_lock:
            return self._state["schedule"]

    async def async_refresh_after_command(self) -> None:
        """Refresh data after sending a command - WebSocket will handle updates automatically."""
        # Small delay to allow WebSocket to receive the update
        await asyncio.sleep(0.1)

    async def async_shutdown(self) -> None:
        """Shutdown coordinator."""
        self.ws_connected = False
        _LOGGER.info("Shutting down IKEA LED coordinator")

    # --- HTTP helper methods to call firmware API endpoints ---
    async def async_set_schedule(self, schedule_json: str) -> bool:
        """Send schedule JSON string to device via HTTP POST.

        The firmware expects form-data with key 'schedule'. Returns True on success.
        """
        url = f"{self.base_url}/schedule"
        session = async_get_clientsession(self.hass)
        try:
            async with session.post(url, data={"schedule": schedule_json}, timeout=10) as resp:
                return resp.status == 200
        except aiohttp.ClientError as ex:
            _LOGGER.debug("Failed to set schedule via %s: %s", url, ex)
            return False

    async def async_clear_schedule(self) -> bool:
        url = f"{self.base_url}/schedule/clear"
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(url, timeout=10) as resp:
                return resp.status == 200
        except aiohttp.ClientError as ex:
            _LOGGER.debug("Failed to clear schedule: %s", ex)
            return False

    async def async_start_schedule(self) -> bool:
        url = f"{self.base_url}/schedule/start"
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(url, timeout=10) as resp:
                return resp.status == 200
        except aiohttp.ClientError as ex:
            _LOGGER.debug("Failed to start schedule: %s", ex)
            return False

    async def async_stop_schedule(self) -> bool:
        url = f"{self.base_url}/schedule/stop"
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(url, timeout=10) as resp:
                return resp.status == 200
        except aiohttp.ClientError as ex:
            _LOGGER.debug("Failed to stop schedule: %s", ex)
            return False

    async def async_add_message(self, text: str, repeat: int = 1, id: int = 0, delay: int = 50, graph: list | None = None, miny: int = 0, maxy: int = 15) -> bool:
        """Add a message via the HTTP API. graph is a list of ints converted to CSV string."""
        url = f"{self.base_url}/message"
        params = {
            "text": text,
            "repeat": str(repeat),
            "id": str(id),
            "delay": str(delay),
            "miny": str(miny),
            "maxy": str(maxy),
        }
        if graph:
            params["graph"] = ",".join(str(x) for x in graph)

        session = async_get_clientsession(self.hass)
        try:
            async with session.get(url, params=params, timeout=10) as resp:
                return resp.status == 200
        except aiohttp.ClientError as ex:
            _LOGGER.debug("Failed to add message: %s", ex)
            return False

    async def async_remove_message(self, id: int) -> bool:
        url = f"{self.base_url}/removemessage"
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(url, params={"id": str(id)}, timeout=10) as resp:
                return resp.status == 200
        except aiohttp.ClientError as ex:
            _LOGGER.debug("Failed to remove message: %s", ex)
            return False

    async def async_clear_storage(self) -> bool:
        url = f"{self.base_url}/storage/clear"
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(url, timeout=10) as resp:
                return resp.status == 200
        except aiohttp.ClientError as ex:
            _LOGGER.debug("Failed to clear storage: %s", ex)
            return False