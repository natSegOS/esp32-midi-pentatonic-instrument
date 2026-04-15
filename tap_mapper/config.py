from dataclasses import dataclass, field

from tap_mapper.types import ScaleMode


@dataclass(frozen=True)
class SerialConnectionConfig:
    port_name: str = "/dev/cu.usbserial-10"
    baud_rate: int = 115200
    timeout_seconds: float = 0.01


@dataclass(frozen=True)
class TempoTrackingConfig:
    default_beats_per_minute: float = 98.0
    minimum_beats_per_minute: float = 50.0
    maximum_beats_per_minute: float = 220.0
    exponential_smoothing_alpha: float = 0.60


@dataclass(frozen=True)
class ScaleRangeConfig:
    root_midi_note: int = 69 # A4
    scale_mode: ScaleMode = ScaleMode.MINOR_PENTATONIC
    lowest_midi_note: int = 64 # E4
    highest_midi_note: int = 84 # C6
    starting_midi_note: int = 69


@dataclass(frozen=True)
class MidiPlaybackConfig:
    channel_number: int = 0
    note_velocity: int = 112
    maximum_note_length_milliseconds: int = 6000
    preferred_output_name_fragments: tuple[str, ...] = ("IAC", "CoreMIDI", "Bus")


@dataclass(frozen=True)
class RuntimeLoopConfig:
    idle_sleep_seconds: float = 0.001


@dataclass(frozen=True)
class ApplicationConfig:
    serial_connection: SerialConnectionConfig = field(default_factory=SerialConnectionConfig)
    tempo_tracking: TempoTrackingConfig = field(default_factory=TempoTrackingConfig)
    scale_range: ScaleRangeConfig = field(default_factory=ScaleRangeConfig)
    midi_playback: MidiPlaybackConfig = field(default_factory=MidiPlaybackConfig)
    runtime_loop: RuntimeLoopConfig = field(default_factory=RuntimeLoopConfig)

