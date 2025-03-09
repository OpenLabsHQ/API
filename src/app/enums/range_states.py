from enum import Enum


class RangeState(Enum):
    """OpenLabs supported cloud regions."""

    ON = "on"
    OFF = "off"
    START = "start"
    STOP = "stop"
