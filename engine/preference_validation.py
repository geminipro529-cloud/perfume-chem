"""Scoped validation utilities for Davidson preference evidence."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from math import isfinite, log
from random import Random
from statistics import mean
from typing import Callable, ClassVar

from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.preference import PairwisePreference, PreferenceOutcome
from engine.preference_davidson import (
    DavidsonFitConfig,
    DavidsonFitReceipt,
    davidson_pair_probabilities,
    fit_davidson,
)

_FALSE_AUTHORITY = {
    "formula": False,
    "liking": False,
    "physical_execution": False,
    "release": False,
    "runtime": False,
    "scientific_claim": False,
    "sensory": False,
}
_LIKELIHOOD_OUTCOMES = {
    PreferenceOutcome.LEFT,
    PreferenceOutcome.RIGHT,
    PreferenceOutcome.NO_PREFERENCE,
}


def _finite_nonnegative(value: float, name: str) -> float:
    if not isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return value


def _percentile(values: list[float], probability: float) -> float:
    if not values:
        raise ValueError("percentile requires values")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _row_key(row: PairwisePreference) -> tuple[object, ...]:
    return (
        row.assessor_id or "",
        row.session_id or "",
        row.comparison_id or "",
        row.left_item,
        row.right_item,
        row.outcome.value,
        row.time_seconds if row.time_seconds is not None else -1.0,
        row.first_presented_item or "",
        row.previous_presented_item or "",
    )


def _items(rows: tuple[PairwisePreference, ...]) -> tuple[str, ...]:
    return tuple(
        sorted({row.left_item for row in rows} | {row.right_item for row in rows})
    )


@dataclass(frozen=True, slots=True)
class ClusterBootstrapConfig:
    replicates: int
    seed: int
    regularization: float = 0.1
    maximum_iterations: int = 200
    confidence_level: float = 0.95
    maximum_failed_fraction: float = 0.2
    nested_session_resampling: bool = False
    cluster_unit: str = "ASSESSOR"

    def __post_init__(self) -> None:
        if isinstance(self.replicates, bool) or self.replicates < 1:
            raise ValueError("replicates must be a positive integer")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ValueError("seed must be an integer")
        _finite_nonnegative(self.regularization, "regularization")
        if isinstance(self.maximum_iterations, bool) or self.maximum_iterations < 1:
            raise ValueError("maximum_iterations must be a positive integer")
        if not 0 < self.confidence_level < 1:
            raise ValueError("confidence_level must be between zero and one")
        if not 0 <= self.maximum_failed_fraction <= 1:
            raise ValueError("maximum_failed_fraction must be from zero to one")
        if not isinstance(self.nested_session_resampling, bool):
            raise TypeError("nested_session_resampling must be boolean")
        cluster_unit = self.cluster_unit.strip().upper()
        if cluster_unit not in {"ASSESSOR", "SESSION"}:
            raise ValueError("cluster_unit must be ASSESSOR or SESSION")
        if cluster_unit == "SESSION" and self.nested_session_resampling:
            raise ValueError(
                "nested_session_resampling cannot be used with SESSION clusters"
            )
        object.__setattr__(self, "cluster_unit", cluster_unit)


@dataclass(frozen=True, slots=True)
class ClusterBootstrapReceipt:
    SCHEMA_VERSION: ClassVar[str] = "cluster_bootstrap_receipt_v1"
    utility_intervals: dict[str, tuple[float, float]]
    completed_replicates: int
    failed_replicates: int
    boundary_replicates: int
    effective_unique_assessors: int
    graph_supported_replicates: int
    interval_method: str
    seed: int
    stable: bool
    leave_one_assessor_max_shift: float | None
    subgroup_reversal: bool
    cluster_unit: str = "ASSESSOR"
    effective_unique_clusters: int | None = None
    leave_one_cluster_max_shift: float | None = None

    @property
    def authority(self) -> dict[str, bool]:
        return dict(_FALSE_AUTHORITY)

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.SCHEMA_VERSION,
            "utility_intervals": {
                item: list(interval) for item, interval in self.utility_intervals.items()
            },
            "completed_replicates": self.completed_replicates,
            "failed_replicates": self.failed_replicates,
            "boundary_replicates": self.boundary_replicates,
            "effective_unique_assessors": self.effective_unique_assessors,
            "graph_supported_replicates": self.graph_supported_replicates,
            "interval_method": self.interval_method,
            "seed": self.seed,
            "stable": self.stable,
            "leave_one_assessor_max_shift": self.leave_one_assessor_max_shift,
            "subgroup_reversal": self.subgroup_reversal,
            "authority": self.authority,
        }
        if self.cluster_unit != "ASSESSOR":
            payload.update(
                {
                    "cluster_unit": self.cluster_unit,
                    "effective_unique_clusters": self.effective_unique_clusters,
                    "leave_one_cluster_max_shift": self.leave_one_cluster_max_shift,
                }
            )
        return payload

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @property
    def receipt_sha256(self) -> str:
        return sha256_hex(self.canonical_bytes())


def _nested_resample(
    rows: tuple[PairwisePreference, ...], rng: Random
) -> tuple[PairwisePreference, ...]:
    sessions: dict[str, list[PairwisePreference]] = defaultdict(list)
    for row in rows:
        if row.session_id is None:
            raise ValueError("nested session resampling requires session identity")
        sessions[row.session_id].append(row)
    names = sorted(sessions)
    sampled = [names[rng.randrange(len(names))] for _ in names]
    return tuple(row for name in sampled for row in sessions[name])


def _fit_or_none(
    items: tuple[str, ...],
    rows: tuple[PairwisePreference, ...],
    config: ClusterBootstrapConfig,
) -> DavidsonFitReceipt | None:
    try:
        return fit_davidson(
            items=items,
            comparisons=rows,
            config=DavidsonFitConfig(
                regularization=config.regularization,
                maximum_iterations=config.maximum_iterations,
            ),
        )
    except ValueError:
        return None


def _subgroup_reversal(
    rows: tuple[PairwisePreference, ...],
    cluster_unit: str,
) -> bool:
    pair_signs: dict[tuple[str, str], set[int]] = defaultdict(set)
    grouped: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for row in rows:
        if row.outcome not in {PreferenceOutcome.LEFT, PreferenceOutcome.RIGHT}:
            continue
        left, right = sorted((row.left_item, row.right_item))
        winner = row.left_item if row.outcome is PreferenceOutcome.LEFT else row.right_item
        grouped[(_cluster_value(row, cluster_unit) or "", left, right)].append(
            1 if winner == left else -1
        )
    for (_, left, right), values in grouped.items():
        score = sum(values)
        if score:
            pair_signs[(left, right)].add(1 if score > 0 else -1)
    return any(len(signs) > 1 for signs in pair_signs.values())


def cluster_bootstrap(
    rows: tuple[PairwisePreference, ...],
    *,
    config: ClusterBootstrapConfig,
) -> ClusterBootstrapReceipt:
    """Resample whole assessor or session clusters deterministically."""

    eligible = tuple(
        sorted(
            (row for row in rows if row.outcome in _LIKELIHOOD_OUTCOMES),
            key=_row_key,
        )
    )
    if not eligible or any(
        _cluster_value(row, config.cluster_unit) is None for row in eligible
    ):
        identity = config.cluster_unit.casefold()
        raise ValueError(f"{identity} identity is required for cluster bootstrap")
    by_cluster: dict[str, tuple[PairwisePreference, ...]] = {}
    cluster_ids = tuple(
        sorted(
            {
                _cluster_value(row, config.cluster_unit) or ""
                for row in eligible
            }
        )
    )
    for cluster_id in cluster_ids:
        by_cluster[cluster_id] = tuple(
            row
            for row in eligible
            if _cluster_value(row, config.cluster_unit) == cluster_id
        )
    items = _items(eligible)
    full = _fit_or_none(items, eligible, config)
    rng = Random(config.seed)
    samples: dict[str, list[float]] = {item: [] for item in items}
    failed = 0
    boundary = 0
    graph_supported = 0
    for _ in range(config.replicates):
        selected = tuple(
            cluster_ids[rng.randrange(len(cluster_ids))] for _ in cluster_ids
        )
        sampled_rows: list[PairwisePreference] = []
        for cluster_id in selected:
            cluster = by_cluster[cluster_id]
            if config.nested_session_resampling:
                cluster = _nested_resample(cluster, rng)
            sampled_rows.extend(cluster)
        fitted = _fit_or_none(items, tuple(sampled_rows), config)
        if fitted is None:
            failed += 1
            continue
        graph_supported += 1
        if not fitted.converged:
            failed += 1
            if "BOUNDARY" in fitted.convergence_code:
                boundary += 1
            continue
        for item in items:
            samples[item].append(fitted.utilities[item])
    completed = config.replicates - failed
    alpha = (1.0 - config.confidence_level) / 2.0
    utility_intervals: dict[str, tuple[float, float]] = {}
    for item in items:
        if samples[item]:
            utility_intervals[item] = (
                _percentile(samples[item], alpha),
                _percentile(samples[item], 1.0 - alpha),
            )
        else:
            point = full.utilities[item] if full is not None else 0.0
            utility_intervals[item] = (point, point)

    leave_shifts: list[float] = []
    if full is not None and full.converged and len(cluster_ids) > 1:
        for omitted in cluster_ids:
            subset = tuple(
                row
                for row in eligible
                if _cluster_value(row, config.cluster_unit) != omitted
            )
            fitted = _fit_or_none(items, subset, config)
            if fitted is not None and fitted.converged:
                leave_shifts.append(
                    max(
                        abs(fitted.utilities[item] - full.utilities[item])
                        for item in items
                    )
                )
    reversal = _subgroup_reversal(eligible, config.cluster_unit)
    failed_fraction = failed / config.replicates
    stable = (
        completed > 0
        and failed_fraction <= config.maximum_failed_fraction
        and boundary == 0
        and not reversal
        and bool(leave_shifts)
    )
    return ClusterBootstrapReceipt(
        utility_intervals=utility_intervals,
        completed_replicates=completed,
        failed_replicates=failed,
        boundary_replicates=boundary,
        effective_unique_assessors=len(
            {row.assessor_id for row in eligible if row.assessor_id is not None}
        ),
        graph_supported_replicates=graph_supported,
        interval_method=f"{config.cluster_unit}_CLUSTER_PERCENTILE",
        seed=config.seed,
        stable=stable,
        leave_one_assessor_max_shift=max(leave_shifts) if leave_shifts else None,
        subgroup_reversal=reversal,
        cluster_unit=config.cluster_unit,
        effective_unique_clusters=len(cluster_ids),
        leave_one_cluster_max_shift=max(leave_shifts) if leave_shifts else None,
    )


@dataclass(frozen=True, slots=True)
class HeldoutValidationConfig:
    split_unit: str = "ASSESSOR"
    practical_margin: float = 0.0
    bootstrap_replicates: int = 200
    seed: int = 0
    baseline_probabilities: tuple[float, float, float] = (1 / 3, 1 / 3, 1 / 3)

    def __post_init__(self) -> None:
        split = self.split_unit.strip().upper()
        if split not in {"ASSESSOR", "SESSION", "MATRIX"}:
            raise ValueError("split_unit must be ASSESSOR, SESSION, or MATRIX")
        object.__setattr__(self, "split_unit", split)
        _finite_nonnegative(self.practical_margin, "practical_margin")
        if isinstance(self.bootstrap_replicates, bool) or self.bootstrap_replicates < 0:
            raise ValueError("bootstrap_replicates must be nonnegative")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ValueError("seed must be an integer")
        probabilities = tuple(float(value) for value in self.baseline_probabilities)
        if len(probabilities) != 3 or any(value <= 0 for value in probabilities):
            raise ValueError("baseline_probabilities must contain three positive values")
        total = sum(probabilities)
        object.__setattr__(
            self, "baseline_probabilities", tuple(value / total for value in probabilities)
        )


@dataclass(frozen=True, slots=True)
class HeldoutValidationReceipt:
    SCHEMA_VERSION: ClassVar[str] = "heldout_validation_receipt_v1"
    split_unit: str
    heldout_count: int
    multinomial_log_loss: float
    brier_score: float
    calibration_intercept: float | None
    calibration_slope: float | None
    baseline_log_loss: float
    paired_gain_interval: tuple[float, float]
    practical_margin: float
    passed: bool
    leakage_codes: tuple[str, ...]

    @property
    def authority(self) -> dict[str, bool]:
        return dict(_FALSE_AUTHORITY)

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "split_unit": self.split_unit,
            "heldout_count": self.heldout_count,
            "multinomial_log_loss": self.multinomial_log_loss,
            "brier_score": self.brier_score,
            "calibration_intercept": self.calibration_intercept,
            "calibration_slope": self.calibration_slope,
            "baseline_log_loss": self.baseline_log_loss,
            "paired_gain_interval": list(self.paired_gain_interval),
            "practical_margin": self.practical_margin,
            "passed": self.passed,
            "leakage_codes": list(self.leakage_codes),
            "authority": self.authority,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @property
    def receipt_sha256(self) -> str:
        return sha256_hex(self.canonical_bytes())


def _group_value(row: PairwisePreference, split_unit: str) -> str | None:
    return {
        "ASSESSOR": row.assessor_id,
        "SESSION": row.session_id,
        "MATRIX": row.matrix_id,
    }[split_unit]


def _outcome_index(row: PairwisePreference) -> int:
    return (
        0
        if row.outcome is PreferenceOutcome.LEFT
        else 1
        if row.outcome is PreferenceOutcome.RIGHT
        else 2
    )


def _calibration(
    probabilities: list[tuple[float, float, float]], outcomes: list[int]
) -> tuple[float | None, float | None]:
    if len(probabilities) < 3:
        return None, None
    xs: list[float] = []
    ys: list[float] = []
    for probability, outcome in zip(probabilities, outcomes):
        predicted = max(range(3), key=lambda index: probability[index])
        confidence = min(max(probability[predicted], 1e-12), 1 - 1e-12)
        xs.append(log(confidence / (1.0 - confidence)))
        ys.append(1.0 if predicted == outcome else 0.0)
    x_mean = mean(xs)
    y_mean = mean(ys)
    variance = sum((value - x_mean) ** 2 for value in xs)
    if variance <= 1e-15:
        return y_mean, None
    slope = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / variance
    return y_mean - slope * x_mean, slope


def validate_heldout(
    *,
    fitted: DavidsonFitReceipt,
    training: tuple[PairwisePreference, ...],
    heldout: tuple[PairwisePreference, ...],
    config: HeldoutValidationConfig,
) -> HeldoutValidationReceipt:
    """Score a frozen grouped holdout with multinomial proper scores."""

    if not fitted.converged:
        raise ValueError("fitted Davidson receipt must be converged")
    leakage: list[str] = []
    training_groups = {_group_value(row, config.split_unit) for row in training}
    heldout_groups = {_group_value(row, config.split_unit) for row in heldout}
    if None in training_groups or None in heldout_groups:
        leakage.append("GROUP_IDENTITY_MISSING")
    if training_groups.intersection(heldout_groups).difference({None}):
        leakage.append("GROUP_SPLIT_LEAKAGE")
    training_ids = {
        row.comparison_id for row in training if row.comparison_id is not None
    }
    heldout_ids = {
        row.comparison_id for row in heldout if row.comparison_id is not None
    }
    if training_ids.intersection(heldout_ids):
        leakage.append("COMPARISON_ID_SPLIT_LEAKAGE")
    if any((row.partition or "").upper() in {"HELDOUT", "FROZEN_TEST"} for row in training):
        leakage.append("FROZEN_TEST_IN_TRAINING")
    if any((row.partition or "").upper() == "TRAINING" for row in heldout):
        leakage.append("TRAINING_LABEL_IN_HELDOUT")
    evaluable = tuple(
        row
        for row in heldout
        if row.outcome in _LIKELIHOOD_OUTCOMES
        and row.left_item in fitted.utilities
        and row.right_item in fitted.utilities
    )
    if not evaluable:
        raise ValueError("heldout data contain no evaluable preference rows")
    probabilities = [
        davidson_pair_probabilities(fitted, row.left_item, row.right_item)
        for row in evaluable
    ]
    outcomes = [_outcome_index(row) for row in evaluable]
    model_losses = [
        -log(max(probability[outcome], 1e-15))
        for probability, outcome in zip(probabilities, outcomes)
    ]
    brier_rows = [
        sum(
            (probability[index] - (1.0 if index == outcome else 0.0)) ** 2
            for index in range(3)
        )
        for probability, outcome in zip(probabilities, outcomes)
    ]
    baseline_losses = [
        -log(config.baseline_probabilities[outcome]) for outcome in outcomes
    ]
    gains = [baseline - model for baseline, model in zip(baseline_losses, model_losses)]
    by_group: dict[str, list[float]] = defaultdict(list)
    for row, gain in zip(evaluable, gains):
        by_group[_group_value(row, config.split_unit) or "MISSING"].append(gain)
    group_names = sorted(by_group)
    bootstrap_means: list[float] = []
    if config.bootstrap_replicates:
        rng = Random(config.seed)
        for _ in range(config.bootstrap_replicates):
            selected = [group_names[rng.randrange(len(group_names))] for _ in group_names]
            values = [value for group in selected for value in by_group[group]]
            bootstrap_means.append(mean(values))
    else:
        bootstrap_means.append(mean(gains))
    paired_interval = (
        _percentile(bootstrap_means, 0.025),
        _percentile(bootstrap_means, 0.975),
    )
    calibration_intercept, calibration_slope = _calibration(probabilities, outcomes)
    leakage_codes = tuple(sorted(set(leakage)))
    return HeldoutValidationReceipt(
        split_unit=config.split_unit,
        heldout_count=len(evaluable),
        multinomial_log_loss=mean(model_losses),
        brier_score=mean(brier_rows),
        calibration_intercept=calibration_intercept,
        calibration_slope=calibration_slope,
        baseline_log_loss=mean(baseline_losses),
        paired_gain_interval=paired_interval,
        practical_margin=config.practical_margin,
        passed=(not leakage_codes and paired_interval[0] > config.practical_margin),
        leakage_codes=leakage_codes,
    )


@dataclass(frozen=True, slots=True)
class TransitivityConfig:
    stable_pair_margin: float = 0.5
    temporal_crossover_margin: float = 0.5

    def __post_init__(self) -> None:
        for name in ("stable_pair_margin", "temporal_crossover_margin"):
            value = getattr(self, name)
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be from zero to one")


@dataclass(frozen=True, slots=True)
class TransitivityReceipt:
    SCHEMA_VERSION: ClassVar[str] = "transitivity_receipt_v1"
    state: str
    stable_cycles: tuple[tuple[str, str, str], ...]
    temporal_crossovers: tuple[tuple[str, str], ...]
    window_probabilities: dict[str, tuple[float, float, float]]
    global_winner_withheld: bool

    @property
    def authority(self) -> dict[str, bool]:
        return dict(_FALSE_AUTHORITY)

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "state": self.state,
            "stable_cycles": [list(value) for value in self.stable_cycles],
            "temporal_crossovers": [list(value) for value in self.temporal_crossovers],
            "window_probabilities": {
                key: list(value) for key, value in self.window_probabilities.items()
            },
            "global_winner_withheld": self.global_winner_withheld,
            "authority": self.authority,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())


def _pair_scores(
    rows: tuple[PairwisePreference, ...],
) -> dict[tuple[str, str], tuple[int, int, int]]:
    counts: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0, 0])
    for row in rows:
        if row.outcome not in _LIKELIHOOD_OUTCOMES:
            continue
        left, right = sorted((row.left_item, row.right_item))
        winner = (
            row.left_item
            if row.outcome is PreferenceOutcome.LEFT
            else row.right_item
            if row.outcome is PreferenceOutcome.RIGHT
            else None
        )
        if winner is None:
            counts[(left, right)][2] += 1
        elif winner == left:
            counts[(left, right)][0] += 1
        else:
            counts[(left, right)][1] += 1
    return {pair: tuple(values) for pair, values in counts.items()}


def _direction(counts: tuple[int, int, int], margin: float) -> int:
    total = sum(counts)
    if not total:
        return 0
    difference = (counts[0] - counts[1]) / total
    return 1 if difference >= margin else -1 if difference <= -margin else 0


def assess_transitivity(
    rows: tuple[PairwisePreference, ...],
    *,
    config: TransitivityConfig,
) -> TransitivityReceipt:
    """Detect stable majority cycles and time-window direction reversals."""

    overall = _pair_scores(rows)
    items = _items(rows)
    directions = {pair: _direction(counts, config.stable_pair_margin) for pair, counts in overall.items()}
    cycles: list[tuple[str, str, str]] = []
    for a, b, c in combinations(items, 3):
        ab = directions.get((a, b), 0)
        bc = directions.get((b, c), 0)
        ac = directions.get((a, c), 0)
        if (ab, bc, ac) in {(1, 1, -1), (-1, -1, 1)}:
            cycles.append((a, b, c))

    by_window: dict[str, list[PairwisePreference]] = defaultdict(list)
    for row in rows:
        if row.time_window_id is not None:
            by_window[row.time_window_id].append(row)
    window_probabilities: dict[str, tuple[float, float, float]] = {}
    window_directions: dict[tuple[str, str], set[int]] = defaultdict(set)
    for window in sorted(by_window):
        for pair, counts in sorted(_pair_scores(tuple(by_window[window])).items()):
            total = sum(counts)
            window_probabilities[f"{window}|{pair[0]}|{pair[1]}"] = tuple(
                value / total for value in counts
            )
            direction = _direction(counts, config.temporal_crossover_margin)
            if direction:
                window_directions[pair].add(direction)
    crossovers = tuple(
        pair for pair, values in sorted(window_directions.items()) if len(values) > 1
    )
    if cycles:
        state = "NONTRANSITIVE_OR_MISSPECIFIED"
    elif crossovers:
        state = "TEMPORAL_CROSSOVER"
    else:
        state = "PASS"
    return TransitivityReceipt(
        state=state,
        stable_cycles=tuple(cycles),
        temporal_crossovers=crossovers,
        window_probabilities=window_probabilities,
        global_winner_withheld=bool(cycles or crossovers),
    )


@dataclass(frozen=True, slots=True)
class PreferenceDiagnosticsConfig:
    cluster_unit: str = "ASSESSOR"
    maximum_order_effect: float = 0.25
    maximum_carryover_effect: float = 0.25
    maximum_repeated_exposure_effect: float = 0.25
    maximum_leave_one_cluster_shift: float = 1.0
    counting_resolution_margin: float = 0.95
    regularization: float = 0.1
    maximum_iterations: int = 300

    def __post_init__(self) -> None:
        unit = self.cluster_unit.strip().upper()
        if unit not in {"ASSESSOR", "SESSION"}:
            raise ValueError("cluster_unit must be ASSESSOR or SESSION")
        object.__setattr__(self, "cluster_unit", unit)
        for name in (
            "maximum_order_effect",
            "maximum_carryover_effect",
            "maximum_repeated_exposure_effect",
            "counting_resolution_margin",
        ):
            value = getattr(self, name)
            if not isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be finite and from zero to one")
        _finite_nonnegative(
            self.maximum_leave_one_cluster_shift,
            "maximum_leave_one_cluster_shift",
        )
        _finite_nonnegative(self.regularization, "regularization")
        if isinstance(self.maximum_iterations, bool) or self.maximum_iterations < 1:
            raise ValueError("maximum_iterations must be a positive integer")

    def as_dict(self) -> dict[str, object]:
        return {
            "cluster_unit": self.cluster_unit,
            "maximum_order_effect": self.maximum_order_effect,
            "maximum_carryover_effect": self.maximum_carryover_effect,
            "maximum_repeated_exposure_effect": (
                self.maximum_repeated_exposure_effect
            ),
            "maximum_leave_one_cluster_shift": (
                self.maximum_leave_one_cluster_shift
            ),
            "counting_resolution_margin": self.counting_resolution_margin,
            "regularization": self.regularization,
            "maximum_iterations": self.maximum_iterations,
        }


@dataclass(frozen=True, slots=True)
class PreferenceScopeDiagnosticsV2:
    SCHEMA_VERSION: ClassVar[str] = "preference_scope_diagnostics_v2"
    criterion_id: str | None
    configuration: tuple[tuple[str, object], ...]
    training_sha256: str
    heldout_sha256: str
    split_sha256: str
    connected_components: tuple[tuple[str, ...], ...]
    order_effect: float | None
    carryover_effect: float | None
    repeated_exposure_effect: float | None
    influential_cluster_id: str | None
    leave_one_cluster_max_shift: float | None
    counting_winner: str | None
    temporal_crossovers: tuple[tuple[str, str], ...]
    blocker_codes: tuple[str, ...]

    @property
    def authority(self) -> dict[str, bool]:
        return dict(_FALSE_AUTHORITY)

    @property
    def configuration_sha256(self) -> str:
        return sha256_hex(canonical_json_bytes(dict(self.configuration)))

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "criterion_id": self.criterion_id,
            "configuration": dict(self.configuration),
            "configuration_sha256": self.configuration_sha256,
            "training_sha256": self.training_sha256,
            "heldout_sha256": self.heldout_sha256,
            "split_sha256": self.split_sha256,
            "connected_components": [
                list(component) for component in self.connected_components
            ],
            "order_effect": self.order_effect,
            "carryover_effect": self.carryover_effect,
            "repeated_exposure_effect": self.repeated_exposure_effect,
            "influential_cluster_id": self.influential_cluster_id,
            "leave_one_cluster_max_shift": self.leave_one_cluster_max_shift,
            "counting_winner": self.counting_winner,
            "temporal_crossovers": [
                list(pair) for pair in self.temporal_crossovers
            ],
            "blocker_codes": list(self.blocker_codes),
            "authority": self.authority,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @property
    def receipt_sha256(self) -> str:
        return sha256_hex(self.canonical_bytes())


def _rows_sha256(rows: tuple[PairwisePreference, ...]) -> str:
    ordered = sorted(
        (row.as_dict() for row in rows),
        key=canonical_json_bytes,
    )
    return sha256_hex(canonical_json_bytes(ordered))


def _connected_components(
    rows: tuple[PairwisePreference, ...],
) -> tuple[tuple[str, ...], ...]:
    items = _items(rows)
    adjacency = {item: set() for item in items}
    for row in rows:
        if row.outcome not in _LIKELIHOOD_OUTCOMES:
            continue
        adjacency[row.left_item].add(row.right_item)
        adjacency[row.right_item].add(row.left_item)
    remaining = set(items)
    components: list[tuple[str, ...]] = []
    while remaining:
        root = min(remaining)
        seen = {root}
        frontier = [root]
        while frontier:
            current = frontier.pop()
            for neighbor in sorted(adjacency[current].difference(seen)):
                seen.add(neighbor)
                frontier.append(neighbor)
        remaining.difference_update(seen)
        components.append(tuple(sorted(seen)))
    return tuple(components)


def _pair_condition_effect(
    rows: tuple[PairwisePreference, ...],
    condition: Callable[[PairwisePreference, str, str], int | None],
) -> float | None:
    grouped: dict[tuple[str, str], dict[int, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in rows:
        if row.outcome not in {PreferenceOutcome.LEFT, PreferenceOutcome.RIGHT}:
            continue
        left, right = sorted((row.left_item, row.right_item))
        group = condition(row, left, right)
        if group not in {0, 1}:
            continue
        winner = row.left_item if row.outcome is PreferenceOutcome.LEFT else row.right_item
        grouped[(left, right)][group].append(1.0 if winner == left else 0.0)
    effects = tuple(
        abs(mean(values[0]) - mean(values[1]))
        for values in grouped.values()
        if values.get(0) and values.get(1)
    )
    return max(effects) if effects else None


def _cluster_value(row: PairwisePreference, cluster_unit: str) -> str | None:
    return row.assessor_id if cluster_unit == "ASSESSOR" else row.session_id


def _influential_cluster(
    *,
    fitted: DavidsonFitReceipt,
    rows: tuple[PairwisePreference, ...],
    config: PreferenceDiagnosticsConfig,
) -> tuple[str | None, float | None]:
    clusters = tuple(
        sorted(
            {
                value
                for row in rows
                if (value := _cluster_value(row, config.cluster_unit)) is not None
            }
        )
    )
    if len(clusters) < 2:
        return None, None
    shifts: list[tuple[float, str]] = []
    items = tuple(fitted.utilities)
    for omitted in clusters:
        subset = tuple(
            row
            for row in rows
            if _cluster_value(row, config.cluster_unit) != omitted
        )
        try:
            reduced = fit_davidson(
                items=items,
                comparisons=subset,
                config=DavidsonFitConfig(
                    regularization=config.regularization,
                    maximum_iterations=config.maximum_iterations,
                ),
            )
        except ValueError:
            continue
        if reduced.converged:
            shifts.append(
                (
                    max(
                        abs(reduced.utilities[item] - fitted.utilities[item])
                        for item in items
                    ),
                    omitted,
                )
            )
    if not shifts:
        return None, None
    shift, cluster = min(shifts, key=lambda item: (-item[0], item[1]))
    return cluster, shift


def _counting_winner(
    rows: tuple[PairwisePreference, ...],
    margin: float,
) -> str | None:
    items = _items(rows)
    scores = _pair_scores(rows)
    directions = {pair: _direction(counts, margin) for pair, counts in scores.items()}
    winners: list[str] = []
    for candidate in items:
        beats_every_other = True
        for other in items:
            if other == candidate:
                continue
            pair = tuple(sorted((candidate, other)))
            direction = directions.get(pair, 0)
            candidate_direction = 1 if candidate == pair[0] else -1
            if direction != candidate_direction:
                beats_every_other = False
                break
        if beats_every_other:
            winners.append(candidate)
    return winners[0] if len(winners) == 1 else None


def diagnose_preference_scope(
    *,
    fitted: DavidsonFitReceipt,
    training: tuple[PairwisePreference, ...],
    heldout: tuple[PairwisePreference, ...],
    cluster_bootstrap_receipt: ClusterBootstrapReceipt,
    heldout_validation_receipt: HeldoutValidationReceipt,
    transitivity_receipt: TransitivityReceipt,
    config: PreferenceDiagnosticsConfig,
) -> PreferenceScopeDiagnosticsV2:
    """Freeze scope, confounding, influence, and counting diagnostics."""

    training_hash = _rows_sha256(training)
    heldout_hash = _rows_sha256(heldout)
    split_hash = sha256_hex(
        canonical_json_bytes(
            {
                "cluster_unit": config.cluster_unit,
                "training_sha256": training_hash,
                "heldout_sha256": heldout_hash,
            }
        )
    )
    components = _connected_components(training)
    rows = training + heldout
    criteria = {row.criterion_id for row in rows if row.criterion_id is not None}
    protocols = {row.protocol_id for row in rows if row.protocol_id is not None}
    criterion_id = next(iter(criteria)) if len(criteria) == 1 else None
    order_effect = _pair_condition_effect(
        rows,
        lambda row, left, right: (
            0
            if row.first_presented_item == left
            else 1
            if row.first_presented_item == right
            else None
        ),
    )
    carryover_effect = _pair_condition_effect(
        rows,
        lambda row, left, right: (
            0
            if row.previous_presented_item == left
            else 1
            if row.previous_presented_item == right
            else None
        ),
    )
    repeated_effect = _pair_condition_effect(
        rows,
        lambda row, _left, _right: (
            None
            if row.position_in_session is None
            else 0
            if row.position_in_session == 1
            else 1
        ),
    )
    influential_id, influential_shift = _influential_cluster(
        fitted=fitted,
        rows=training,
        config=config,
    )
    blockers: list[str] = []
    if any(row.criterion_id is None for row in rows) or len(criteria) != 1:
        blockers.append("CRITERION_MIXED_OR_MISSING")
    if any(row.protocol_id is None for row in rows) or len(protocols) != 1:
        blockers.append("PROTOCOL_SCOPE_MIXED_OR_MISSING")
    if len(components) != 1:
        blockers.append("DISCONNECTED_GRAPH")
    if order_effect is not None and order_effect > config.maximum_order_effect:
        blockers.append("ORDER_CONFOUNDED")
    if (
        carryover_effect is not None
        and carryover_effect > config.maximum_carryover_effect
    ):
        blockers.append("CARRYOVER_CONFOUNDED")
    if (
        repeated_effect is not None
        and repeated_effect > config.maximum_repeated_exposure_effect
    ):
        blockers.append("REPEATED_EXPOSURE_CONFOUNDED")
    if (
        influential_shift is not None
        and influential_shift > config.maximum_leave_one_cluster_shift
    ):
        blockers.append("INFLUENTIAL_CLUSTER")
    if heldout_validation_receipt.leakage_codes:
        blockers.extend(heldout_validation_receipt.leakage_codes)
    if transitivity_receipt.temporal_crossovers:
        blockers.append("TEMPORAL_CROSSOVER")
    if transitivity_receipt.stable_cycles:
        blockers.append("NONTRANSITIVE_OR_MISSPECIFIED")
    if not cluster_bootstrap_receipt.stable:
        blockers.append("CLUSTER_BOOTSTRAP_UNSTABLE")
    return PreferenceScopeDiagnosticsV2(
        criterion_id=criterion_id,
        configuration=tuple(config.as_dict().items()),
        training_sha256=training_hash,
        heldout_sha256=heldout_hash,
        split_sha256=split_hash,
        connected_components=components,
        order_effect=order_effect,
        carryover_effect=carryover_effect,
        repeated_exposure_effect=repeated_effect,
        influential_cluster_id=influential_id,
        leave_one_cluster_max_shift=influential_shift,
        counting_winner=_counting_winner(
            training,
            config.counting_resolution_margin,
        ),
        temporal_crossovers=transitivity_receipt.temporal_crossovers,
        blocker_codes=tuple(sorted(set(blockers))),
    )


@dataclass(frozen=True, slots=True)
class NextPairConstraints:
    decision_resolved: bool = False
    connected_components: tuple[tuple[str, ...], ...] = ()
    exposure_counts: tuple[tuple[str, int], ...] = ()
    maximum_exposure: int | None = None
    forbidden_carryover_pairs: tuple[tuple[str, str], ...] = ()
    first_position_counts: tuple[tuple[str, int], ...] = ()
    pair_observation_counts: tuple[tuple[str, str, int], ...] = ()
    exploration_quota_remaining: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.decision_resolved, bool):
            raise TypeError("decision_resolved must be boolean")
        if self.maximum_exposure is not None and self.maximum_exposure < 1:
            raise ValueError("maximum_exposure must be positive")
        if self.exploration_quota_remaining < 0:
            raise ValueError("exploration_quota_remaining must be nonnegative")


@dataclass(frozen=True, slots=True)
class NextPairReceipt:
    SCHEMA_VERSION: ClassVar[str] = "next_pair_receipt_v1"
    selected_pair: tuple[str, str] | None
    reason_code: str
    eligible_count: int
    score_components: tuple[tuple[str, float], ...]

    @property
    def authority(self) -> dict[str, bool]:
        return dict(_FALSE_AUTHORITY)

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "selected_pair": (
                None if self.selected_pair is None else list(self.selected_pair)
            ),
            "reason_code": self.reason_code,
            "eligible_count": self.eligible_count,
            "score_components": [list(value) for value in self.score_components],
            "authority": self.authority,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())


def _component_map(
    components: tuple[tuple[str, ...], ...]
) -> dict[str, int]:
    return {
        item: index for index, component in enumerate(components) for item in component
    }


def select_next_pair(
    *,
    fitted: DavidsonFitReceipt,
    eligible_pairs: tuple[tuple[str, str], ...],
    constraints: NextPairConstraints,
) -> NextPairReceipt:
    """Select zero or one pair after connectivity, burden, and order constraints."""

    if constraints.decision_resolved:
        return NextPairReceipt(None, "DECISION_RESOLVED", 0, ())
    pairs = tuple(sorted({tuple(sorted(pair)) for pair in eligible_pairs}))
    if any(len(pair) != 2 or pair[0] == pair[1] for pair in pairs):
        raise ValueError("eligible pairs must contain two different item IDs")
    exposure = dict(constraints.exposure_counts)
    forbidden = {tuple(sorted(pair)) for pair in constraints.forbidden_carryover_pairs}
    filtered = tuple(
        pair
        for pair in pairs
        if pair not in forbidden
        and (
            constraints.maximum_exposure is None
            or all(exposure.get(item, 0) < constraints.maximum_exposure for item in pair)
        )
    )
    if not filtered:
        return NextPairReceipt(None, "NO_ELIGIBLE_PAIR", 0, ())
    components = _component_map(constraints.connected_components)
    bridges = tuple(
        pair
        for pair in filtered
        if pair[0] in components
        and pair[1] in components
        and components[pair[0]] != components[pair[1]]
    )
    if bridges:
        selected = min(bridges)
        return NextPairReceipt(
            selected,
            "CONNECTIVITY_FIRST",
            len(filtered),
            (("connectivity_gain", 1.0),),
        )
    first_counts = dict(constraints.first_position_counts)
    pair_counts = {
        tuple(sorted((left, right))): count
        for left, right, count in constraints.pair_observation_counts
    }

    def score(pair: tuple[str, str]) -> tuple[float, float, float, tuple[str, str]]:
        if all(item in fitted.utilities for item in pair):
            probabilities = davidson_pair_probabilities(fitted, *pair)
            uncertainty = 1.0 - max(probabilities)
        else:
            uncertainty = 1.0
        order_imbalance = abs(first_counts.get(pair[0], 0) - first_counts.get(pair[1], 0))
        burden = exposure.get(pair[0], 0) + exposure.get(pair[1], 0)
        repetitions = pair_counts.get(pair, 0)
        return (-uncertainty, order_imbalance + repetitions, burden, pair)

    selected = min(filtered, key=score)
    reason = (
        "EXPLORATION_QUOTA"
        if constraints.exploration_quota_remaining > 0
        else "UNCERTAINTY_REDUCTION"
    )
    selected_score = score(selected)
    return NextPairReceipt(
        selected,
        reason,
        len(filtered),
        (
            ("uncertainty", -selected_score[0]),
            ("order_and_repeat_penalty", selected_score[1]),
            ("exposure_burden", selected_score[2]),
        ),
    )


__all__ = [
    "ClusterBootstrapConfig",
    "ClusterBootstrapReceipt",
    "HeldoutValidationConfig",
    "HeldoutValidationReceipt",
    "NextPairConstraints",
    "NextPairReceipt",
    "PreferenceDiagnosticsConfig",
    "PreferenceScopeDiagnosticsV2",
    "TransitivityConfig",
    "TransitivityReceipt",
    "assess_transitivity",
    "cluster_bootstrap",
    "diagnose_preference_scope",
    "select_next_pair",
    "validate_heldout",
]
