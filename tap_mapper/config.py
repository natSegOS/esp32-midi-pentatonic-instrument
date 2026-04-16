from dataclasses import dataclass, field

from tap_mapper.types import ScaleMode


@dataclass(frozen=True)
class SerialConfig:
    port: str = "/dev/cu.usbserial-10"
    baud_rate: int = 115200
    timeout_s: float = 0.01
    read_size_bytes: int = 256


@dataclass(frozen=True)
class TempoConfig:
    default_bpm: float = 98.0
    min_bpm: float = 50.0
    max_bpm: float = 220.0
    smoothing_alpha: float = 0.60


@dataclass(frozen=True)
class ScaleConfig:
    root_note: int = 69 # A4
    mode: ScaleMode = ScaleMode.MINOR_PENTATONIC
    low_note: int = 64 # E4
    high_note: int = 84 # C6
    start_note: int = 69
    octave_size: int = 12
    octave_search_below_root: int = 24
    octave_search_above_root: int = 24
    max_melodic_jump_semitones: int = 5


@dataclass(frozen=True)
class MidiConfig:
    channel: int = 0
    velocity: int = 112
    max_note_length_ms: int = 6000
    note_count: int = 128
    preferred_output_name_parts: tuple[str, ...] = ("IAC", "CoreMIDI", "Bus")


@dataclass(frozen=True)
class RuntimeConfig:
    idle_sleep_s: float = 0.001


@dataclass(frozen=True)
class AppConfig:
    serial: SerialConfig = field(default_factory=SerialConfig)
    tempo: TempoConfig = field(default_factory=TempoConfig)
    scale: ScaleConfig = field(default_factory=ScaleConfig)
    midi: MidiConfig = field(default_factory=MidiConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)

