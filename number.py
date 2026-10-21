"""Pulse duration settings (1-10 s) for the C3 pulse buttons."""

from __future__ import annotations

from homeassistant.components.number import NumberMode, RestoreNumber
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    DEFAULT_PULSE_DURATION_AUX,
    DEFAULT_PULSE_DURATION_DOOR,
    MAX_PULSE_DURATION,
    MIN_PULSE_DURATION,
)
from .coordinator import C3ConfigEntry, C3Coordinator
from .entity import C3Entity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: C3ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up pulse duration numbers."""
    coordinator = entry.runtime_data
    entities: list[C3PulseDuration] = [
        C3PulseDuration(coordinator, idx, "door")
        for idx in range(1, coordinator.panel.nr_of_locks + 1)
    ]
    entities.extend(
        C3PulseDuration(coordinator, idx, "aux")
        for idx in range(1, coordinator.panel.nr_aux_out + 1)
    )
    async_add_entities(entities)


class C3PulseDuration(C3Entity, RestoreNumber):
    """Relay activation time used by the matching pulse button."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = MIN_PULSE_DURATION
    _attr_native_max_value = MAX_PULSE_DURATION
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_icon = "mdi:timer-outline"

    def __init__(self, coordinator: C3Coordinator, idx: int, kind: str) -> None:
        """Initialize the number."""
        super().__init__(coordinator, idx, f"pulse_time_{kind}")
        self._key = f"{kind}{idx}"
        default = (
            DEFAULT_PULSE_DURATION_DOOR if kind == "door" else DEFAULT_PULSE_DURATION_AUX
        )
        if kind == "door":
            self._attr_name = f"Door {idx} pulse time"
        else:
            self._attr_name = f"Auxiliary Output {idx} pulse time"
        self._attr_native_value = float(default)
        coordinator.pulse_durations[self._key] = default

    async def async_added_to_hass(self) -> None:
        """Restore the last set value."""
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        if last is not None and last.native_value is not None:
            value = int(
                max(MIN_PULSE_DURATION, min(MAX_PULSE_DURATION, last.native_value))
            )
            self._attr_native_value = float(value)
            self.coordinator.pulse_durations[self._key] = value
            self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Value is local, only availability follows the coordinator."""
        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        """Set a new pulse duration."""
        self._attr_native_value = float(int(value))
        self.coordinator.pulse_durations[self._key] = int(value)
        self.async_write_ha_state()
