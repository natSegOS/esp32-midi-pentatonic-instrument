from dataclasses import dataclass

from tap_mapper.types import ScaleMode


SEMITONES_PER_OCTAVE = 12
OCTAVE_RANGE = 2

SCALE_INTERVALS_BY_MODE: dict[ScaleMode, tuple[int, ...]] = {
    ScaleMode.MINOR_PENTATONIC: (0, 3, 5, 7, 10),
    ScaleMode.MAJOR_PENTATONIC: (0, 2, 4, 7, 9),
    ScaleMode.MAJOR: (0, 2, 4, 5, 7, 9, 11),
    ScaleMode.MINOR: (0, 2, 3, 5, 7, 8, 10)
}


@dataclass(frozen=True)
class ScaleDefinition:
    midi_notes: tuple[int, ...]

    def find_index_of_closest_note(self, target_midi_note: int) -> int:
        return min(
            range(len(self.midi_notes)),
            key=lambda index: abs(self.midi_notes[index] - target_midi_note)
        )


def build_scale_definition(
    *,
    root_midi_note: int,
    scale_mode: ScaleMode,
    lowest_midi_note: int,
    highest_midi_note: int
) -> ScaleDefinition:
    midi_notes: set[int] = set()
    intervals = SCALE_INTERVALS_BY_MODE[scale_mode]

    for octave_root in range(
            root_midi_note - OCTAVE_RANGE * SEMITONES_PER_OCTAVE,
            root_midi_note + OCTAVE_RANGE * SEMITONES_PER_OCTAVE + 1,
            SEMITONES_PER_OCTAVE):
        for interval in intervals:
            midi_note = octave_root + interval
            if lowest_midi_note <= midi_note <= highest_midi_note:
                midi_notes.add(midi_note)

    ordered_midi_notes = tuple(sorted(midi_notes))
    if not ordered_midi_notes:
        raise ValueError("The configured scale ranged failed to produce notes")

    return ScaleDefinition(midi_notes=ordered_midi_notes)
