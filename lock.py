"""Lock entity implementation for C3 doors."""

from __future__ import annotations

from typing import Any

from c3.consts import ControlOutputAddress, InOutStatus
from c3.controldevice import ControlDeviceOutput

from homeassistant.components.lock import LockEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import C3ConfigEntry, C3Coordinator
from .entity import C3Entity

PARALLEL_UPDATES = 1

_ICON_LOCK = {
    False: "mdi:door-open",
    True: "mdi:door-closed-lock",
    None: "mdi:door",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: C3ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up C3 door locks."""
    coordinator = entry.runtime_data
    async_add_entities(
        C3LockEntity(coordinator, idx)
        for idx in range(1, coordinator.panel.nr_of_locks + 1)
    )


class C3LockEntity(C3Entity, LockEntity):
    """Entity representing a C3 panel door lock."""

    def __init__(self, coordinator: C3Coordinator, idx: int) -> None:
        """Initialize the lock."""
        super().__init__(coordinator, idx, "lock")
        self._attr_name = f"Door {idx}"
        settings = coordinator.panel.door_settings(idx)
        self._attr_extra_state_attributes = {
            "sensor_type": repr(settings.sensor_type),
            "lock_drive_time": settings.lock_drive_time,
            "door_alarm_timeout": settings.door_alarm_timeout,
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        status = self.coordinator.panel.lock_status(self._idx)
        if status == InOutStatus.OPEN:
            self._attr_is_locked = False
        elif status == InOutStatus.CLOSED:
            self._attr_is_locked = True
        else:
            self._attr_is_locked = None
        self._attr_is_locking = False
        self._attr_is_unlocking = False
        self._attr_icon = _ICON_LOCK[self._attr_is_locked]
        self.async_write_ha_state()

    async def async_lock(self, **kwargs: Any) -> None:
        """Close the door output."""
        await self.coordinator.async_send_command(
            ControlDeviceOutput(self._idx, ControlOutputAddress.DOOR_OUTPUT, 0)
        )

    async def async_unlock(self, **kwargs: Any) -> None:
        """Release the door for the configured duration (max. 254 s)."""
        await self.coordinator.async_send_command(
            ControlDeviceOutput(
                self._idx,
                ControlOutputAddress.DOOR_OUTPUT,
                self.coordinator.unlock_duration,
            )
        )
