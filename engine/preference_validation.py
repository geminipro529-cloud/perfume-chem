"""Scoped validation utilities for Davidson preference evidence."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from math import isfinite, log
from random import Random
from statistics import mean
from typing import ClassVar

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

    @property
    def authority(self) -> dict[str, bool]:
        return dict(_FALSE_AUTHORITY)

    def as_dict(self) -> dict[str, object]:
        return {
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


def _subgroup_reversal(rows: tuple[PairwisePreference, ...]) -> bool:
    pair_signs: dict[tuple[str, str], set[int]] = defaultdict(set)
    grouped: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for row in rows:
        if row.outcome not in {PreferenceOutcome.LEFT, PreferenceOutcome.RIGHT}:
            continue
        left, right = sorted((row.left_item, row.right_item))
        winner = row.left_item if row.outcome is PreferenceOutcome.LEFT else row.right_item
        grouped[(row.assessor_id or "", left, right)].append(
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
    """Resample whole assessor clusters with deterministic ordering and RNG."""

    eligible = tuple(sorted((row for row in rows if row.outcome in _LIKELIHOOD_OUTCOMES), key=_row_key))
    if not eligible or any(row.assessor_id is None for row in eligible):
        raise ValueError("assessor identity is required for cluster bootstrap")
    by_assessor: dict[str, tuple[PairwisePreference, ...]] = {}
    for assessor in sorted({row.assessor_id or "" for row in eligible}):
        by_assessor[assessor] = tuple(
            row for row in eligible if row.assessor_id == assessor
        )
    assessors = tuple(by_assessor)
    items = _items(eligible)
    full = _fit_or_none(items, eligible, config)
    rng = Random(config.seed)
    samples: dict[str, list[float]] = {item: [] for item in items}
    failed = 0
    boundary = 0
    graph_supported = 0
    for _ in range(config.replicates):
        selected = tuple(
            assessors[rng.randrange(len(assessors))] for _ in assessors
        )
        sampled_rows: list[PairwisePreference] = []
        for assessor in selected:
            cluster = by_assessor[assessor]
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
    if full is not None and full.converged and len(assessors) > 1:
        for omitted in assessors:
            subset = tuple(row for row in eligible if row.assessor_id != omitted)
            fitted = _fit_or_none(items, subset, config)
            if fitted is not None and fitted.converged:
                leave_shifts.append(
                    max(
                        abs(fitted.utilities[item] - full.utilities[item])
                        for item in items
                    )
                )
    reversal = _subgroup_reversal(eligible)
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
        effective_unique_assessors=len(assessors),
        graph_supported_replicates=graph_supported,
        interval_method="ASSESSOR_CLUSTER_PERCENTILE",
        seed=config.seed,
        stable=stable,
        leave_one_assessor_max_shift=max(leave_shifts) if leave_shifts else None,
        subgroup_reversal=reversal,
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
    training_group_count: int
    heldout_group_count: int
    bootstrap_replicates: int
    bootstrap_seed: int
    baseline_probabilities: tuple[float, float, float]

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
            "training_group_count": self.training_group_count,
            "heldout_group_count": self.heldout_group_count,
            "bootstrap_replicates": self.bootstrap_replicates,
            "bootstrap_seed": self.bootstrap_seed,
            "baseline_probabilities": list(self.baseline_probabilities),
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
    if any((row.partition or "").upper() in {"HELDOUT", "FROZEN_TEST"} for row in training):
        leakage.append("FROZEN_TEST_IN_TRAINING")
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
        training_group_count=len(training_groups.difference({None})),
        heldout_group_count=len(heldout_groups.difference({None})),
        bootstrap_replicates=config.bootstrap_replicates,
        bootstrap_seed=config.seed,
        baseline_probabilities=config.baseline_probabilities,
    )


@dataclass(frozen=True, slots=True)
class OrderCarryoverConfig:
    """Hard design limits for realized order and sequential carryover."""

    maximum_pair_order_count_difference: int = 1
    maximum_absolute_first_position_effect: float = 0.25
    require_qualified_carryover: bool = True

    def __post_init__(self) -> None:
        if (
            isinstance(self.maximum_pair_order_count_difference, bool)
            or not isinstance(self.maximum_pair_order_count_difference, int)
            or self.maximum_pair_order_count_difference < 0
        ):
            raise ValueError(
                "maximum_pair_order_count_difference must be a nonnegative integer"
            )
        effect = self.maximum_absolute_first_position_effect
        if isinstance(effect, bool) or not isinstance(effect, (int, float)):
            raise TypeError(
                "maximum_absolute_first_position_effect must be a real number"
            )
        effect = float(effect)
        if not isfinite(effect) or not 0 <= effect <= 1:
            raise ValueError(
                "maximum_absolute_first_position_effect must be from zero to one"
            )
        object.__setattr__(self, "maximum_absolute_first_position_effect", effect)
        if not isinstance(self.require_qualified_carryover, bool):
            raise TypeError("require_qualified_carryover must be boolean")


@dataclass(frozen=True, slots=True)
class OrderCarryoverReceipt:
    """Observed, not merely planned, order and sequence diagnostics."""

    SCHEMA_VERSION: ClassVar[str] = "order_carryover_receipt_v1"
    pair_order_counts: tuple[tuple[str, str, int, int], ...]
    directional_comparison_count: int
    tie_count: int
    stratified_first_position_effect: float | None
    order_imbalanced_pairs: tuple[tuple[str, str], ...]
    order_confounding_pairs: tuple[tuple[str, str], ...]
    sequence_failure_codes: tuple[str, ...]
    carryover_qualified: bool
    passed: bool

    @property
    def authority(self) -> dict[str, bool]:
        return dict(_FALSE_AUTHORITY)

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "pair_order_counts": [list(value) for value in self.pair_order_counts],
            "directional_comparison_count": self.directional_comparison_count,
            "tie_count": self.tie_count,
            "stratified_first_position_effect": self.stratified_first_position_effect,
            "order_imbalanced_pairs": [list(value) for value in self.order_imbalanced_pairs],
            "order_confounding_pairs": [
                list(value) for value in self.order_confounding_pairs
            ],
            "sequence_failure_codes": list(self.sequence_failure_codes),
            "carryover_qualified": self.carryover_qualified,
            "passed": self.passed,
            "authority": self.authority,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @property
    def receipt_sha256(self) -> str:
        return sha256_hex(self.canonical_bytes())


def assess_order_and_carryover(
    rows: tuple[PairwisePreference, ...],
    *,
    config: OrderCarryoverConfig,
    carryover_qualified: bool,
) -> OrderCarryoverReceipt:
    """Audit realized pair orders and the integrity of within-session sequences."""

    if not isinstance(carryover_qualified, bool):
        raise TypeError("carryover_qualified must be boolean")
    pair_orders: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: defaultdict(int)
    )
    pair_partition_orders: dict[
        tuple[tuple[str, str], str], dict[str, int]
    ] = defaultdict(lambda: defaultdict(int))
    pair_first_outcomes: dict[tuple[str, str], list[int]] = defaultdict(list)
    sequence_failures: set[str] = set()
    directional_count = 0
    tie_count = 0
    for row in rows:
        if row.outcome not in _LIKELIHOOD_OUTCOMES:
            continue
        pair = tuple(sorted((row.left_item, row.right_item)))
        if row.first_presented_item is None:
            sequence_failures.add("FIRST_PRESENTED_ITEM_MISSING")
        else:
            pair_orders[pair][row.first_presented_item] += 1
            pair_partition_orders[(pair, row.partition or "UNSCOPED")][
                row.first_presented_item
            ] += 1
        if row.outcome is PreferenceOutcome.NO_PREFERENCE:
            tie_count += 1
            continue
        directional_count += 1
        if row.first_presented_item is not None:
            pair_first_outcomes[pair].append(
                1 if row.preferred_item == row.first_presented_item else -1
            )

    pair_order_counts: list[tuple[str, str, int, int]] = []
    imbalanced: list[tuple[str, str]] = []
    confounded: list[tuple[str, str]] = []
    pair_first_effects: list[float] = []
    for pair in sorted(pair_orders):
        first_count = pair_orders[pair].get(pair[0], 0)
        second_count = pair_orders[pair].get(pair[1], 0)
        pair_order_counts.append((pair[0], pair[1], first_count, second_count))
        if (
            first_count == 0
            or second_count == 0
            or abs(first_count - second_count)
            > config.maximum_pair_order_count_difference
        ):
            imbalanced.append(pair)
        outcomes = pair_first_outcomes.get(pair, [])
        if outcomes and abs(sum(outcomes) / len(outcomes)) == 1.0:
            confounded.append(pair)
        if outcomes:
            pair_first_effects.append(sum(outcomes) / len(outcomes))

    for (pair, _partition), counts in sorted(pair_partition_orders.items()):
        if counts.get(pair[0], 0) == 0 or counts.get(pair[1], 0) == 0:
            confounded.append(pair)
    confounded = sorted(set(confounded))

    first_effect = (
        round(sum(pair_first_effects) / len(pair_first_effects), 12)
        if pair_first_effects
        else None
    )
    by_session: dict[tuple[str, str], list[PairwisePreference]] = defaultdict(list)
    for row in rows:
        if row.assessor_id is None or row.session_id is None:
            sequence_failures.add("SESSION_IDENTITY_MISSING")
            continue
        by_session[(row.assessor_id, row.session_id)].append(row)
    has_sequential_exposure = False
    for session_rows in by_session.values():
        positions = [row.position_in_session for row in session_rows]
        if any(position is None for position in positions):
            sequence_failures.add("SESSION_POSITION_MISSING")
            continue
        integer_positions = [int(position) for position in positions if position is not None]
        if len(integer_positions) != len(set(integer_positions)):
            sequence_failures.add("DUPLICATE_SESSION_POSITION")
        if sorted(integer_positions) != list(range(1, len(integer_positions) + 1)):
            sequence_failures.add("NONCONTIGUOUS_SESSION_SEQUENCE")
        for row in session_rows:
            if row.position_in_session == 1:
                if (
                    row.previous_presented_item is not None
                    or row.previous_presented_sample_sha256 is not None
                ):
                    sequence_failures.add("UNEXPECTED_PREVIOUS_PRESENTATION")
                continue
            has_sequential_exposure = True
            if row.previous_presented_item is None:
                sequence_failures.add("PREVIOUS_PRESENTED_ITEM_MISSING")
            if row.previous_presented_sample_sha256 is None:
                sequence_failures.add("PREVIOUS_PRESENTED_SAMPLE_MISSING")
    if (
        config.require_qualified_carryover
        and has_sequential_exposure
        and not carryover_qualified
    ):
        sequence_failures.add("CARRYOVER_CONTROL_NOT_QUALIFIED")
    if first_effect is not None and (
        abs(first_effect) > config.maximum_absolute_first_position_effect
    ):
        sequence_failures.add("FIRST_POSITION_EFFECT_EXCEEDS_LIMIT")
    passed = not (imbalanced or confounded or sequence_failures)
    return OrderCarryoverReceipt(
        pair_order_counts=tuple(pair_order_counts),
        directional_comparison_count=directional_count,
        tie_count=tie_count,
        stratified_first_position_effect=first_effect,
        order_imbalanced_pairs=tuple(imbalanced),
        order_confounding_pairs=tuple(confounded),
        sequence_failure_codes=tuple(sorted(sequence_failures)),
        carryover_qualified=carryover_qualified,
        passed=passed,
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
    "OrderCarryoverConfig",
    "OrderCarryoverReceipt",
    "TransitivityConfig",
    "TransitivityReceipt",
    "assess_order_and_carryover",
    "assess_transitivity",
    "cluster_bootstrap",
    "select_next_pair",
    "validate_heldout",
]
