"""Conservatively gated Bradley-Terry preference diagnostics."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from itertools import combinations
from math import exp, isfinite
from random import Random
from typing import Any, Mapping, cast

from engine.scientific_contract import EvidenceDescriptor, ScientificClass


class PreferenceFitStatus(str, Enum):
    WITHHELD = "withheld"
    DIAGNOSTIC = "diagnostic"
    VALIDATED = "validated"


class PreferenceOutcome(str, Enum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    NO_PREFERENCE = "NO_PREFERENCE"
    NO_PERCEPTIBLE_DIFFERENCE = "NO_PERCEPTIBLE_DIFFERENCE"
    CANNOT_JUDGE = "CANNOT_JUDGE"
    PROTOCOL_ABORT = "PROTOCOL_ABORT"


class PreferenceModelFamily(str, Enum):
    DAVIDSON_V1 = "DAVIDSON_V1"
    BRADLEY_TERRY_LEGACY = "BRADLEY_TERRY_LEGACY"


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
    outcome: PreferenceOutcome | str | None = None
    session_id: str | None = None
    matrix_id: str | None = None
    time_window_id: str | None = None
    previous_presented_item: str | None = None
    position_in_session: int | None = None
    protocol_sha256: str | None = None
    sample_sha256: str | None = None
    partition: str | None = None
    legacy_outcome_semantics: bool = field(init=False)

    def __post_init__(self) -> None:
        left = self.left_item.strip()
        right = self.right_item.strip()
        preferred = self.preferred_item.strip() if self.preferred_item else None
        if not left or not right or left == right:
            raise ValueError("pairwise comparison requires two different named items")
        if preferred is not None and preferred not in {left, right}:
            raise ValueError("preferred item must be the left item, right item, or None for a tie")
        object.__setattr__(self, "left_item", left)
        object.__setattr__(self, "right_item", right)
        legacy_outcome = self.outcome is None
        if self.outcome is None:
            outcome = (
                PreferenceOutcome.LEFT
                if preferred == left
                else PreferenceOutcome.RIGHT
                if preferred == right
                else PreferenceOutcome.NO_PREFERENCE
            )
        else:
            outcome = PreferenceOutcome(self.outcome)
            if outcome is PreferenceOutcome.LEFT:
                if preferred not in {None, left}:
                    raise ValueError("preferred_item contradicts explicit outcome")
                preferred = left
            elif outcome is PreferenceOutcome.RIGHT:
                if preferred not in {None, right}:
                    raise ValueError("preferred_item contradicts explicit outcome")
                preferred = right
            elif preferred is not None:
                raise ValueError("preferred_item contradicts explicit outcome")
        object.__setattr__(self, "preferred_item", preferred)
        object.__setattr__(self, "outcome", outcome)
        object.__setattr__(self, "legacy_outcome_semantics", legacy_outcome)
        for name in (
            "comparison_id",
            "assessor_id",
            "protocol_id",
            "criterion_id",
            "session_id",
            "matrix_id",
            "time_window_id",
            "previous_presented_item",
            "partition",
        ):
            value = getattr(self, name)
            normalized = value.strip() if value is not None else None
            if value is not None and not normalized:
                raise ValueError(f"{name} must be nonblank when provided")
            object.__setattr__(self, name, normalized)
        if self.time_seconds is not None and (
            not isfinite(self.time_seconds) or self.time_seconds < 0
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
        if self.position_in_session is not None and (
            isinstance(self.position_in_session, bool)
            or not isinstance(self.position_in_session, int)
            or self.position_in_session < 1
        ):
            raise ValueError("position_in_session must be a positive integer")
        for name in ("protocol_sha256", "sample_sha256"):
            value = getattr(self, name)
            if value is None:
                continue
            digest = value.strip().lower()
            if len(digest) != 64 or any(
                character not in "0123456789abcdef" for character in digest
            ):
                raise ValueError(f"{name} must be a SHA-256 hex digest")
            object.__setattr__(self, name, digest)

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "left_item": self.left_item,
            "right_item": self.right_item,
            "preferred_item": self.preferred_item,
            "comparison_id": self.comparison_id,
            "assessor_id": self.assessor_id,
            "protocol_id": self.protocol_id,
            "criterion_id": self.criterion_id,
            "time_seconds": self.time_seconds,
            "first_presented_item": self.first_presented_item,
            "session_id": self.session_id,
            "matrix_id": self.matrix_id,
            "time_window_id": self.time_window_id,
            "previous_presented_item": self.previous_presented_item,
            "position_in_session": self.position_in_session,
            "protocol_sha256": self.protocol_sha256,
            "sample_sha256": self.sample_sha256,
            "partition": self.partition,
        }
        if not self.legacy_outcome_semantics:
            payload["outcome"] = cast(PreferenceOutcome, self.outcome).value
        return payload

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> PairwisePreference:
        if not isinstance(value, Mapping):
            raise TypeError("pairwise preference context must be a mapping")
        return cls(
            left_item=str(value["left_item"]),
            right_item=str(value["right_item"]),
            preferred_item=(
                str(value["preferred_item"])
                if value.get("preferred_item") is not None
                else None
            ),
            comparison_id=(
                str(value["comparison_id"])
                if value.get("comparison_id") is not None
                else None
            ),
            assessor_id=(
                str(value["assessor_id"])
                if value.get("assessor_id") is not None
                else None
            ),
            protocol_id=(
                str(value["protocol_id"])
                if value.get("protocol_id") is not None
                else None
            ),
            criterion_id=(
                str(value["criterion_id"])
                if value.get("criterion_id") is not None
                else None
            ),
            time_seconds=(
                float(value["time_seconds"])
                if value.get("time_seconds") is not None
                else None
            ),
            first_presented_item=(
                str(value["first_presented_item"])
                if value.get("first_presented_item") is not None
                else None
            ),
            outcome=(
                str(value["outcome"]) if value.get("outcome") is not None else None
            ),
            session_id=(
                str(value["session_id"])
                if value.get("session_id") is not None
                else None
            ),
            matrix_id=(
                str(value["matrix_id"])
                if value.get("matrix_id") is not None
                else None
            ),
            time_window_id=(
                str(value["time_window_id"])
                if value.get("time_window_id") is not None
                else None
            ),
            previous_presented_item=(
                str(value["previous_presented_item"])
                if value.get("previous_presented_item") is not None
                else None
            ),
            position_in_session=(
                int(value["position_in_session"])
                if value.get("position_in_session") is not None
                else None
            ),
            protocol_sha256=(
                str(value["protocol_sha256"])
                if value.get("protocol_sha256") is not None
                else None
            ),
            sample_sha256=(
                str(value["sample_sha256"])
                if value.get("sample_sha256") is not None
                else None
            ),
            partition=(
                str(value["partition"])
                if value.get("partition") is not None
                else None
            ),
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
    model_family: PreferenceModelFamily | str = PreferenceModelFamily.DAVIDSON_V1

    def __post_init__(self) -> None:
        if self.minimum_comparisons < 1 or self.minimum_heldout_comparisons < 1:
            raise ValueError("comparison gates must be positive integers")
        if self.maximum_iterations < 1:
            raise ValueError("maximum_iterations must be positive")
        if isinstance(self.bootstrap_replicates, bool) or self.bootstrap_replicates < 0:
            raise ValueError("bootstrap_replicates must be a nonnegative integer")
        if isinstance(self.bootstrap_seed, bool) or not isinstance(self.bootstrap_seed, int):
            raise ValueError("bootstrap_seed must be an integer")
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
        if self.criterion_id is not None:
            criterion = self.criterion_id.strip()
            if not criterion:
                raise ValueError("criterion_id must be nonblank when provided")
            object.__setattr__(self, "criterion_id", criterion)
        object.__setattr__(
            self, "model_family", PreferenceModelFamily(self.model_family)
        )


@dataclass(frozen=True, slots=True)
class PreferenceFitResult:
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
    model_family: PreferenceModelFamily
    tie_parameter: float | None
    converged: bool
    convergence_code: str
    pair_probabilities: dict[str, tuple[float, float, float]]
    cluster_bootstrap_receipt: object | None
    heldout_validation_receipt: object | None
    transitivity_receipt: object | None
    next_pair_receipt: object | None


def _withheld_result(
    *,
    request: PreferenceFitRequest,
    connected: bool,
    comparison_count: int,
    tie_rate: float,
    failures: tuple[str, ...],
) -> PreferenceFitResult:
    return PreferenceFitResult(
        status=PreferenceFitStatus.WITHHELD,
        validated=False,
        utilities={},
        comparison_count=comparison_count,
        connected=connected,
        regularization=request.regularization,
        heldout_accuracy=None,
        baseline_accuracy=request.declared_baseline_accuracy,
        gate_failures=failures,
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
            basis=(
                "Preference utilities withheld because identifiability, sample, "
                "or convergence gates failed."
            ),
            sources=("engine.preference",),
            limitations=failures,
        ),
        model_family=cast(PreferenceModelFamily, request.model_family),
        tie_parameter=None,
        converged=False,
        convergence_code="GATED_BEFORE_FIT",
        pair_probabilities={},
        cluster_bootstrap_receipt=None,
        heldout_validation_receipt=None,
        transitivity_receipt=None,
        next_pair_receipt=None,
    )


def fit_preference_model(request: PreferenceFitRequest) -> PreferenceFitResult:
    """Fit utilities only after basic identifiability and sample gates pass."""

    likelihood_rows = tuple(
        item
        for item in request.training
        if item.outcome
        in {
            PreferenceOutcome.LEFT,
            PreferenceOutcome.RIGHT,
            PreferenceOutcome.NO_PREFERENCE,
        }
    )
    decisive = tuple(
        item
        for item in request.training
        if item.outcome in {PreferenceOutcome.LEFT, PreferenceOutcome.RIGHT}
    )
    fitting_rows = (
        likelihood_rows
        if request.model_family is PreferenceModelFamily.DAVIDSON_V1
        else decisive
    )
    comparison_count = len(decisive)
    tie_rate = (
        sum(item.outcome is PreferenceOutcome.NO_PREFERENCE for item in likelihood_rows)
        / len(likelihood_rows)
        if likelihood_rows
        else 0.0
    )
    items = sorted(
        {item.left_item for item in fitting_rows}
        | {item.right_item for item in fitting_rows}
    )
    connected = _is_connected(items, fitting_rows)
    failures: list[str] = list(_criterion_gate_failures(request))
    if comparison_count < request.minimum_comparisons:
        failures.append(
            f"minimum comparisons not met: {comparison_count}/{request.minimum_comparisons}"
        )
    if items and not connected:
        failures.append("comparison graph is not connected")
    if len(items) < 2:
        failures.append("at least two compared items are required")

    if failures:
        return _withheld_result(
            request=request,
            connected=connected,
            comparison_count=comparison_count,
            tie_rate=tie_rate,
            failures=tuple(failures),
        )

    tie_parameter: float | None = None
    converged = True
    convergence_code = "LEGACY_OPTIMIZER"
    pair_probabilities: dict[str, tuple[float, float, float]] = {}
    if request.model_family is PreferenceModelFamily.DAVIDSON_V1:
        from engine.preference_davidson import (
            DavidsonFitConfig,
            davidson_pair_probabilities,
            fit_davidson,
        )

        try:
            davidson = fit_davidson(
                items=tuple(items),
                comparisons=fitting_rows,
                config=DavidsonFitConfig(
                    regularization=request.regularization,
                    maximum_iterations=request.maximum_iterations,
                ),
            )
        except ValueError as exc:
            failures.append(f"Davidson fit failed: {exc}")
            return _withheld_result(
                request=request,
                connected=connected,
                comparison_count=comparison_count,
                tie_rate=tie_rate,
                failures=tuple(failures),
            )
        if not davidson.converged:
            failures.append(
                f"Davidson fit did not converge: {davidson.convergence_code}"
            )
            return _withheld_result(
                request=request,
                connected=connected,
                comparison_count=comparison_count,
                tie_rate=tie_rate,
                failures=tuple(failures),
            )
        utilities = davidson.utilities
        tie_parameter = davidson.tie_parameter
        converged = davidson.converged
        convergence_code = davidson.convergence_code
        pair_probabilities = {
            f"{left}|{right}": davidson_pair_probabilities(davidson, left, right)
            for left, right in combinations(items, 2)
        }
    else:
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
        comparison_count=comparison_count,
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
                (
                    "L2-regularized Davidson paired-comparison utilities with ties; "
                    if request.model_family is PreferenceModelFamily.DAVIDSON_V1
                    else "L2-regularized Bradley-Terry paired-comparison utilities; "
                )
                + (
                    "validated on held-out comparisons against the declared baseline."
                    if validated
                    else "diagnostic only until held-out baseline validation passes."
                )
            ),
            sources=(
                (
                    "https://doi.org/10.1080/01621459.1970.10481082"
                    if request.model_family is PreferenceModelFamily.DAVIDSON_V1
                    else "https://doi.org/10.1093/biomet/39.3-4.324"
                ),
                "engine.preference",
            ),
            assumptions=("Pairwise choices are conditionally independent observations.",),
            limitations=(
                "Utilities are relative to this connected item set and protocol.",
                "Order, context, and assessor effects are not modeled in this fit.",
            ),
        ),
        model_family=cast(PreferenceModelFamily, request.model_family),
        tie_parameter=tie_parameter,
        converged=converged,
        convergence_code=convergence_code,
        pair_probabilities=pair_probabilities,
        cluster_bootstrap_receipt=None,
        heldout_validation_receipt=None,
        transitivity_receipt=None,
        next_pair_receipt=None,
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
    failures: list[str] = []
    if (
        request.require_scoped_validation
        and request.model_family is PreferenceModelFamily.BRADLEY_TERRY_LEGACY
    ):
        failures.append("legacy model family is prohibited for scoped validation")
    if request.criterion_id is not None:
        mismatched = declared.difference({request.criterion_id})
        if mismatched:
            failures.append(
                "training comparisons mix the requested criterion with: "
                + ", ".join(sorted(mismatched))
            )
    elif len(declared) > 1:
        failures.append("training comparisons contain multiple preference criteria")
    return tuple(failures)


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
        left_item, right_item = sorted(
            (comparison.left_item, comparison.right_item)
        )
        pair = (left_item, right_item)
        first = comparison.first_presented_item
        if first is not None:
            pair_orders[pair][first] += 1
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
                item: (round(point_utilities[item], 12), round(point_utilities[item], 12))
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
        and comparison.outcome
        in {PreferenceOutcome.LEFT, PreferenceOutcome.RIGHT}
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
    "PreferenceModelFamily",
    "PreferenceOutcome",
    "fit_preference_model",
]
