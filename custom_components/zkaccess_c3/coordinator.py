"""Coordinator for the ZKAccess C3 panel."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import threading
from collections.abc import Iterator
from datetime import timedelta

from c3 import C3, rtlog
from c3.consts import EventType
from c3.controldevice import ControlDeviceBase

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_AUX_ON_DURATION,
    CONF_UNLOCK_DURATION,
    DEFAULT_AUX_ON_DURATION,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_UNLOCK_DURATION,
    DOMAIN,
    IO_LOCK_TIMEOUT,
    MAX_OUTPUT_DURATION,
    MAX_POLL_INTERVAL,
    MAX_FAILED_POLLS,
    MAX_RTLOG_READS,
    MIN_OUTPUT_DURATION,
    MIN_POLL_INTERVAL,
    POLL_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)
# Logger used by the zkaccess_c3 library. At DEBUG level it logs every raw
# frame in hex, including the login frame that carries the password.
_C3_LOGGER = logging.getLogger("C3")

_AUX_EVENTS = (
    EventType.OPEN_AUX_OUTPUT,
    EventType.CLOSE_AUX_OUTPUT,
    EventType.AUX_INPUT_DISCONNECT,
    EventType.AUX_INPUT_SHORT,
)

type C3ConfigEntry = ConfigEntry[C3Coordinator]


def _clamp(value: int | None, default: int, minimum: int, maximum: int) -> int:
    """Return value limited to the given range, or default when not set."""
    if value is None:
        return default
    return max(minimum, min(maximum, int(value)))


@contextlib.contextmanager
def _no_c3_debug_logging() -> Iterator[None]:
    """Temporarily block library debug output, so the password is never logged."""
    previous = _C3_LOGGER.level
    _C3_LOGGER.setLevel(max(previous, logging.INFO))
    try:
        yield
    finally:
        _C3_LOGGER.setLevel(previous)


class C3Coordinator(DataUpdateCoordinator[bool]):
    """ZKAccess C3 panel coordinator.

    All communication with the panel is blocking socket I/O. It runs in the
    executor and is serialized with a lock, because the panel protocol does
    not allow concurrent requests on one session.
    """

    config_entry: C3ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: C3ConfigEntry) -> None:
        """Initialize C3 coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.data[CONF_HOST]}",
            update_interval=timedelta(
                seconds=_clamp(
                    entry.options.get(CONF_SCAN_INTERVAL),
                    DEFAULT_POLL_INTERVAL,
                    MIN_POLL_INTERVAL,
                    MAX_POLL_INTERVAL,
                )
            ),
        )
        self._host: str = entry.data[CONF_HOST]
        self._port: int = entry.data[CONF_PORT]
        self._password: str = entry.data.get(CONF_PASSWORD) or ""
        self._io_lock = threading.Lock()
        self._failed_polls = 0
        self._door_events: dict[int, rtlog.EventRecord] = {}
        # Pulse durations per output, keyed "door1".."door4", "aux1".."aux4".
        # Filled by the number entities (restored after restart).
        self.pulse_durations: dict[str, int] = {}

        self.panel = C3(self._host, self._port)
        self.status = rtlog.DoorAlarmStatusRecord()
        self.unlock_duration = _clamp(
            entry.options.get(CONF_UNLOCK_DURATION),
            DEFAULT_UNLOCK_DURATION,
            MIN_OUTPUT_DURATION,
            MAX_OUTPUT_DURATION,
        )
        self.aux_on_duration = _clamp(
            entry.options.get(CONF_AUX_ON_DURATION),
            DEFAULT_AUX_ON_DURATION,
            MIN_OUTPUT_DURATION,
            MAX_OUTPUT_DURATION,
        )

    @property
    def device_id(self) -> str:
        """Return a stable identifier of the panel."""
        return self.panel.serial_number or self.config_entry.entry_id

    def last_door_event(self, door_id: int) -> rtlog.EventRecord:
        """Return the last received event for a door."""
        return self._door_events.get(door_id) or rtlog.EventRecord()

    # --- Blocking helpers, call only from the executor --------------------

    def _connect(self) -> bool:
        """Open a session. Caller must hold the I/O lock."""
        with _no_c3_debug_logging():
            return self.panel.connect(self._password)

    def _disconnect(self) -> None:
        """Close the session, ignoring errors. Caller must hold the I/O lock."""
        with contextlib.suppress(Exception):
            self.panel.disconnect()

    def _acquire(self) -> bool:
        return self._io_lock.acquire(timeout=IO_LOCK_TIMEOUT)

    def setup_panel(self) -> None:
        """Connect and read the panel configuration."""
        if not self._acquire():
            raise ConfigEntryNotReady("C3 panel connection is busy")
        try:
            if not self._connect():
                raise ConfigEntryNotReady(
                    f"Cannot connect to C3 panel at {self._host}:{self._port}"
                )
            if self.panel.nr_of_locks:
                # Reads and caches the settings of all doors.
                self.panel.door_settings(1)
        except (OSError, ValueError) as err:
            self._disconnect()
            raise ConfigEntryNotReady(f"C3 panel setup failed: {err}") from err
        finally:
            self._io_lock.release()

    def close(self) -> None:
        """Close the session to the panel."""
        if self._acquire():
            try:
                self._disconnect()
            finally:
                self._io_lock.release()

    def _read_rt_log(self) -> None:
        """Read the realtime log until a door/alarm status record arrives.

        The panel may answer with an empty log (nothing new, or the library
        is switching from binary to key/value mode on firmware 4.x). That is
        a valid answer, not an error: the previous status is kept.
        """
        for _ in range(MAX_RTLOG_READS):
            for log in self.panel.get_rt_log():
                if isinstance(log, rtlog.DoorAlarmStatusRecord):
                    self.status = log
                    return
                if (
                    isinstance(log, rtlog.EventRecord)
                    and log.port_nr > 0
                    and log.event_type not in _AUX_EVENTS
                ):
                    self._door_events[log.port_nr] = log

    def _poll(self) -> bool:
        """Poll the panel; reconnect once when the session has died."""
        if not self._acquire():
            raise UpdateFailed("C3 panel connection is busy")
        try:
            last_err: Exception | None = None
            for _attempt in range(2):
                try:
                    if not self.panel.is_connected() and not self._connect():
                        raise ConnectionError(
                            f"Cannot connect to C3 panel at {self._host}:{self._port}"
                        )
                    self._read_rt_log()
                    return True
                except (OSError, ValueError) as err:
                    last_err = err
                    _LOGGER.debug("C3 poll failed, reconnecting: %s", err)
                    self._disconnect()
            raise UpdateFailed(f"Communication with C3 panel failed: {last_err}")
        finally:
            self._io_lock.release()

    def _send_command(self, command: ControlDeviceBase) -> None:
        """Send a control command to the panel.

        The panel silently drops idle sessions, so the library may still
        report a connection that is already dead. When the first attempt
        fails, the session is reopened and the command is sent once more.
        """
        if not self._acquire():
            raise HomeAssistantError("C3 panel connection is busy")
        try:
            last_err: Exception | None = None
            for _attempt in range(2):
                try:
                    if not self.panel.is_connected() and not self._connect():
                        raise ConnectionError(
                            f"Cannot connect to C3 panel at {self._host}:{self._port}"
                        )
                    self.panel.control_device(command)
                    return
                except (OSError, ValueError) as err:
                    last_err = err
                    _LOGGER.debug("C3 command failed, reconnecting: %s", err)
                    self._disconnect()
            raise HomeAssistantError(f"C3 panel command failed: {last_err}")
        finally:
            self._io_lock.release()

    # --- Async API ----------------------------------------------------------

    async def _async_update_data(self) -> bool:
        """Fetch the realtime log from the panel.

        Single failed polls are tolerated: entities keep their last state and
        become unavailable only after MAX_FAILED_POLLS failures in a row.
        """
        try:
            async with asyncio.timeout(POLL_TIMEOUT):
                result = await self.hass.async_add_executor_job(self._poll)
        except (TimeoutError, UpdateFailed) as err:
            self._failed_polls += 1
            if self.data is not None and self._failed_polls < MAX_FAILED_POLLS:
                _LOGGER.debug(
                    "C3 poll failed (%d/%d): %s",
                    self._failed_polls,
                    MAX_FAILED_POLLS,
                    err,
                )
                return self.data
            if isinstance(err, UpdateFailed):
                raise
            raise UpdateFailed("Timeout while polling C3 panel") from err
        self._failed_polls = 0
        return result

    async def async_send_command(self, command: ControlDeviceBase) -> None:
        """Send a control command and refresh the state afterwards."""
        await self.hass.async_add_executor_job(self._send_command, command)
        await self.async_request_refresh()
