import time

from tap_mapper.adapters.midi_output_device import MidiOutputDevice
from tap_mapper.adapters.serial_button_event_source import SerialButtonEventSource
from tap_mapper.config import ApplicationConfig
from tap_mapper.domain.scale_definition import build_scale_definition
from tap_mapper.domain.tap_note_selector import TapDrivenNoteSelector
from tap_mapper.types import ButtonEventType


class TapMapperApplicationRuntime:
    def __init__(self, application_config: ApplicationConfig) -> None:
        self._application_config = application_config

        self._scale_definition = build_scale_definition(
            root_midi_note=application_config.scale_range.root_midi_note,
            scale_mode=application_config.scale_range.scale_mode,
            lowest_midi_note=application_config.scale_range.lowest_midi_note,
            highest_midi_note=application_config.scale_range.highest_midi_note
        )

        self._tap_note_selector = TapDrivenNoteSelector(
            scale_definition=self._scale_definition,
            tempo_tracking_config=application_config.tempo_tracking,
            starting_midi_note=application_config.scale_range.starting_midi_note
        )

        self._midi_output_device = MidiOutputDevice(
            midi_channel_number=application_config.midi_playback.channel_number,
            maximum_note_length_milliseconds=application_config.midi_playback.maximum_note_length_milliseconds
        )

        self._serial_button_event_source: SerialButtonEventSource | None = None

    def run(self) -> int:
        try:
            output_device_id = self._require_midi_output_device_id()
            self._midi_output_device.open(output_device_id=output_device_id)

            self._serial_button_event_source = SerialButtonEventSource(
                serial_port_name=self._application_config.serial_connection.port_name,
                baud_rate=self._application_config.serial_connection.baud_rate,
                timeout_seconds=self._application_config.serial_connection.timeout_seconds
            )

            self._print_startup_summary(output_device_id)
            return self._run_forever()

        except Exception as exception:
            print(f"Startup failed: {exception}")
            return 1

        finally:
            self.close()

    def close(self) -> None:
        if self._serial_button_event_source is not None:
            try:
                self._serial_button_event_source.close()
            except Exception:
                pass

            self._serial_button_event_source = None

        self._midi_output_device.close()

    def _run_forever(self) -> int:
        try:
            while True:
                if self._serial_button_event_source is not None:
                    for button_event in self._serial_button_event_source.read_available_events():
                        if button_event.event_type is ButtonEventType.BUTTON_PRESSED:
                            decision = self._tap_note_selector.handle_button_press(button_event.timestamp_milliseconds)
                            self._midi_output_device.play_note(
                                midi_note=decision.midi_note_to_play,
                                velocity=self._application_config.midi_playback.note_velocity
                            )
                        elif button_event.event_type is ButtonEventType.BUTTON_RELEASED:
                            self._midi_output_device.stop_current_note()

                self._midi_output_device.tick()
                time.sleep(self._application_config.runtime_loop.idle_sleep_seconds)

        except KeyboardInterrupt:
            print("\nStopping")
            return 0

    def _require_midi_output_device_id(self) -> int:
        output_device_id = self._midi_output_device.find_prefered_output_device_id(
            preferred_name_fragments=self._application_config.midi_playback.preferred_output_name_fragments
        )

        if output_device_id is not None:
            return output_device_id

        available_devices = self._midi_output_device.list_available_output_devices()
        if not available_devices:
            raise RuntimeError("No MIDI output devices were found")

        available_devices_summary = ", ".join(
            f"{device_id}:{device_name}" for device_id, device_name in available_devices
        )

        raise RuntimeError(
            "No preferred MIDI output device matched the configured names. "
            f"Available output devices: {available_devices_summary}"
        )

    def _print_startup_summary(self, output_device_id: int) -> None:
        print("Tap mapper ready")
        print(f"Selected MIDI output device: {output_device_id}")
        print(
            f"Scale mode: {self._application_config.scale_range.scale_mode.value} | "
            f"Root note: {self._application_config.scale_range.root_midi_note} | "
            f"Range: {self._scale_definition.midi_notes[0]}-{self._scale_definition.midi_notes[-1]}"
        )


def main() -> int:
    return TapMapperApplicationRuntime(ApplicationConfig()).run()
