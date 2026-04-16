import time

from tap_mapper.adapters.midi_output import MidiOutput
from tap_mapper.adapters.serial_input import SerialInput
from tap_mapper.config import AppConfig
from tap_mapper.domain.scale import build_scale
from tap_mapper.domain.tap_sequence import TapSequence
from tap_mapper.types import ButtonEventType


class TapMapperRuntime:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._scale = build_scale(config.scale)

        self._tap_sequence = TapSequence(
            scale=self._scale,
            tempo_config=config.tempo,
            scale_config=config.scale
        )

        self._midi_output = MidiOutput(config.midi)
        self._serial_input: SerialInput | None = None

    def run(self) -> int:
        try:
            midi_device_id = self._require_midi_device_id()
            self._midi_output.open(midi_device_id)

            self._serial_input = SerialInput(self._config.serial)

            self._print_startup_summary(midi_device_id)
            return self._run_loop()

        except Exception as exception:
            print(f"Startup failed: {exception}")
            return 1

        finally:
            self.close()

    def close(self) -> None:
        if self._serial_input is not None:
            try:
                self._serial_input.close()
            except Exception:
                pass

            self._serial_input = None

        self._midi_output.close()

    def _run_loop(self) -> int:
        try:
            while True:
                if self._serial_input is not None:
                    for event in self._serial_input.read_events():
                        if event.event_type is ButtonEventType.PRESS:
                            note = self._tap_sequence.handle_press(event.timestamp_ms)
                            self._midi_output.play_note(note=note, velocity=self._config.midi.velocity)
                        elif event.event_type is ButtonEventType.RELEASE:
                            self._midi_output.stop_note()

                self._midi_output.tick()
                time.sleep(self._config.runtime.idle_sleep_s)

        except KeyboardInterrupt:
            print("\nStopping")
            return 0

    def _require_midi_device_id(self) -> int:
        device_id = self._midi_output.find_preferred_device_id(self._config.midi.preferred_output_name_parts)

        if device_id is not None:
            return device_id

        devices = self._midi_output.list_output_devices()
        if not devices:
            raise RuntimeError("No MIDI output devices were found")

        device_summary = ", ".join(f"{device_id}:{device_name}" for device_id, device_name in devices)

        raise RuntimeError(
            "No preferred MIDI output device matched the configured names. "
            f"Available output devices: {device_summary}"
        )

    def _print_startup_summary(self, midi_device_id: int) -> None:
        print("Tap mapper ready")
        print(f"MIDI device: {midi_device_id}")
        print(
            f"Scale: {self._config.scale.mode.value} | "
            f"Root: {self._config.scale.root_note} | "
            f"Range: {self._scale.notes[0]}-{self._scale.notes[-1]}"
        )


def main() -> int:
    return TapMapperRuntime(AppConfig()).run()
