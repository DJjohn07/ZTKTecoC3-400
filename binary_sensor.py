"""Binary sensor entities for C3 auxiliary inputs."""

from __future__ import annotations

from c3.consts import InOutStatus

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import C3ConfigEntry, C3Coordinator
from .entity import C3Entity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: C3ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up C3 auxiliary inputs."""
    coordinator = entry.runtime_data
    async_add_entities(
        C3AuxInEntity(coordinator, idx)
        for idx in range(1, coordinator.panel.nr_aux_in + 1)
    )


class C3AuxInEntity(C3Entity, BinarySensorEntity):
    """Entity representing a C3 panel auxiliary input."""

    _attr_device_class = BinarySensorDeviceClass.DOOR

    def __init__(self, coordinator: C3Coordinator, idx: int) -> None:
        """Initialize the auxiliary input."""
        super().__init__(coordinator, idx, "in")
        self._attr_name = f"Auxiliary Input {idx}"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        status = self.coordinator.panel.aux_in_status(self._idx)
        if status == InOutStatus.OPEN:
            self._attr_is_on = True
        elif status == InOutStatus.CLOSED:
            self._attr_is_on = False
        else:
            self._attr_is_on = None
        self.async_write_ha_state()
