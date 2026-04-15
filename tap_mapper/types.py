from dataclasses import dataclass
from enum import Enum


class ButtonEventType(str, Enum):
    BUTTON_PRESSED = "BUTTON_PRESSED"
    BUTTON_RELEASED = "BUTTON_RELEASED"


class ScaleMode(str, Enum):
    MINOR_PENTATONIC = "MINOR_PENTATONIC"
    MAJOR_PENTATONIC = "MAJOR_PENTATONIC"
    MAJOR = "MAJOR"
    MINOR = "MINOR"


@dataclass(frozen=True)
class ButtonEvent:
    event_type: ButtonEventType
    timestamp_milliseconds: int

