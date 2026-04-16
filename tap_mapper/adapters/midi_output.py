import time

import pygame.midi

from tap_mapper.config import MidiConfig


class MidiOutput:
    def __init__(self, config: MidiConfig) -> None:
        self._channel = config.channel
        self._max_note_length_s = config.max_note_length_ms / 1000.0
        self._note_count = config.note_count
        self._output: pygame.midi.Output | None = None
        self._current_note: int | None = None
        self._note_deadline_s: float | None = None

    def open(self, device_id: int) -> None:
        pygame.midi.init()
        self._output = pygame.midi.Output(device_id)

    def play_note(self, *, note: int, velocity: int) -> None:
        self.stop_note()

        output = self._require_output()
        output.note_on(note, velocity, self._channel)

        self._current_note = note
        self._note_deadline_s = time.monotonic() + self._max_note_length_s

    def stop_note(self) -> None:
        if self._current_note is None:
            return

        output = self._require_output()
        output.note_off(self._current_note, 0, self._channel)

        self._current_note = None
        self._note_deadline_s = None

    def tick(self) -> None:
        if self._current_note is None:
            return

        if self._note_deadline_s is None:
            return

        if time.monotonic() >= self._note_deadline_s:
            self.stop_note()

    def close(self) -> None:
        try:
            self.all_notes_off()
        finally:
            if self._output is not None:
                self._output.close()
                self._output = None

            pygame.midi.quit()

    def all_notes_off(self) -> None:
        if self._output is None:
            return

        for note in range(self._note_count):
            self._output.note_off(note, 0, self._channel)

        self._current_note = None
        self._note_deadline_s = None

    @staticmethod
    def list_output_devices() -> list[tuple[int, str]]:
        pygame.midi.init()

        try:
            devices: list[tuple[int, str]] = []

            for device_id in range(pygame.midi.get_count()):
                _, raw_name, is_input, is_output, _ = pygame.midi.get_device_info(device_id)
                if is_output and not is_input:
                    devices.append((device_id, raw_name.decode(errors="ignore")))

            return devices
        finally:
            pygame.midi.quit()

    @staticmethod
    def find_prefered_device_id(name_parts: tuple[str, ...]) -> int | None:
        normalized_name_parts = tuple(part.lower() for part in name_parts)

        for device_id, device_name in MidiOutput.list_output_devices():
            normalized_device_name = device_name.lower()
            if any(part in normalized_device_name for part in normalized_name_parts):
                return device_id

        return None

    def _require_output(self) -> pygame.midi.Output:
        if self._output is None:
            raise RuntimeError("MIDI output is not open")

        return self._output
