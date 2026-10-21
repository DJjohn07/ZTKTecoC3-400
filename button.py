"""Pulse buttons for C3 door and auxiliary relays.

One press activates the relay for the duration set in the matching number
entity (1-10 s). The panel switches the relay off by itself, so the pulse
ends correctly even if Home Assistant loses the connection meanwhile.
"""

from __future__ import annotations

from c3.consts import ControlOutputAddress
from c3.controldevice import ControlDeviceOutput

from homeassistant.components.button import ButtonEntity
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

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: C3ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up pulse buttons."""
    coordinator = entry.runtime_data
    entities: list[C3PulseButton] = [
        C3PulseButton(coordinator, idx, "door")
        for idx in range(1, coordinator.panel.nr_of_locks + 1)
    ]
    entities.extend(
        C3PulseButton(coordinator, idx, "aux")
        for idx in range(1, coordinator.panel.nr_aux_out + 1)
    )
    async_add_entities(entities)


class C3PulseButton(C3Entity, ButtonEntity):
    """Button that activates a door or auxiliary relay for a set time."""

    def __init__(self, coordinator: C3Coordinator, idx: int, kind: str) -> None:
        """Initialize the button."""
        super().__init__(coordinator, idx, f"pulse_{kind}")
        self._kind = kind
        if kind == "door":
            self._address = ControlOutputAddress.DOOR_OUTPUT
            self._default = DEFAULT_PULSE_DURATION_DOOR
            self._attr_name = f"Door {idx} pulse"
            self._attr_icon = "mdi:door-open"
        else:
            self._address = ControlOutputAddress.AUX_OUTPUT
            self._default = DEFAULT_PULSE_DURATION_AUX
            self._attr_name = f"Auxiliary Output {idx} pulse"
            self._attr_icon = "mdi:gesture-tap-button"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Buttons have no state, only availability follows the coordinator."""
        self.async_write_ha_state()

    async def async_press(self) -> None:
        """Send one pulse to the relay."""
        duration = self.coordinator.pulse_durations.get(
            f"{self._kind}{self._idx}", self._default
        )
        duration = max(MIN_PULSE_DURATION, min(MAX_PULSE_DURATION, int(duration)))
        await self.coordinator.async_send_command(
            ControlDeviceOutput(self._idx, self._address, duration)
        )
