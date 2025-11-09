"""The IKEA OBEGRÄNSAD LED Control integration."""
from __future__ import annotations

import json
import logging

import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import IkeaLedCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.LIGHT, Platform.SELECT, Platform.SENSOR, Platform.BUTTON]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration and register module-level services.

    Services are registered at module level so they show up in the UI even
    before an entry is configured. Handlers will pick the right coordinator
    based on configured entries.
    """

    def _get_coordinator(host: str | None = None) -> IkeaLedCoordinator | None:
        data = hass.data.get(DOMAIN, {})
        if host:
            for entry_id, coord in data.items():
                if isinstance(coord, IkeaLedCoordinator) and coord.host == host:
                    return coord

        # If only a single coordinator is configured, return it
        coords = [c for c in data.values() if isinstance(c, IkeaLedCoordinator)]
        if len(coords) == 1:
            return coords[0]
        return None

    async def persist_plugin_service(call) -> None:
        host = call.data.get("host")
        coord = _get_coordinator(host)
        if not coord:
            _LOGGER.error("No IKEA OBEGRÄNSAD coordinator found for persist_plugin")
            return
        await hass.async_add_executor_job(coord.persist_plugin)

    async def set_schedule_service(call) -> None:
        host = call.data.get("host")
        schedule = call.data.get("schedule")
        coord = _get_coordinator(host)
        if not coord:
            _LOGGER.error("No IKEA OBEGRÄNSAD coordinator found for set_schedule")
            return
        # Expect schedule as a JSON string in the UI for best frontend support.
        # If callers provide structured data (dict/list), convert to JSON here.
        if not isinstance(schedule, str):
            schedule = json.dumps(schedule)
        await coord.async_set_schedule(schedule)

    async def clear_schedule_service(call) -> None:
        host = call.data.get("host")
        coord = _get_coordinator(host)
        if not coord:
            _LOGGER.error("No IKEA OBEGRÄNSAD coordinator found for clear_schedule")
            return
        await coord.async_clear_schedule()

    async def start_schedule_service(call) -> None:
        host = call.data.get("host")
        coord = _get_coordinator(host)
        if not coord:
            _LOGGER.error("No IKEA OBEGRÄNSAD coordinator found for start_schedule")
            return
        await coord.async_start_schedule()

    async def stop_schedule_service(call) -> None:
        host = call.data.get("host")
        coord = _get_coordinator(host)
        if not coord:
            _LOGGER.error("No IKEA OBEGRÄNSAD coordinator found for stop_schedule")
            return
        await coord.async_stop_schedule()

    async def add_message_service(call) -> None:
        host = call.data.get("host")
        coord = _get_coordinator(host)
        if not coord:
            _LOGGER.error("No IKEA OBEGRÄNSAD coordinator found for add_message")
            return
        text = call.data.get("text")
        repeat = call.data.get("repeat", 1)
        mid = call.data.get("id", 0)
        delay = call.data.get("delay", 50)
        graph = call.data.get("graph")
        miny = call.data.get("miny", 0)
        maxy = call.data.get("maxy", 15)
        # If graph is provided as string (JSON array or CSV), parse into list[int]
        graph_list = None
        if isinstance(graph, str):
            # Try JSON first
            try:
                parsed = json.loads(graph)
                if isinstance(parsed, list):
                    graph_list = [int(x) for x in parsed]
            except Exception:
                # Fallback: parse comma-separated integers
                try:
                    parts = [p.strip() for p in graph.split(",") if p.strip()]
                    graph_list = [int(p) for p in parts]
                except Exception:
                    graph_list = None
        else:
            graph_list = graph

        await coord.async_add_message(text, repeat, mid, delay, graph_list, miny, maxy)

    async def remove_message_service(call) -> None:
        host = call.data.get("host")
        coord = _get_coordinator(host)
        if not coord:
            _LOGGER.error("No IKEA OBEGRÄNSAD coordinator found for remove_message")
            return
        mid = call.data.get("id")
        await coord.async_remove_message(mid)

    async def clear_storage_service(call) -> None:
        host = call.data.get("host")
        coord = _get_coordinator(host)
        if not coord:
            _LOGGER.error("No IKEA OBEGRÄNSAD coordinator found for clear_storage")
            return
        await coord.async_clear_storage()

    async def get_data_service(call) -> None:
        host = call.data.get("host")
        coord = _get_coordinator(host)
        if not coord:
            _LOGGER.error("No IKEA OBEGRÄNSAD coordinator found for get_data")
            return
        data = await coord.async_get_data()
        if not data:
            _LOGGER.error("Failed to fetch data from device")
            return
        try:
            hass_config = hass.config.path()
            outpath = f"{hass_config}/ikea_obegraensad_data.bin"
            with open(outpath, "wb") as f:
                f.write(data)
            _LOGGER.info("Saved device data to %s", outpath)
        except Exception as ex:
            _LOGGER.error("Failed to save device data: %s", ex)

    # Service schemas (use selector objects for better UI rendering)
    persist_schema = vol.Schema({vol.Optional("host"): selector.TextSelector({})})
    set_schedule_schema = vol.Schema(
        {
            vol.Optional("host"): selector.TextSelector({}),
            vol.Required("schedule"): selector.TextSelector({"multiline": True}),
        }
    )
    simple_host_schema = vol.Schema({vol.Optional("host"): selector.TextSelector({})})
    add_message_schema = vol.Schema(
        {
            vol.Optional("host"): selector.TextSelector({}),
            vol.Required("text"): selector.TextSelector({"multiline": True}),
            vol.Optional("repeat", default=1): selector.NumberSelector({"min": 1, "max": 1000}),
            vol.Optional("id", default=0): selector.NumberSelector({"min": 0, "max": 65535}),
            vol.Optional("delay", default=50): selector.NumberSelector({"min": 0, "max": 10000}),
            vol.Optional("graph"): selector.TextSelector({}),
            vol.Optional("miny", default=0): selector.NumberSelector({"min": -32768, "max": 32767}),
            vol.Optional("maxy", default=15): selector.NumberSelector({"min": -32768, "max": 32767}),
        }
    )
    remove_message_schema = vol.Schema(
        {vol.Optional("host"): selector.TextSelector({}), vol.Required("id"): selector.NumberSelector({"min": 0, "max": 65535})}
    )

    hass.services.async_register(DOMAIN, "persist_plugin", persist_plugin_service, schema=persist_schema)
    hass.services.async_register(DOMAIN, "set_schedule", set_schedule_service, schema=set_schedule_schema)
    hass.services.async_register(DOMAIN, "clear_schedule", clear_schedule_service, schema=simple_host_schema)
    hass.services.async_register(DOMAIN, "start_schedule", start_schedule_service, schema=simple_host_schema)
    hass.services.async_register(DOMAIN, "stop_schedule", stop_schedule_service, schema=simple_host_schema)
    hass.services.async_register(DOMAIN, "add_message", add_message_service, schema=add_message_schema)
    hass.services.async_register(DOMAIN, "remove_message", remove_message_service, schema=remove_message_schema)
    hass.services.async_register(DOMAIN, "clear_storage", clear_storage_service, schema=simple_host_schema)
    hass.services.async_register(DOMAIN, "get_data", get_data_service, schema=simple_host_schema)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry (per device)."""
    host = entry.data[CONF_HOST]
    coordinator = IkeaLedCoordinator(hass, host)

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        _LOGGER.exception("Error setting up IKEA OBEGRÄNSAD LED device")
        raise

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.async_shutdown()
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
