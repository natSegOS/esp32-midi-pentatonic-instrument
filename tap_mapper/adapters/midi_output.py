import time

import pygame.midi


class MidiOutputDevice:
    def __init__(
        self,
        *,
        midi_channel_number: int,
        maximum_note_length_milliseconds: int
    ) -> None:
        self._midi_channel_number = midi_channel_number
        self._maximum_note_length_seconds = maximum_note_length_milliseconds / 1000.0
        self._pygame_output: pygame.midi.Output | None = None
        self._currently_playing_midi_note: int | None = None
        self._automatic_note_off_deadline_seconds: float | None = None

    def open(self, *, output_device_id: int) -> None:
        pygame.midi.init()
        self._pygame_output = pygame.midi.Output(output_device_id)

    def play_note(self, *, midi_note: int, velocity: int) -> None:
        self.stop_current_note()

        output = self._require_open_output()
        output.note_on(midi_note, velocity, self._midi_channel_number)

        self._currently_playing_midi_note = midi_note
        self._automatic_note_off_deadline_seconds = time.monotonic() + self._maximum_note_length_seconds

    def stop_current_note(self) -> None:
        if self._currently_playing_midi_note is None:
            return

        output = self._require_open_output()
        output.note_off(self._currently_playing_midi_note, 0, self._midi_channel_number)

        self._currently_playing_midi_note = None
        self._automatic_note_off_deadline_seconds = None

    def tick(self) -> None:
        if self._currently_playing_midi_note is None:
            return

        if self._automatic_note_off_deadline_seconds is None:
            return

        if time.monotonic() >= self._automatic_note_off_deadline_seconds:
            self.stop_current_note()

    def close(self) -> None:
        try:
            self.send_all_notes_off()
        finally:
            if self._pygame_output is not None:
                self._pygame_output.close()
                self._pygame_output = None

            pygame.midi.quit()

    def send_all_notes_off(self) -> None:
        if self._pygame_output is None:
            return

        for midi_note in range(128):
            self._pygame_output.note_off(midi_note, 0, self._midi_channel_number)

        self._currently_playing_midi_note = None
        self._automatic_note_off_deadline_seconds = None

    @staticmethod
    def list_available_output_devices() -> list[tuple[int, str]]:
        pygame.midi.init()
        try:
            output_devices: list[tuple[int, str]] = []

            for device_id in range(pygame.midi.get_count()):
                _, raw_name, is_input, is_output, _ = pygame.midi.get_device_info(device_id)
                if is_output and not is_input:
                    output_devices.append((device_id, raw_name.decode(errors="ignore")))

            return output_devices
        finally:
            pygame.midi.quit()

    @staticmethod
    def find_prefered_output_device_id(
        *,
        preferred_name_fragments: tuple[str, ...]
    ) -> int | None:
        normalized_fragments = tuple(fragment.lower() for fragment in preferred_name_fragments)

        for device_id, device_name in MidiOutputDevice.list_available_output_devices():
            normalized_device_name = device_name.lower()
            if any(fragment in normalized_device_name for fragment in normalized_fragments):
                return device_id

        return None

    def _require_open_output(self) -> pygame.midi.Output:
        if self._pygame_output is None:
            raise RuntimeError("The MIDI output device is not open")
        
        return self._pygame_output
