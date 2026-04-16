from dataclasses import dataclass

from tap_mapper.config import ScaleConfig
from tap_mapper.types import ScaleMode


SCALE_INTERVALS: dict[ScaleMode, tuple[int, ...]] = {
    ScaleMode.MINOR_PENTATONIC: (0, 3, 5, 7, 10),
    ScaleMode.MAJOR_PENTATONIC: (0, 2, 4, 7, 9),
    ScaleMode.MAJOR: (0, 2, 4, 5, 7, 9, 11),
    ScaleMode.MINOR: (0, 2, 3, 5, 7, 8, 10)
}


@dataclass(frozen=True)
class Scale:
    notes: tuple[int, ...]

    def closest_index(self, target_note: int) -> int:
        return min(
            range(len(self.notes)),
            key=lambda index: abs(self.notes[index] - target_note)
        )


def build_scale(config: ScaleConfig) -> Scale:
    notes: set[int] = set()
    intervals = SCALE_INTERVALS[config.mode]

    start_root = config.root_note - config.octave_search_below_root
    stop_root = config.root_note + config.octave_search_above_root

    for octave_root in range(start_root, stop_root + 1, config.octave_size):
        for interval in intervals:
            note = octave_root + interval
            if config.low_note <= note <= config.high_note:
                notes.add(note)

    ordered_notes = tuple(sorted(notes))
    if not ordered_notes:
        raise ValueError("The configured scale ranged failed to produce notes")

    return Scale(notes=ordered_notes)

