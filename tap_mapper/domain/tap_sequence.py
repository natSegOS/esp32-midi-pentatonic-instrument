from dataclasses import dataclass

from tap_mapper.config import ScaleConfig, TempoConfig
from tap_mapper.domain.scale import Scale


MILLISECONDS_PER_MINUTE: float = 60_000.0

FAST_TAP_THRESHOLD = 0.33
MEDIUM_TAP_THRESHOLD = 0.75
SLOW_TAP_THRESHOLD = 1.5

DETERMINISTIC_MODULUS = 997


@dataclass
class TapState:
    current_index: int
    bpm: float
    last_press_ms: int | None = None


class TapSequence:
    """Selects next note from a scale based on press timing"""

    def __init__(
        self,
        *,
        scale: Scale,
        tempo_config: TempoConfig,
        scale_config: ScaleConfig
    ) -> None:
        self._scale = scale
        self._tempo_config = tempo_config
        self._scale_config = scale_config
        self._state = TapState(
            current_index=scale.closest_index(scale_config.start_note),
            bpm=tempo_config.default_bpm
        )

    def handle_press(self, timestamp_ms: int) -> int:
        if self._state.last_press_ms is not None:
            interval_ms = max(1, timestamp_ms - self._state.last_press_ms)

            self._state.bpm = update_bpm(
                current_bpm=self._state.bpm,
                interval_ms=interval_ms,
                tempo_config=self._tempo_config
            )

            self._state.current_index = choose_next_index(
                current_index=self._state.current_index,
                interval_ms=interval_ms,
                bpm=self._state.bpm,
                notes=self._scale.notes,
                max_jump_semitones=self._scale_config.max_melodic_jump_semitones
            )

        self._state.last_press_ms = timestamp_ms

        return self._scale.notes[self._state.current_index]


def update_bpm(
    *,
    current_bpm: float,
    interval_ms: int,
    tempo_config: TempoConfig
) -> float:
    measured_bpm = MILLISECONDS_PER_MINUTE / interval_ms
    clamped_bpm = clamp(measured_bpm, tempo_config.min_bpm, tempo_config.max_bpm)
    alpha = tempo_config.smoothing_alpha

    return alpha * clamped_bpm + (1.0 - alpha) * current_bpm


def choose_next_index(
    *,
    current_index: int,
    interval_ms: int,
    bpm: float,
    notes: tuple[int, ...],
    max_jump_semitones: int
) -> int:
    step = choose_step(interval_ms=interval_ms, bpm=bpm)
    candidate_index = reflect_index(index=current_index + step, length=len(notes))

    current_note = notes[current_index]
    candidate_note = notes[candidate_index]

    if abs(candidate_note - current_note) > max_jump_semitones:
        direction = 1 if candidate_index > current_index else -1
        candidate_index = reflect_index(index=current_index + direction, length=len(notes))

    return candidate_index


def choose_step(*, interval_ms: int, bpm: float) -> int:
    beat_ms = MILLISECONDS_PER_MINUTE / bpm
    relative_interval = interval_ms / beat_ms

    if relative_interval <= FAST_TAP_THRESHOLD:
        return weighted_choice(
            seed_value=interval_ms,
            choices=(0, 1),
            weights=(0.4, 0.6)
        )

    if relative_interval <= MEDIUM_TAP_THRESHOLD:
        return weighted_choice(
            seed_value=interval_ms,
            choices=(-1, 1),
            weights=(0.5, 0.5)
        )

    if relative_interval <= SLOW_TAP_THRESHOLD:
        return weighted_choice(
            seed_value=interval_ms,
            choices=(-2, -1, 1, 2),
            weights=(0.2, 0.3, 0.3, 0.2)
        )

    return weighted_choice(
        seed_value=interval_ms,
        choices=(-2, 0, 2),
        weights=(0.3, 0.4, 0.3)
    )


def weighted_choice(
    *,
    seed_value: int,
    choices: tuple[int, ...],
    weights: tuple[float, ...]
) -> int:
    """
    Deterministic weighted choice keeps behavior reproducible for tests
    while still producing varied melodic movement
    """
    roll = (seed_value % DETERMINISTIC_MODULUS) / float(DETERMINISTIC_MODULUS)
    total_weight = sum(weights)
    cumulative_weight = 0.0

    for choice, weight in zip(choices, weights):
        cumulative_weight += weight / total_weight
        if roll <= cumulative_weight:
            return choice

    return choices[-1]


def reflect_index(*, index: int, length: int) -> int:
    if length <= 0:
        raise ValueError("collection_length must be positive")

    last_valid_index = length - 1

    new_index = index

    while new_index < 0 or new_index > last_valid_index:
        if new_index < 0:
            new_index = -new_index
        elif new_index > last_valid_index:
            new_index = last_valid_index - (new_index - last_valid_index)

    return new_index


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))
