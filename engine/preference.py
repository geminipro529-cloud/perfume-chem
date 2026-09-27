"""Conservatively gated Bradley-Terry preference diagnostics."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from itertools import combinations
from math import exp, isfinite
from random import Random
from typing import Any, Mapping

from engine.scientific_contract import EvidenceDescriptor, ScientificClass


class PreferenceFitStatus(str, Enum):
    WITHHELD = "withheld"
    DIAGNOSTIC = "diagnostic"
    VALIDATED = "validated"


@dataclass(frozen=True, slots=True)
class PairwisePreference:
    left_item: str
    right_item: str
    preferred_item: str | None
    comparison_id: str | None = None
    assessor_id: str | None = None
    protocol_id: str | None = None
    criterion_id: str | None = None
    time_seconds: float | None = None
    first_presented_item: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.left_item, str) or not isinstance(self.right_item, str):
            raise TypeError("pairwise item identities must be text")
        if self.preferred_item is not None and not isinstance(
            self.preferred_item, str
        ):
            raise TypeError("preferred_item must be text when provided")
        if self.first_presented_item is not None and not isinstance(
            self.first_presented_item, str
        ):
            raise TypeError("first_presented_item must be text when provided")
        left = self.left_item.strip()
        right = self.right_item.strip()
        preferred = self.preferred_item.strip() if self.preferred_item else None
        if not left or not right or left == right:
            raise ValueError("pairwise comparison requires two different named items")
        if preferred is not None and preferred not in {left, right}:
            raise ValueError("preferred item must be the left item, right item, or None for a tie")
        object.__setattr__(self, "left_item", left)
        object.__setattr__(self, "right_item", right)
        object.__setattr__(self, "preferred_item", preferred)
        for name in (
            "comparison_id",
            "assessor_id",
            "protocol_id",
            "criterion_id",
        ):
            value = getattr(self, name)
            if value is not None and not isinstance(value, str):
                raise TypeError(f"{name} must be text when provided")
            normalized = value.strip() if value is not None else None
            if value is not None and not normalized:
                raise ValueError(f"{name} must be nonblank when provided")
            object.__setattr__(self, name, normalized)
        if self.time_seconds is not None and (
            isinstance(self.time_seconds, bool)
            or not isfinite(self.time_seconds)
            or self.time_seconds < 0
        ):
            raise ValueError("time_seconds must be finite and nonnegative")
        first = (
            self.first_presented_item.strip()
            if self.first_presented_item is not None
            else None
        )
        if first is not None and first not in {left, right}:
            raise ValueError("first presented item must be the left or right item")
        object.__setattr__(self, "first_presented_item", first)

    def as_dict(self) -> dict[str, Any]:
        """Return the stable JSON-compatible scoped comparison shape."""

        return {
            "left_item": self.left_item,
            "right_item": self.right_item,
            "preferred_item": self.preferred_item,
            "comparison_id": self.comparison_id,
            "assessor_id": self.assessor_id,
            "protocol_id": self.protocol_id,
            "criterion_id": self.criterion_id,
            "time_seconds": self.time_seconds,
            "first_presented_item": self.first_presented_item,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> PairwisePreference:
        """Hydrate one comparison without coercing malformed numeric fields."""

        if not isinstance(value, Mapping):
            raise TypeError("pairwise preference context must be a mapping")
        time_seconds = value.get("time_seconds")
        if isinstance(time_seconds, bool) or (
            time_seconds is not None and not isinstance(time_seconds, (int, float))
        ):
            raise ValueError("time_seconds must be finite and nonnegative")

        def optional_text(field_name: str) -> str | None:
            raw = value.get(field_name)
            if raw is None:
                return None
            if not isinstance(raw, str):
                raise TypeError(f"{field_name} must be text when provided")
            return raw

        left_item = value["left_item"]
        right_item = value["right_item"]
        preferred_item = value.get("preferred_item")
        if not isinstance(left_item, str) or not isinstance(right_item, str):
            raise TypeError("pairwise item identities must be text")
        if preferred_item is not None and not isinstance(preferred_item, str):
            raise TypeError("preferred_item must be text when provided")
        return cls(
            left_item=left_item,
            right_item=right_item,
            preferred_item=preferred_item,
            comparison_id=optional_text("comparison_id"),
            assessor_id=optional_text("assessor_id"),
            protocol_id=optional_text("protocol_id"),
            criterion_id=optional_text("criterion_id"),
            time_seconds=(float(time_seconds) if time_seconds is not None else None),
            first_presented_item=optional_text("first_presented_item"),
        )


@dataclass(frozen=True, slots=True)
class PreferenceFitRequest:
    training: tuple[PairwisePreference, ...]
    heldout: tuple[PairwisePreference, ...] = ()
    minimum_comparisons: int = 10
    minimum_heldout_comparisons: int = 5
    declared_baseline_accuracy: float | None = None
    regularization: float = 0.1
    learning_rate: float = 0.3
    maximum_iterations: int = 2000
    criterion_id: str | None = None
    bootstrap_replicates: int = 0
    bootstrap_seed: int = 0
    require_scoped_validation: bool = False

    def __post_init__(self) -> None:
        if self.minimum_comparisons < 1 or self.minimum_heldout_comparisons < 1:
            raise ValueError("comparison gates must be positive integers")
        if self.maximum_iterations < 1:
            raise ValueError("maximum_iterations must be positive")
        if (
            isinstance(self.bootstrap_replicates, bool)
            or not isinstance(self.bootstrap_replicates, int)
            or self.bootstrap_replicates < 0
        ):
            raise ValueError("bootstrap_replicates must be a nonnegative integer")
        if isinstance(self.bootstrap_seed, bool) or not isinstance(
            self.bootstrap_seed, int
        ):
            raise ValueError("bootstrap_seed must be an integer")
        if not isinstance(self.require_scoped_validation, bool):
            raise TypeError("require_scoped_validation must be boolean")
        if not isfinite(self.regularization) or self.regularization < 0:
            raise ValueError("regularization must be finite and nonnegative")
        if not isfinite(self.learning_rate) or self.learning_rate <= 0:
            raise ValueError("learning_rate must be finite and greater than zero")
        if self.declared_baseline_accuracy is not None and not (
            0 <= self.declared_baseline_accuracy <= 1
        ):
            raise ValueError("declared baseline accuracy must be from zero to one")
        object.__setattr__(self, "training", tuple(self.training))
        object.__setattr__(self, "heldout", tuple(self.heldout))
        if any(
            not isinstance(comparison, PairwisePreference)
            for comparison in self.training + self.heldout
        ):
            raise TypeError("training and heldout must contain PairwisePreference values")
        if self.criterion_id is not None:
            if not isinstance(self.criterion_id, str):
                raise TypeError("criterion_id must be text when provided")
            criterion = self.criterion_id.strip()
            if not criterion:
                raise ValueError("criterion_id must be nonblank when provided")
            object.__setattr__(self, "criterion_id", criterion)


@dataclass(frozen=True, slots=True)
class PreferenceFitResult:
    """Scoped model evidence; it never grants formula or sensory authority."""

    status: PreferenceFitStatus
    validated: bool
    utilities: dict[str, float]
    comparison_count: int
    connected: bool
    regularization: float
    heldout_accuracy: float | None
    baseline_accuracy: float | None
    gate_failures: tuple[str, ...]
    validation_notes: tuple[str, ...]
    criterion_id: str | None
    utility_intervals: dict[str, tuple[float, float]]
    tie_rate: float
    assessor_heterogeneity: dict[str, float]
    order_effect: float | None
    next_comparison: tuple[str, str] | None
    bootstrap_replicates: int
    bootstrap_seed: int
    bootstrap_method: str
    evidence: EvidenceDescriptor
    formula_optimization_authority: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    compounding_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)


def fit_preference_model(request: PreferenceFitRequest) -> PreferenceFitResult:
    """Fit utilities only after basic identifiability and sample gates pass."""

    decisive = tuple(item for item in request.training if item.preferred_item is not None)
    tie_rate = (
        sum(item.preferred_item is None for item in request.training)
        / len(request.training)
        if request.training
        else 0.0
    )
    items = sorted(
        {item.left_item for item in decisive} | {item.right_item for item in decisive}
    )
    connected = _is_connected(items, decisive)
    failures: list[str] = list(_criterion_gate_failures(request))
    if len(decisive) < request.minimum_comparisons:
        failures.append(
            f"minimum comparisons not met: {len(decisive)}/{request.minimum_comparisons}"
        )
    if items and not connected:
        failures.append("comparison graph is not connected")
    if len(items) < 2:
        failures.append("at least two compared items are required")

    if failures:
        return PreferenceFitResult(
            status=PreferenceFitStatus.WITHHELD,
            validated=False,
            utilities={},
            comparison_count=len(decisive),
            connected=connected,
            regularization=request.regularization,
            heldout_accuracy=None,
            baseline_accuracy=request.declared_baseline_accuracy,
            gate_failures=tuple(failures),
            validation_notes=(),
            criterion_id=request.criterion_id,
            utility_intervals={},
            tie_rate=tie_rate,
            assessor_heterogeneity={},
            order_effect=None,
            next_comparison=None,
            bootstrap_replicates=request.bootstrap_replicates,
            bootstrap_seed=request.bootstrap_seed,
            bootstrap_method="NOT_RUN",
            evidence=EvidenceDescriptor(
                classification=ScientificClass.UNKNOWN,
                basis="Preference utilities withheld because identifiability or sample gates failed.",
                sources=("engine.preference",),
                limitations=tuple(failures),
            ),
        )

    utilities = _fit_utilities(
        items,
        decisive,
        regularization=request.regularization,
        learning_rate=request.learning_rate,
        maximum_iterations=request.maximum_iterations,
    )
    utility_intervals, bootstrap_method = _bootstrap_intervals(
        items,
        decisive,
        regularization=request.regularization,
        learning_rate=request.learning_rate,
        maximum_iterations=request.maximum_iterations,
        replicates=request.bootstrap_replicates,
        seed=request.bootstrap_seed,
        point_utilities=utilities,
    )
    assessor_heterogeneity = _assessor_heterogeneity(utilities, decisive)
    order_effect = _order_effect(decisive)
    next_comparison = _next_comparison(utilities, utility_intervals)
    validation_notes: list[str] = []
    scoped_validation_notes = _scoped_validation_notes(request)
    validation_notes.extend(scoped_validation_notes)
    heldout_accuracy: float | None = None
    validated = False
    evaluable_heldout = tuple(
        item
        for item in request.heldout
        if item.preferred_item is not None
        and item.left_item in utilities
        and item.right_item in utilities
    )
    if len(evaluable_heldout) < request.minimum_heldout_comparisons:
        validation_notes.append(
            "minimum held-out comparisons not met: "
            f"{len(evaluable_heldout)}/{request.minimum_heldout_comparisons}"
        )
    elif request.declared_baseline_accuracy is None:
        validation_notes.append("no declared held-out baseline accuracy")
    else:
        heldout_accuracy = _accuracy(utilities, evaluable_heldout)
        if (
            heldout_accuracy > request.declared_baseline_accuracy
            and not scoped_validation_notes
        ):
            validated = True
        elif heldout_accuracy <= request.declared_baseline_accuracy:
            validation_notes.append("model did not beat the declared held-out baseline")

    status = (
        PreferenceFitStatus.VALIDATED if validated else PreferenceFitStatus.DIAGNOSTIC
    )
    classification = (
        ScientificClass.EMPIRICALLY_CALIBRATED
        if validated
        else ScientificClass.UNKNOWN
    )
    return PreferenceFitResult(
        status=status,
        validated=validated,
        utilities={name: round(value, 12) for name, value in utilities.items()},
        comparison_count=len(decisive),
        connected=True,
        regularization=request.regularization,
        heldout_accuracy=(
            round(heldout_accuracy, 12) if heldout_accuracy is not None else None
        ),
        baseline_accuracy=request.declared_baseline_accuracy,
        gate_failures=(),
        validation_notes=tuple(validation_notes),
        criterion_id=request.criterion_id,
        utility_intervals=utility_intervals,
        tie_rate=tie_rate,
        assessor_heterogeneity=assessor_heterogeneity,
        order_effect=order_effect,
        next_comparison=next_comparison,
        bootstrap_replicates=request.bootstrap_replicates,
        bootstrap_seed=request.bootstrap_seed,
        bootstrap_method=bootstrap_method,
        evidence=EvidenceDescriptor(
            classification=classification,
            basis=(
                "L2-regularized Bradley-Terry paired-comparison utilities; "
                + (
                    "validated on held-out comparisons against the declared baseline."
                    if validated
                    else "diagnostic only until held-out baseline validation passes."
                )
            ),
            sources=(
                "https://doi.org/10.1093/biomet/39.3-4.324",
                "engine.preference",
            ),
            assumptions=("Pairwise choices are conditionally independent observations.",),
            limitations=(
                "Utilities are relative to this connected item set and protocol.",
                "Order, context, assessor, and tie effects are not modeled.",
            ),
        ),
    )


def _fit_utilities(
    items: list[str],
    comparisons: tuple[PairwisePreference, ...],
    *,
    regularization: float,
    learning_rate: float,
    maximum_iterations: int,
) -> dict[str, float]:
    utilities = {item: 0.0 for item in items}
    scale = max(1, len(comparisons))
    for iteration in range(maximum_iterations):
        gradient = {item: -regularization * utilities[item] for item in items}
        for comparison in comparisons:
            left = comparison.left_item
            right = comparison.right_item
            probability_left = _sigmoid(utilities[left] - utilities[right])
            outcome_left = 1.0 if comparison.preferred_item == left else 0.0
            residual = outcome_left - probability_left
            gradient[left] += residual
            gradient[right] -= residual
        step_scale = learning_rate / (scale * (1.0 + iteration / 200.0) ** 0.5)
        max_step = 0.0
        for item in items:
            step = step_scale * gradient[item]
            utilities[item] += step
            max_step = max(max_step, abs(step))
        mean = sum(utilities.values()) / len(utilities)
        utilities = {item: value - mean for item, value in utilities.items()}
        if max_step < 1e-10:
            break
    return utilities


def _criterion_gate_failures(request: PreferenceFitRequest) -> tuple[str, ...]:
    declared = {
        comparison.criterion_id
        for comparison in request.training
        if comparison.criterion_id is not None
    }
    if request.criterion_id is not None:
        mismatched = declared.difference({request.criterion_id})
        if mismatched:
            return (
                "training comparisons mix the requested criterion with: "
                + ", ".join(sorted(mismatched)),
            )
    elif len(declared) > 1:
        return ("training comparisons contain multiple preference criteria",)
    return ()


def _scoped_validation_notes(request: PreferenceFitRequest) -> tuple[str, ...]:
    if not request.require_scoped_validation:
        return ()
    records = request.training + request.heldout
    required = (
        "comparison_id",
        "assessor_id",
        "protocol_id",
        "criterion_id",
        "time_seconds",
        "first_presented_item",
    )
    notes: list[str] = []
    if any(
        any(getattr(comparison, field_name) is None for field_name in required)
        for comparison in records
    ):
        notes.append("scoped metadata is incomplete for validation")
        return tuple(notes)
    comparison_ids = tuple(comparison.comparison_id for comparison in records)
    if len(comparison_ids) != len(set(comparison_ids)):
        notes.append("scoped comparison IDs are not unique")
    protocols = {comparison.protocol_id for comparison in records}
    if len(protocols) != 1:
        notes.append("scoped comparisons span multiple protocols")
    criteria = {comparison.criterion_id for comparison in records}
    if len(criteria) != 1 or (
        request.criterion_id is not None and criteria != {request.criterion_id}
    ):
        notes.append("scoped comparisons do not isolate one requested criterion")
    assessors = {
        comparison.assessor_id
        for comparison in request.training
        if comparison.preferred_item is not None
    }
    if len(assessors) < 2:
        notes.append("scoped validation requires at least two assessors")
    pair_orders: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: defaultdict(int)
    )
    for comparison in request.training:
        if comparison.preferred_item is None:
            continue
        pair = tuple(sorted((comparison.left_item, comparison.right_item)))
        first = comparison.first_presented_item
        if first is not None:
            pair_orders[(pair[0], pair[1])][first] += 1
    if any(
        set(counts) != set(pair)
        or max(counts.values()) - min(counts.values()) > 1
        for pair, counts in pair_orders.items()
    ):
        notes.append("presentation order is not balanced within each item pair")
    return tuple(notes)


def _is_connected(
    items: list[str], comparisons: tuple[PairwisePreference, ...]
) -> bool:
    if not items:
        return False
    adjacency: dict[str, set[str]] = {item: set() for item in items}
    for comparison in comparisons:
        adjacency[comparison.left_item].add(comparison.right_item)
        adjacency[comparison.right_item].add(comparison.left_item)
    seen = {items[0]}
    frontier = [items[0]]
    while frontier:
        current = frontier.pop()
        for neighbor in adjacency[current].difference(seen):
            seen.add(neighbor)
            frontier.append(neighbor)
    return len(seen) == len(items)


def _accuracy(
    utilities: dict[str, float], comparisons: tuple[PairwisePreference, ...]
) -> float:
    correct = 0.0
    for comparison in comparisons:
        left = utilities[comparison.left_item]
        right = utilities[comparison.right_item]
        if left == right:
            correct += 0.5
        elif (left > right and comparison.preferred_item == comparison.left_item) or (
            right > left and comparison.preferred_item == comparison.right_item
        ):
            correct += 1.0
    return correct / len(comparisons)


def _sigmoid(value: float) -> float:
    if value >= 0:
        inverse = exp(-value)
        return 1.0 / (1.0 + inverse)
    positive = exp(value)
    return positive / (1.0 + positive)


def _bootstrap_intervals(
    items: list[str],
    comparisons: tuple[PairwisePreference, ...],
    *,
    regularization: float,
    learning_rate: float,
    maximum_iterations: int,
    replicates: int,
    seed: int,
    point_utilities: dict[str, float],
) -> tuple[dict[str, tuple[float, float]], str]:
    if replicates == 0:
        return (
            {
                item: (
                    round(point_utilities[item], 12),
                    round(point_utilities[item], 12),
                )
                for item in items
            },
            "NOT_RUN",
        )
    rng = Random(seed)
    by_assessor: dict[str, list[PairwisePreference]] = defaultdict(list)
    all_scoped = bool(comparisons) and all(
        comparison.assessor_id is not None for comparison in comparisons
    )
    if all_scoped:
        for comparison in comparisons:
            by_assessor[comparison.assessor_id or ""].append(comparison)
        assessor_ids = sorted(by_assessor)
        method = "ASSESSOR_CLUSTER"
    else:
        assessor_ids = []
        method = "COMPARISON"
    samples: dict[str, list[float]] = {item: [] for item in items}
    for _ in range(replicates):
        if assessor_ids:
            selected = rng.choices(assessor_ids, k=len(assessor_ids))
            resampled = tuple(
                comparison
                for assessor_id in selected
                for comparison in by_assessor[assessor_id]
            )
        else:
            resampled = tuple(rng.choices(comparisons, k=len(comparisons)))
        fitted = _fit_utilities(
            items,
            resampled,
            regularization=regularization,
            learning_rate=learning_rate,
            maximum_iterations=maximum_iterations,
        )
        for item in items:
            samples[item].append(fitted[item])
    return (
        {
            item: (
                round(_percentile(values, 0.025), 12),
                round(_percentile(values, 0.975), 12),
            )
            for item, values in samples.items()
        },
        method,
    )


def _percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def _assessor_heterogeneity(
    utilities: dict[str, float],
    comparisons: tuple[PairwisePreference, ...],
) -> dict[str, float]:
    grouped: dict[str, list[PairwisePreference]] = defaultdict(list)
    for comparison in comparisons:
        if comparison.assessor_id is not None:
            grouped[comparison.assessor_id].append(comparison)
    return {
        assessor_id: round(1.0 - _accuracy(utilities, tuple(values)), 12)
        for assessor_id, values in sorted(grouped.items())
    }


def _order_effect(
    comparisons: tuple[PairwisePreference, ...],
) -> float | None:
    ordered = tuple(
        comparison
        for comparison in comparisons
        if comparison.first_presented_item is not None
    )
    if not ordered:
        return None
    first_wins = sum(
        comparison.preferred_item == comparison.first_presented_item
        for comparison in ordered
    )
    return round(first_wins / len(ordered) - 0.5, 12)


def _next_comparison(
    utilities: dict[str, float],
    intervals: dict[str, tuple[float, float]],
) -> tuple[str, str] | None:
    if len(utilities) < 2:
        return None
    pairs = tuple(combinations(sorted(utilities), 2))
    return min(
        pairs,
        key=lambda pair: (
            abs(utilities[pair[0]] - utilities[pair[1]]),
            -(
                intervals[pair[0]][1]
                - intervals[pair[0]][0]
                + intervals[pair[1]][1]
                - intervals[pair[1]][0]
            ),
            pair,
        ),
    )


__all__ = [
    "PairwisePreference",
    "PreferenceFitRequest",
    "PreferenceFitResult",
    "PreferenceFitStatus",
    "fit_preference_model",
]
