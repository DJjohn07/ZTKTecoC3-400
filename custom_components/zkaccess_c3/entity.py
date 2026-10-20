"""Base entity for the ZKAccess C3 integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import C3Coordinator


class C3Entity(CoordinatorEntity[C3Coordinator]):
    """Common properties of all C3 panel entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: C3Coordinator, idx: int, key: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, context=idx)
        self._idx = idx
        panel = coordinator.panel
        device_name = panel.device_name
        if not device_name or device_name == "?":
            device_name = coordinator.config_entry.title
        self._attr_unique_id = f"{coordinator.device_id}-{key}{idx}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_id)},
            manufacturer=MANUFACTURER,
            model="C3/inBio",
            name=device_name,
            serial_number=panel.serial_number,
            sw_version=panel.firmware_version,
        )

    async def async_added_to_hass(self) -> None:
        """Set the initial state from the already fetched data."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()
