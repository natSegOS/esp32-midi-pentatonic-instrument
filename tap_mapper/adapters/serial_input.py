from collections.abc import Iterator

import serial

from tap_mapper.config import SerialConfig
from tap_mapper.types import ButtonEvent, ButtonEventType


SERIAL_PRESS_TOKEN = "DOWN"
SERIAL_RELEASE_TOKEN = "UP"


class SerialInput:
    def __init__(self, config: SerialConfig) -> None:
        self._read_size_bytes = config.read_size_bytes
        self.buffer = b""

        self._serial = serial.Serial(
            config.port,
            config.baud_rate,
            timeout=config.timeout_s
        )

    def read_events(self) -> Iterator[ButtonEvent]:
        chunk = self._serial.read(self._read_size_bytes)
        if not chunk:
            return

        self._buffer += chunk

        while b"\n" in self._buffer:
            raw_line, self._buffer = self._buffer.split(b"\n", 1)
            event = parse_serial_line(raw_line.decode(errors="ignore").strip())

            if event is not None:
                yield event

    def close(self) -> None:
        self._serial.close()


def parse_serial_line(line: str) -> ButtonEvent | None:
    if not line:
        return None

    parts = line.split()

    try:
        if parts == [SERIAL_PRESS_TOKEN, parts[1]]:
            return ButtonEvent(
                event_type=ButtonEventType.PRESS,
                timestamp_ms=int(parts[1])
            )

        if parts == [SERIAL_RELEASE_TOKEN, parts[1]]:
            return ButtonEvent(
                event_type=ButtonEventType.RELEASE,
                timestamp_ms=int(parts[1])
            )
    except (IndexError, ValueError):
        return None

    return None
