from dataclasses import dataclass

from tap_mapper.config import TempoTrackingConfig
from tap_mapper.domain.scale_definition import ScaleDefinition


MILLISECONDS_PER_MINUTE: float = 60_000.0
MAX_INTERVAL_SEMITONES = 5

FAST_TAP_THRESHOLD = 0.33
MEDIUM_TAP_THRESHOLD = 0.75
SLOW_TAP_THRESHOLD = 1.5

DETERMINISTIC_MODULUS = 997


@dataclass
class TapSequenceState:
    current_scale_index: int
    estimated_beats_per_minute: float
    previous_press_timestamp_milliseconds: int | None = None


@dataclass(frozen=True)
class NoteSelectionDecision:
    midi_note_to_play: int


class TapDrivenNoteSelector:
    """Converts button press timing into constrained melodic movement"""

    def __init__(
        self,
        *,
        scale_definition: ScaleDefinition,
        tempo_tracking_config: TempoTrackingConfig,
        starting_midi_note: int
    ) -> None:
        self._scale_definition = scale_definition
        self._tempo_tracking_config = tempo_tracking_config
        self._state = TapSequenceState(
            current_scale_index=scale_definition.find_index_of_closest_note(starting_midi_note),
            estimated_beats_per_minute=tempo_tracking_config.default_beats_per_minute
        )

    def handle_button_press(self, timestamp_milliseconds: int) -> NoteSelectionDecision:
        if self._state.previous_press_timestamp_milliseconds is not None:
            interval_milliseconds = max(
                1,
                timestamp_milliseconds - self._state.previous_press_timestamp_milliseconds
            )

            self._state.estimated_beats_per_minute = update_estimated_beats_per_minute(
                current_beats_per_minute=self._state.estimated_beats_per_minute,
                interval_milliseconds=interval_milliseconds,
                tempo_tracking_config=self._tempo_tracking_config
            )

            self._state.current_scale_index = choose_next_scale_index(
                current_scale_index=self._state.current_scale_index,
                interval_milliseconds=interval_milliseconds,
                estimated_beats_per_minute=self._state.estimated_beats_per_minute,
                available_midi_notes=self._scale_definition.midi_notes
            )

        self._state.previous_press_timestamp_milliseconds = timestamp_milliseconds

        return NoteSelectionDecision(
            midi_note_to_play=self._scale_definition.midi_notes[self._state.current_scale_index]
        )

    @property
    def estimated_beats_per_minute(self) -> float:
        return self._state.estimated_beats_per_minute


def update_estimated_beats_per_minute(
    *,
    current_beats_per_minute: float,
    interval_milliseconds: int,
    tempo_tracking_config: TempoTrackingConfig
) -> float:
    measured_beats_per_minute = MILLISECONDS_PER_MINUTE / interval_milliseconds
    clamped_beats_per_minute = clamp_float(
        measured_beats_per_minute,
        tempo_tracking_config.minimum_beats_per_minute,
        tempo_tracking_config.maximum_beats_per_minute
    )

    alpha = tempo_tracking_config.exponential_smoothing_alpha
    return alpha * clamped_beats_per_minute + (1.0 - alpha) * current_beats_per_minute


def choose_next_scale_index(
    *,
    current_scale_index: int,
    interval_milliseconds: int,
    estimated_beats_per_minute: float,
    available_midi_notes: tuple[int, ...]
) -> int:
    scale_step_offset = choose_scale_step_offset(
        interval_milliseconds=interval_milliseconds,
        estimated_beats_per_minute=estimated_beats_per_minute
    )

    collection_length = len(available_midi_notes)

    candidate_scale_index = reflect_index_into_valid_range(
        index=current_scale_index + scale_step_offset,
        collection_length=collection_length
    )

    current_midi_note = available_midi_notes[current_scale_index]
    candidate_midi_note = available_midi_notes[candidate_scale_index]

    if abs(candidate_midi_note - current_midi_note) > MAX_INTERVAL_SEMITONES:
        direction = 1 if candidate_scale_index > current_scale_index else -1
        candidate_scale_index = reflect_index_into_valid_range(
            index=current_scale_index + direction,
            collection_length=collection_length
        )

    return candidate_scale_index


def choose_scale_step_offset(
    *,
    interval_milliseconds: int,
    estimated_beats_per_minute: float
) -> int:
    beat_length_milliseconds = MILLISECONDS_PER_MINUTE / estimated_beats_per_minute
    relative_interval = interval_milliseconds / beat_length_milliseconds

    if relative_interval <= FAST_TAP_THRESHOLD:
        return choose_deterministic_weighted_value(
            seed_value=interval_milliseconds,
            choices=(0, 1),
            weights=(0.4, 0.6)
        )

    if relative_interval <= MEDIUM_TAP_THRESHOLD:
        return choose_deterministic_weighted_value(
            seed_value=interval_milliseconds,
            choices=(-1, 1),
            weights=(0.5, 0.5)
        )

    if relative_interval <= SLOW_TAP_THRESHOLD:
        return choose_deterministic_weighted_value(
            seed_value=interval_milliseconds,
            choices=(-2, -1, 1, 2),
            weights=(0.2, 0.3, 0.3, 0.2)
        )

    return choose_deterministic_weighted_value(
        seed_value=interval_milliseconds,
        choices=(-2, 0, 2),
        weights=(0.3, 0.4, 0.3)
    )


def choose_deterministic_weighted_value(
    *,
    seed_value: int,
    choices: tuple[int, ...],
    weights: tuple[float, ...]
) -> int:
    """
    Uses the tap interval as a deterministic seed so the result feels varied
    without requiring randomness in unit tests
    """
    normalized_roll = (seed_value % DETERMINISTIC_MODULUS) / float(DETERMINISTIC_MODULUS)
    total_weight = sum(weights)
    cumulative_weight = 0.0

    for choice, weight in zip(choices, weights):
        cumulative_weight += weight / total_weight
        if normalized_roll <= cumulative_weight:
            return choice

    return choices[-1]


def reflect_index_into_valid_range(*, index: int, collection_length: int) -> int:
    """Reflects an out-of-range index back into the valid note range"""
    if collection_length <= 0:
        raise ValueError("collection_length must be positive")

    last_valid_index = collection_length - 1

    new_index = index

    while new_index < 0 or new_index > last_valid_index:
        if new_index < 0:
            new_index = -new_index
        elif new_index > last_valid_index:
            new_index = last_valid_index - (new_index - last_valid_index)

    return new_index


def clamp_float(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))
