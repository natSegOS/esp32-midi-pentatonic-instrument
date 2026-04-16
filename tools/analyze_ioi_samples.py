import argparse
import csv
import json
import math
import random
import statistics
from pathlib import Path

from tap_mapper.config import AppConfig
from tap_mapper.domain.scale import build_scale
from tap_mapper.domain.tap_sequence import TapSequence, choose_step


ROLLING_WINDOW_RADIUS = 2
MIN_INTERVAL_MS = 1.0
DEFAULT_MONTE_CARLO_RUNS = 500
THRESHOLD_RATIOS = (0.33, 0.75, 1.5)
BOUNDARY_OFFSETS_MS = tuple(range(-40, 41, 5))

MILLISECONDS_PER_MINUTE = 60_000.0


def load_iois_ms(csv_path: Path) -> list[float]:
    iois_ms: list[float] = []

    with csv_path.open() as file:
        reader = csv.DictReader(file)
        for row in reader:
            raw_value = row["ioi_ms"].strip()
            if raw_value:
                iois_ms.append(float(raw_value))

    if len(iois_ms) < 2:
        raise ValueError("Need at least 2 IOI samples for analysis.")

    return iois_ms


def median_absolute_deviation(values: list[float]) -> float:
    center = statistics.median(values)
    absolute_deviations = [abs(value - center) for value in values]
    return statistics.median(absolute_deviations)


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower_index = math.floor(position)
    upper_index = math.ceil(position)

    if lower_index == upper_index:
        return ordered[lower_index]

    lower_value = ordered[lower_index]
    upper_value = ordered[upper_index]
    weight = position - lower_index
    return lower_value * (1.0 - weight) + upper_value * weight


def mean_abs_successive_diff(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0

    diffs = [abs(values[index] - values[index - 1]) for index in range(1, len(values))]
    return statistics.mean(diffs)


def rolling_median(values: list[float], index: int, radius: int) -> float:
    start = max(0, index - radius)
    stop = min(len(values), index + radius + 1)
    window = values[start:stop]
    return statistics.median(window)


def compute_empirical_jitter_residuals(iois_ms: list[float]) -> list[float]:
    residuals: list[float] = []

    for index, value in enumerate(iois_ms):
        local_center = rolling_median(iois_ms, index, ROLLING_WINDOW_RADIUS)
        residuals.append(value - local_center)

    return residuals


def build_baseline_note_sequence(iois_ms: list[float], config: AppConfig) -> list[int]:
    scale = build_scale(config.scale)
    sequence = TapSequence(
        scale=scale,
        tempo_config=config.tempo,
        scale_config=config.scale
    )

    notes: list[int] = []
    timestamp_ms = 0.0

    for interval_ms in iois_ms:
        timestamp_ms += interval_ms
        note = sequence.handle_press(int(round(timestamp_ms)))
        notes.append(note)

    return notes


def perturb_ioi_sequence(iois_ms: list[float], residuals: list[float], rng: random.Random) -> list[float]:
    perturbed: list[float] = []

    for interval_ms in iois_ms:
        sampled_residual = rng.choice(residuals)
        perturbed_interval = max(MIN_INTERVAL_MS, interval_ms + sampled_residual)
        perturbed.append(perturbed_interval)

    return perturbed


def compute_sequence_note_divergence(
    iois_ms: list[float],
    residuals: list[float],
    config: AppConfig,
    monte_carlo_runs: int,
    seed: int,
) -> dict:
    rng = random.Random(seed)
    baseline_notes = build_baseline_note_sequence(iois_ms, config)

    divergence_rates: list[float] = []

    for _ in range(monte_carlo_runs):
        perturbed_iois_ms = perturb_ioi_sequence(iois_ms, residuals, rng)
        perturbed_notes = build_baseline_note_sequence(perturbed_iois_ms, config)

        mismatch_count = sum(
            1 for baseline_note, perturbed_note in zip(baseline_notes, perturbed_notes)
            if baseline_note != perturbed_note
        )
        divergence_rates.append(mismatch_count / len(baseline_notes))

    return {
        "baseline_note_count": len(baseline_notes),
        "mean_note_divergence_rate_per_run": statistics.mean(divergence_rates),
        "median_note_divergence_rate_per_run": statistics.median(divergence_rates),
        "p95_note_divergence_rate_per_run": percentile(divergence_rates, 0.95),
        "max_note_divergence_rate_per_run": max(divergence_rates),
    }


def compute_boundary_flip_rates(
    *,
    residuals: list[float],
    bpm: float
) -> dict:
    beat_ms = MILLISECONDS_PER_MINUTE / bpm
    results: dict[str, dict[str, float]] = {}

    for threshold_ratio in THRESHOLD_RATIOS:
        threshold_ms = threshold_ratio * beat_ms
        threshold_key = f"ratio_{threshold_ratio:.2f}"

        offset_rates: dict[str, float] = {}
        for offset_ms in BOUNDARY_OFFSETS_MS:
            nominal_interval_ms = max(MIN_INTERVAL_MS, threshold_ms + offset_ms)
            baseline_step = choose_step(
                interval_ms=int(round(nominal_interval_ms)),
                bpm=bpm
            )

            flips = 0
            for residual in residuals:
                perturbed_interval_ms = max(MIN_INTERVAL_MS, nominal_interval_ms + residual)
                perturbed_step = choose_step(
                    interval_ms=int(round(perturbed_interval_ms)),
                    bpm=bpm
                )
                if perturbed_step != baseline_step:
                    flips += 1

            flip_rate = flips / len(residuals)
            offset_rates[str(offset_ms)] = flip_rate

        results[threshold_key] = offset_rates

    return results


def summarize_boundary_vs_interior(boundary_flip_rates: dict) -> dict:
    boundary_values: list[float] = []
    interior_values: list[float] = []

    for offset_rates in boundary_flip_rates.values():
        for offset_text, flip_rate in offset_rates.items():
            offset = int(offset_text)
            if abs(offset) <= 5:
                boundary_values.append(flip_rate)
            if abs(offset) >= 25:
                interior_values.append(flip_rate)

    boundary_mean = statistics.mean(boundary_values) if boundary_values else 0.0
    interior_mean = statistics.mean(interior_values) if interior_values else 0.0
    ratio = boundary_mean / interior_mean if interior_mean > 0 else float("inf")

    return {
        "boundary_mean_flip_rate": boundary_mean,
        "interior_mean_flip_rate": interior_mean,
        "boundary_instability_ratio": ratio,
    }


def build_input_noise_summary(iois_ms: list[float]) -> dict:
    mean_ioi = statistics.mean(iois_ms)
    std_ioi = statistics.stdev(iois_ms) if len(iois_ms) > 1 else 0.0
    median_ioi = statistics.median(iois_ms)
    mad_ioi = median_absolute_deviation(iois_ms)

    return {
        "sample_count": len(iois_ms),
        "mean_ioi_ms": mean_ioi,
        "median_ioi_ms": median_ioi,
        "std_ioi_ms": std_ioi,
        "mad_ioi_ms": mad_ioi,
        "cv_ioi": std_ioi / mean_ioi if mean_ioi > 0 else 0.0,
        "mean_abs_successive_diff_ms": mean_abs_successive_diff(iois_ms),
        "p05_ioi_ms": percentile(iois_ms, 0.05),
        "p95_ioi_ms": percentile(iois_ms, 0.95),
        "min_ioi_ms": min(iois_ms),
        "max_ioi_ms": max(iois_ms),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze real IOI data and output instability.")
    parser.add_argument("csv_path", type=Path, help="Path to collected IOI CSV.")
    parser.add_argument("--out", type=Path, required=True, help="Output JSON report path.")
    parser.add_argument("--runs", type=int, default=DEFAULT_MONTE_CARLO_RUNS, help="Monte Carlo runs.")
    parser.add_argument("--seed", type=int, default=7, help="Random seed.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = AppConfig()

    iois_ms = load_iois_ms(args.csv_path)
    residuals = compute_empirical_jitter_residuals(iois_ms)
    input_summary = build_input_noise_summary(iois_ms)

    representative_bpm = MILLISECONDS_PER_MINUTE / input_summary["median_ioi_ms"]

    boundary_flip_rates = compute_boundary_flip_rates(
        residuals=residuals,
        bpm=representative_bpm
    )

    boundary_summary = summarize_boundary_vs_interior(boundary_flip_rates)

    sequence_divergence = compute_sequence_note_divergence(
        iois_ms=iois_ms,
        residuals=residuals,
        config=config,
        monte_carlo_runs=args.runs,
        seed=args.seed,
    )

    report = {
        "source_csv": str(args.csv_path),
        "input_noise_summary": input_summary,
        "empirical_jitter_summary": {
            "mean_residual_ms": statistics.mean(residuals),
            "std_residual_ms": statistics.stdev(residuals) if len(residuals) > 1 else 0.0,
            "mad_residual_ms": median_absolute_deviation(residuals),
            "p05_residual_ms": percentile(residuals, 0.05),
            "p95_residual_ms": percentile(residuals, 0.95),
        },
        "analysis_parameters": {
            "representative_bpm": representative_bpm,
            "monte_carlo_runs": args.runs,
            "seed": args.seed,
            "threshold_ratios": list(THRESHOLD_RATIOS),
            "boundary_offsets_ms": list(BOUNDARY_OFFSETS_MS),
        },
        "boundary_flip_rates": boundary_flip_rates,
        "boundary_summary": boundary_summary,
        "sequence_divergence": sequence_divergence,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
