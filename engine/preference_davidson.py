"""Deterministic Davidson paired-comparison fitting with explicit ties."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, isfinite, log
from typing import ClassVar

from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.preference import PairwisePreference, PreferenceOutcome


@dataclass(frozen=True, slots=True)
class DavidsonFitConfig:
    regularization: float = 0.1
    maximum_iterations: int = 200
    gradient_tolerance: float = 1e-8
    minimum_step_scale: float = 2.0**-30
    maximum_absolute_parameter: float = 30.0

    def __post_init__(self) -> None:
        if not isfinite(self.regularization) or self.regularization < 0:
            raise ValueError("regularization must be finite and nonnegative")
        if isinstance(self.maximum_iterations, bool) or self.maximum_iterations < 1:
            raise ValueError("maximum_iterations must be a positive integer")
        for name in (
            "gradient_tolerance",
            "minimum_step_scale",
            "maximum_absolute_parameter",
        ):
            value = getattr(self, name)
            if not isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")


@dataclass(frozen=True, slots=True)
class DavidsonFitReceipt:
    SCHEMA_VERSION: ClassVar[str] = "davidson_fit_receipt_v1"
    utilities: dict[str, float]
    tie_parameter: float
    objective_value: float
    iterations: int
    gradient_norm: float
    converged: bool
    convergence_code: str
    parameter_order: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.utilities:
            raise ValueError("utilities must not be empty")
        if tuple(self.utilities) != self.parameter_order[:-1]:
            raise ValueError("utility order must match parameter_order")
        if self.parameter_order[-1:] != ("LOG_TIE_PARAMETER",):
            raise ValueError("parameter_order must end with LOG_TIE_PARAMETER")
        for value in self.utilities.values():
            if not isfinite(value):
                raise ValueError("utilities must be finite")
        for name in ("tie_parameter", "objective_value", "gradient_norm"):
            if not isfinite(getattr(self, name)) or getattr(self, name) < 0:
                raise ValueError(f"{name} must be finite and nonnegative")
        if isinstance(self.iterations, bool) or self.iterations < 0:
            raise ValueError("iterations must be a nonnegative integer")
        if not isinstance(self.converged, bool):
            raise TypeError("converged must be boolean")
        if not self.convergence_code.strip():
            raise ValueError("convergence_code must be nonblank")

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "utilities": self.utilities,
            "tie_parameter": self.tie_parameter,
            "objective_value": self.objective_value,
            "iterations": self.iterations,
            "gradient_norm": self.gradient_norm,
            "converged": self.converged,
            "convergence_code": self.convergence_code,
            "parameter_order": list(self.parameter_order),
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @property
    def receipt_sha256(self) -> str:
        return sha256_hex(self.canonical_bytes())


_LIKELIHOOD_OUTCOMES = {
    PreferenceOutcome.LEFT,
    PreferenceOutcome.RIGHT,
    PreferenceOutcome.NO_PREFERENCE,
}


def _eligible(
    comparisons: tuple[PairwisePreference, ...],
) -> tuple[PairwisePreference, ...]:
    return tuple(row for row in comparisons if row.outcome in _LIKELIHOOD_OUTCOMES)


def _connected(items: tuple[str, ...], rows: tuple[PairwisePreference, ...]) -> bool:
    adjacency = {item: set() for item in items}
    for row in rows:
        adjacency[row.left_item].add(row.right_item)
        adjacency[row.right_item].add(row.left_item)
    seen = {items[0]}
    frontier = [items[0]]
    while frontier:
        current = frontier.pop()
        for neighbor in adjacency[current].difference(seen):
            seen.add(neighbor)
            frontier.append(neighbor)
    return len(seen) == len(items)


def _full_parameters(theta: list[float], item_count: int) -> list[float]:
    utilities = theta[: item_count - 1]
    utilities.append(-sum(utilities))
    return utilities + [theta[-1]]


def _transformation(item_count: int) -> list[list[float]]:
    free_count = item_count
    matrix = [[0.0] * free_count for _ in range(item_count + 1)]
    for index in range(item_count - 1):
        matrix[index][index] = 1.0
        matrix[item_count - 1][index] = -1.0
    matrix[item_count][item_count - 1] = 1.0
    return matrix


def _evaluate(
    theta: list[float],
    *,
    items: tuple[str, ...],
    rows: tuple[PairwisePreference, ...],
    regularization: float,
) -> tuple[float, list[float], list[list[float]], list[float]]:
    item_count = len(items)
    index_by_item = {item: index for index, item in enumerate(items)}
    full = _full_parameters(theta, item_count)
    utilities = full[:-1]
    log_tie = full[-1]
    parameter_count = item_count + 1
    objective = 0.0
    gradient = [0.0] * parameter_count
    hessian = [[0.0] * parameter_count for _ in range(parameter_count)]

    for row in rows:
        left = index_by_item[row.left_item]
        right = index_by_item[row.right_item]
        features = [[0.0] * parameter_count for _ in range(3)]
        features[0][left] = 1.0
        features[1][right] = 1.0
        features[2][left] = 0.5
        features[2][right] = 0.5
        features[2][-1] = 1.0
        scores = (
            utilities[left],
            utilities[right],
            log_tie + 0.5 * (utilities[left] + utilities[right]),
        )
        maximum = max(scores)
        weights = tuple(exp(score - maximum) for score in scores)
        total = sum(weights)
        probabilities = tuple(weight / total for weight in weights)
        outcome_index = (
            0
            if row.outcome is PreferenceOutcome.LEFT
            else 1
            if row.outcome is PreferenceOutcome.RIGHT
            else 2
        )
        objective += maximum + log(total) - scores[outcome_index]
        expected = [
            sum(probabilities[k] * features[k][j] for k in range(3))
            for j in range(parameter_count)
        ]
        for j in range(parameter_count):
            gradient[j] += expected[j] - features[outcome_index][j]
        for j in range(parameter_count):
            for k in range(parameter_count):
                hessian[j][k] += sum(
                    probabilities[outcome]
                    * (features[outcome][j] - expected[j])
                    * (features[outcome][k] - expected[k])
                    for outcome in range(3)
                )

    if regularization:
        objective += 0.5 * regularization * sum(value * value for value in full)
        for index, value in enumerate(full):
            gradient[index] += regularization * value
            hessian[index][index] += regularization

    transform = _transformation(item_count)
    free_count = item_count
    projected_gradient = [
        sum(transform[row][column] * gradient[row] for row in range(parameter_count))
        for column in range(free_count)
    ]
    projected_hessian = [
        [
            sum(
                transform[row][left]
                * hessian[row][column]
                * transform[column][right]
                for row in range(parameter_count)
                for column in range(parameter_count)
            )
            for right in range(free_count)
        ]
        for left in range(free_count)
    ]
    return objective, projected_gradient, projected_hessian, full


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float] | None:
    size = len(vector)
    augmented = [row[:] + [value] for row, value in zip(matrix, vector)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-14:
            return None
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        pivot_value = augmented[column][column]
        for index in range(column, size + 1):
            augmented[column][index] /= pivot_value
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            for index in range(column, size + 1):
                augmented[row][index] -= factor * augmented[column][index]
    return [augmented[row][-1] for row in range(size)]


def _boundary_receipt(items: tuple[str, ...]) -> DavidsonFitReceipt:
    return DavidsonFitReceipt(
        utilities={item: 0.0 for item in items},
        tie_parameter=0.0,
        objective_value=0.0,
        iterations=0,
        gradient_norm=0.0,
        converged=False,
        convergence_code="BOUNDARY_UNIDENTIFIED",
        parameter_order=items + ("LOG_TIE_PARAMETER",),
    )


def fit_davidson(
    *,
    items: tuple[str, ...],
    comparisons: tuple[PairwisePreference, ...],
    config: DavidsonFitConfig,
) -> DavidsonFitReceipt:
    """Fit centered item utilities and a positive tie parameter."""

    if not isinstance(config, DavidsonFitConfig):
        raise TypeError("config must be a DavidsonFitConfig")
    normalized_items = tuple(item.strip() for item in items)
    if (
        len(normalized_items) < 2
        or any(not item for item in normalized_items)
        or len(normalized_items) != len(set(normalized_items))
    ):
        raise ValueError("items must contain at least two unique nonblank names")
    rows = _eligible(tuple(comparisons))
    if len(rows) < 2:
        raise ValueError("at least two likelihood rows are required")
    item_set = set(normalized_items)
    if any(
        row.left_item not in item_set or row.right_item not in item_set for row in rows
    ):
        raise ValueError("comparison item is absent from items")
    if not _connected(normalized_items, rows):
        raise ValueError("comparison graph must be connected")
    observed_outcomes = {row.outcome for row in rows}
    if config.regularization == 0 and observed_outcomes != _LIKELIHOOD_OUTCOMES:
        return _boundary_receipt(normalized_items)

    theta = [0.0] * len(normalized_items)
    convergence_code = "MAXIMUM_ITERATIONS"
    converged = False
    iterations = 0
    for iteration in range(1, config.maximum_iterations + 1):
        objective, gradient, hessian, _ = _evaluate(
            theta,
            items=normalized_items,
            rows=rows,
            regularization=config.regularization,
        )
        gradient_norm = max(abs(value) for value in gradient)
        iterations = iteration - 1
        if gradient_norm <= config.gradient_tolerance:
            converged = True
            convergence_code = "GRADIENT_TOLERANCE"
            break
        direction = _solve(hessian, gradient)
        if direction is None or any(not isfinite(value) for value in direction):
            convergence_code = "HESSIAN_SINGULAR"
            break
        step_scale = 1.0
        accepted = False
        while step_scale >= config.minimum_step_scale:
            candidate = [
                value - step_scale * step
                for value, step in zip(theta, direction)
            ]
            candidate_objective, _, _, _ = _evaluate(
                candidate,
                items=normalized_items,
                rows=rows,
                regularization=config.regularization,
            )
            if isfinite(candidate_objective) and candidate_objective < objective:
                theta = candidate
                accepted = True
                iterations = iteration
                break
            step_scale *= 0.5
        if not accepted:
            convergence_code = "NO_DESCENT_STEP"
            break

    objective, gradient, _, full = _evaluate(
        theta,
        items=normalized_items,
        rows=rows,
        regularization=config.regularization,
    )
    gradient_norm = max(abs(value) for value in gradient)
    if max(abs(value) for value in full) > config.maximum_absolute_parameter:
        converged = False
        convergence_code = "BOUNDARY_UNIDENTIFIED"
    utilities = {
        item: (0.0 if abs(value) < 1e-15 else value)
        for item, value in zip(normalized_items, full[:-1])
    }
    return DavidsonFitReceipt(
        utilities=utilities,
        tie_parameter=exp(full[-1]),
        objective_value=objective,
        iterations=iterations,
        gradient_norm=gradient_norm,
        converged=converged,
        convergence_code=convergence_code,
        parameter_order=normalized_items + ("LOG_TIE_PARAMETER",),
    )


def davidson_pair_probabilities(
    receipt: DavidsonFitReceipt,
    left_item: str,
    right_item: str,
) -> tuple[float, float, float]:
    """Return left, right, and tie probabilities for one fitted pair."""

    left = receipt.utilities[left_item]
    right = receipt.utilities[right_item]
    tie_score = log(receipt.tie_parameter) + 0.5 * (left + right)
    maximum = max(left, right, tie_score)
    weights = (
        exp(left - maximum),
        exp(right - maximum),
        exp(tie_score - maximum),
    )
    total = sum(weights)
    return tuple(value / total for value in weights)


__all__ = [
    "DavidsonFitConfig",
    "DavidsonFitReceipt",
    "davidson_pair_probabilities",
    "fit_davidson",
]
