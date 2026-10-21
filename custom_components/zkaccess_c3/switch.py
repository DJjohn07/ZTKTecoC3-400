"""Switch entities for C3 auxiliary outputs and door alarms."""

from __future__ import annotations

from typing import Any

from c3.consts import ControlOutputAddress, InOutStatus
from c3.controldevice import ControlDeviceCancelAlarms, ControlDeviceOutput

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import C3ConfigEntry, C3Coordinator
from .entity import C3Entity

PARALLEL_UPDATES = 1

_ICON_AUX = {
    False: "mdi:toggle-switch-variant-off",
    True: "mdi:toggle-switch-variant",
    None: "mdi:help-circle-outline",
}
_ICON_ALARM = {
    False: "mdi:alarm-light-off-outline",
    True: "mdi:alarm-light",
    None: "mdi:alarm-light-off-outline",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: C3ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up C3 auxiliary outputs and door alarms."""
    coordinator = entry.runtime_data
    entities: list[SwitchEntity] = [
        C3AuxOutEntity(coordinator, idx)
        for idx in range(1, coordinator.panel.nr_aux_out + 1)
    ]
    entities.extend(
        C3AlarmEntity(coordinator, idx)
        for idx in range(1, coordinator.panel.nr_of_locks + 1)
    )
    async_add_entities(entities)


class C3AuxOutEntity(C3Entity, SwitchEntity):
    """Entity representing a C3 panel auxiliary output."""

    def __init__(self, coordinator: C3Coordinator, idx: int) -> None:
        """Initialize the auxiliary output."""
        super().__init__(coordinator, idx, "out")
        self._attr_name = f"Auxiliary Output {idx}"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        status = self.coordinator.panel.aux_out_status(self._idx)
        if status == InOutStatus.OPEN:
            self._attr_is_on = True
        elif status == InOutStatus.CLOSED:
            self._attr_is_on = False
        else:
            self._attr_is_on = None
        self._attr_icon = _ICON_AUX[self._attr_is_on]
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Activate the output for the configured duration (max. 254 s)."""
        await self.coordinator.async_send_command(
            ControlDeviceOutput(
                self._idx,
                ControlOutputAddress.AUX_OUTPUT,
                self.coordinator.aux_on_duration,
            )
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Deactivate the output."""
        await self.coordinator.async_send_command(
            ControlDeviceOutput(self._idx, ControlOutputAddress.AUX_OUTPUT, 0)
        )


class C3AlarmEntity(C3Entity, SwitchEntity):
    """Entity representing a door alarm. Turning it off cancels all panel alarms."""

    def __init__(self, coordinator: C3Coordinator, idx: int) -> None:
        """Initialize the alarm."""
        super().__init__(coordinator, idx, "alarm")
        self._attr_name = f"Door {idx} alarm"
        self._attr_extra_state_attributes = {
            "last_event_time": None,
            "last_event": None,
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_is_on = self.coordinator.status.has_alarm(self._idx)
        event = self.coordinator.last_door_event(self._idx)
        self._attr_extra_state_attributes = {
            "last_event_time": event.time_second,
            "last_event": repr(event.event_type),
        }
        self._attr_icon = _ICON_ALARM[self._attr_is_on]
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Do nothing, an alarm cannot be raised from Home Assistant."""

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Cancel all alarms on the panel."""
        await self.coordinator.async_send_command(ControlDeviceCancelAlarms())
