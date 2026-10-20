"""Constants for ZKAccess C3 integration."""

from homeassistant.const import Platform

DOMAIN = "zkaccess_c3"
MANUFACTURER = "ZKTeco"

SUPPORTED_PLATFORMS: list[Platform] = [
    Platform.LOCK,
    Platform.SWITCH,
    Platform.BINARY_SENSOR,
]

CONF_UNLOCK_DURATION = "unlock_duration"
CONF_AUX_ON_DURATION = "aux_on_duration"

DEFAULT_POLL_INTERVAL = 15
DEFAULT_UNLOCK_DURATION = 3
DEFAULT_AUX_ON_DURATION = 33

MIN_POLL_INTERVAL = 2
MAX_POLL_INTERVAL = 3600

# The panel interprets duration 255 as "normal open" (door stays open
# permanently) and 0 as "close". Valid timed activation is 1..254 seconds.
MIN_OUTPUT_DURATION = 1
MAX_OUTPUT_DURATION = 254

# Maximum time to wait for exclusive access to the panel connection.
IO_LOCK_TIMEOUT = 10
# Maximum time for one poll cycle.
POLL_TIMEOUT = 15
# Maximum number of RT log reads per poll cycle.
MAX_RTLOG_READS = 10
