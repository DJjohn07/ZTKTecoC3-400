"""The ZKAccess C3 integration."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from .const import SUPPORTED_PLATFORMS
from .coordinator import C3ConfigEntry, C3Coordinator


async def async_setup_entry(hass: HomeAssistant, entry: C3ConfigEntry) -> bool:
    """Set up a C3 panel from a config entry."""
    coordinator = C3Coordinator(hass, entry)
    await hass.async_add_executor_job(coordinator.setup_panel)

    async def _async_close() -> None:
        await hass.async_add_executor_job(coordinator.close)

    entry.async_on_unload(_async_close)

    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, SUPPORTED_PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: C3ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, SUPPORTED_PLATFORMS)


async def _async_options_updated(hass: HomeAssistant, entry: C3ConfigEntry) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
