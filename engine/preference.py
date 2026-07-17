"""Conservatively gated Bradley-Terry preference diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import exp, isfinite

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
        object.__setattr__(self, "preferred_item", preferred)


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

    def __post_init__(self) -> None:
        if self.minimum_comparisons < 1 or self.minimum_heldout_comparisons < 1:
            raise ValueError("comparison gates must be positive integers")
        if self.maximum_iterations < 1:
            raise ValueError("maximum_iterations must be positive")
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
    evidence: EvidenceDescriptor


def fit_preference_model(request: PreferenceFitRequest) -> PreferenceFitResult:
    """Fit utilities only after basic identifiability and sample gates pass."""

    decisive = tuple(item for item in request.training if item.preferred_item is not None)
    items = sorted(
        {item.left_item for item in decisive} | {item.right_item for item in decisive}
    )
    connected = _is_connected(items, decisive)
    failures: list[str] = []
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
    validation_notes: list[str] = []
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
        if heldout_accuracy > request.declared_baseline_accuracy:
            validated = True
        else:
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


__all__ = [
    "PairwisePreference",
    "PreferenceFitRequest",
    "PreferenceFitResult",
    "PreferenceFitStatus",
    "fit_preference_model",
]
