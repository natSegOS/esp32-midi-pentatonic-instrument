from collections.abc import Iterator

import serial

from tap_mapper.types import ButtonEvent, ButtonEventType


class SerialButtonEventSource:
    def __init__(
        self,
        *,
        serial_port_name: str,
        baud_rate: int,
        timeout_seconds: float,
    ) -> None:
        self._serial_connection = serial.Serial(serial_port_name, baud_rate, timeout=timeout_seconds)
        self._buffer = b""

    def read_available_events(self) -> Iterator[ButtonEvent]:
        incoming_bytes = self._serial_connection.read(256)
        if not incoming_bytes:
            return

        self._buffer += incoming_bytes

        while b"\n" in self._buffer:
            raw_line_bytes, self._buffer = self._buffer.split(b"\n", 1)
            parsed_event = parse_button_event_from_serial_line(
                raw_line_bytes.decode(errors="ignore").strip()
            )

            if parsed_event is not None:
                yield parsed_event

    def close(self) -> None:
        self._serial_connection.close()


def parse_button_event_from_serial_line(serial_line: str) -> ButtonEvent | None:
    if not serial_line:
        return None

    parts = serial_line.split()

    try:
        if parts[0] == "DOWN" and len(parts) == 2:
            return ButtonEvent(
                event_type=ButtonEventType.BUTTON_PRESSED,
                timestamp_milliseconds=int(parts[1])
            )

        if parts[0] == "UP" and len(parts) >= 2:
            return ButtonEvent(
                event_type=ButtonEventType.BUTTON_RELEASED,
                timestamp_milliseconds=int(parts[1])
            )
    except (IndexError, ValueError):
        return None

    return None
