"""Equal-budget conservative selection over a finite feasible candidate pool."""

from __future__ import annotations

import math
import random
from dataclasses import asdict, dataclass
from decimal import Decimal
from statistics import median
from typing import Any, Literal, Mapping, Sequence

from engine.optimizer.gate_aware import PROHIBITED_SELECTION_FEATURES

from .contracts import FALSE_ACTION_AUTHORITY, decimal_text


def _normalized_feature(value: str) -> str:
    return value.strip().upper().replace("-", "_").replace(" ", "_")


@dataclass(frozen=True, slots=True)
class OfflineCandidateV1:
    candidate_id: str
    variables: Mapping[str, float]
    endpoint_value: float
    prediction_interval: tuple[float, float]
    coverage_decimal: str
    applicability_state: Literal["APPLICABLE", "PARTIAL", "OUT_OF_DOMAIN", "UNAVAILABLE"]
    feature_lineage: tuple[str, ...]
    model_signs: Mapping[str, int]

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_id, str) or not self.candidate_id.strip():
            raise ValueError("candidate_id must be non-empty text")
        object.__setattr__(self, "candidate_id", self.candidate_id.strip())
        variables: dict[str, float] = {}
        for name, value in self.variables.items():
            if (
                not isinstance(name, str)
                or not name.strip()
                or isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
            ):
                raise ValueError("candidate variables require named finite numeric values")
            variables[name.strip()] = float(value)
        if not variables:
            raise ValueError("candidate variables must not be empty")
        object.__setattr__(self, "variables", variables)
        if (
            isinstance(self.endpoint_value, bool)
            or not isinstance(self.endpoint_value, (int, float))
            or not math.isfinite(float(self.endpoint_value))
        ):
            raise ValueError("endpoint_value must be finite")
        object.__setattr__(self, "endpoint_value", float(self.endpoint_value))
        if len(self.prediction_interval) != 2:
            raise ValueError("prediction_interval must contain lower and upper bounds")
        low, high = (float(self.prediction_interval[0]), float(self.prediction_interval[1]))
        if not all(math.isfinite(value) for value in (low, high)) or low > high:
            raise ValueError("prediction_interval must be finite and ordered")
        object.__setattr__(self, "prediction_interval", (low, high))
        coverage = decimal_text(self.coverage_decimal, "coverage_decimal", nonnegative=True)
        if Decimal(coverage) > 1:
            raise ValueError("coverage cannot exceed one")
        object.__setattr__(self, "coverage_decimal", coverage)
        lineage = tuple(str(value).strip() for value in self.feature_lineage)
        if not lineage or any(not value for value in lineage):
            raise ValueError("feature lineage must be explicit")
        prohibited = {_normalized_feature(value) for value in lineage} & PROHIBITED_SELECTION_FEATURES
        if prohibited:
            raise ValueError("prohibited selection feature: " + ",".join(sorted(prohibited)))
        object.__setattr__(self, "feature_lineage", lineage)
        signs: dict[str, int] = {}
        for model, sign in self.model_signs.items():
            if isinstance(sign, bool) or sign not in {-1, 0, 1}:
                raise ValueError("model signs must be -1, 0, or 1")
            signs[str(model)] = int(sign)
        object.__setattr__(self, "model_signs", signs)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _distance(
    left: OfflineCandidateV1,
    right: OfflineCandidateV1,
    bounds: Mapping[str, tuple[float, float]],
) -> float:
    squared = 0.0
    for name in sorted(bounds):
        low, high = bounds[name]
        scale = high - low
        if scale <= 0:
            continue
        squared += ((left.variables[name] - right.variables[name]) / scale) ** 2
    return math.sqrt(squared)


def _cholesky(matrix: list[list[float]]) -> list[list[float]]:
    size = len(matrix)
    lower = [[0.0] * size for _ in range(size)]
    for row in range(size):
        for column in range(row + 1):
            value = matrix[row][column] - math.fsum(
                lower[row][index] * lower[column][index] for index in range(column)
            )
            if row == column:
                if value <= 0:
                    raise ArithmeticError("non-positive GP covariance")
                lower[row][column] = math.sqrt(value)
            else:
                lower[row][column] = value / lower[column][column]
    return lower


def _solve_cholesky(lower: list[list[float]], vector: Sequence[float]) -> list[float]:
    size = len(lower)
    forward = [0.0] * size
    for row in range(size):
        forward[row] = (
            vector[row]
            - math.fsum(lower[row][column] * forward[column] for column in range(row))
        ) / lower[row][row]
    result = [0.0] * size
    for row in reversed(range(size)):
        result[row] = (
            forward[row]
            - math.fsum(lower[column][row] * result[column] for column in range(row + 1, size))
        ) / lower[row][row]
    return result


def _kernel(distance: float, length_scale: float = 0.35) -> float:
    return math.exp(-0.5 * (distance / length_scale) ** 2)


def _gp_prediction(
    observed: Sequence[OfflineCandidateV1],
    candidate: OfflineCandidateV1,
    bounds: Mapping[str, tuple[float, float]],
) -> tuple[float, float]:
    values = [row.endpoint_value for row in observed]
    mean_value = math.fsum(values) / len(values)
    scale = max(
        math.sqrt(math.fsum((value - mean_value) ** 2 for value in values) / len(values)),
        1e-9,
    )
    targets = [(value - mean_value) / scale for value in values]
    covariance = [
        [
            _kernel(_distance(left, right, bounds)) + (1e-8 if i == j else 0.0)
            for j, right in enumerate(observed)
        ]
        for i, left in enumerate(observed)
    ]
    lower = _cholesky(covariance)
    alpha = _solve_cholesky(lower, targets)
    vector = [_kernel(_distance(row, candidate, bounds)) for row in observed]
    predicted_standard = math.fsum(weight * value for weight, value in zip(vector, alpha, strict=True))
    projection = _solve_cholesky(lower, vector)
    variance = max(0.0, 1.0 - math.fsum(value * value for value in projection))
    return mean_value + scale * predicted_standard, scale * math.sqrt(variance)


def _validate_pool(
    candidates: Sequence[OfflineCandidateV1],
    baseline_id: str,
) -> tuple[tuple[OfflineCandidateV1, ...], OfflineCandidateV1, dict[str, tuple[float, float]]]:
    pool = tuple(candidates)
    if len(pool) < 2:
        raise ValueError("candidate pool requires a baseline and at least one challenger")
    if len({row.candidate_id for row in pool}) != len(pool):
        raise ValueError("candidate IDs must be unique")
    matches = [row for row in pool if row.candidate_id == baseline_id]
    if len(matches) != 1:
        raise ValueError("baseline_id must identify exactly one candidate")
    variable_names = set(matches[0].variables)
    if any(set(row.variables) != variable_names for row in pool):
        raise ValueError("all candidates must share the same variable set")
    coordinate_keys = [tuple(row.variables[name] for name in sorted(variable_names)) for row in pool]
    if len(coordinate_keys) != len(set(coordinate_keys)):
        raise ValueError("candidate variable coordinates must be unique")
    bounds = {
        name: (
            min(row.variables[name] for row in pool),
            max(row.variables[name] for row in pool),
        )
        for name in sorted(variable_names)
    }
    return pool, matches[0], bounds


def compare_search_arms(
    candidates: Sequence[OfflineCandidateV1],
    *,
    baseline_id: str,
    endpoint_id: str,
    budget_per_arm: int = 64,
    seeds: Sequence[int] = (17, 29, 43, 71, 101),
    minimize: bool = True,
) -> dict[str, Any]:
    """Compare random, simple-local, and conservative-GP selection fairly."""

    if not isinstance(endpoint_id, str) or not endpoint_id.strip():
        raise ValueError("one endpoint_id is required")
    if isinstance(budget_per_arm, bool) or budget_per_arm < 1:
        raise ValueError("budget_per_arm must be a positive integer")
    if not seeds or len(set(seeds)) != len(seeds) or any(
        isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds
    ):
        raise ValueError("seeds must be unique integers")
    pool, baseline, bounds = _validate_pool(candidates, baseline_id)
    challengers = tuple(row for row in pool if row.candidate_id != baseline_id)
    if len(challengers) < budget_per_arm:
        return {
            "schema_version": "conservative-search-comparison-v1",
            "selection_status": "WITHHELD_INSUFFICIENT_UNIQUE_FEASIBLE_CANDIDATES",
            "endpoint_id": endpoint_id,
            "required_nonbaseline_candidates": budget_per_arm,
            "available_nonbaseline_candidates": len(challengers),
            "ranked_candidates": [],
            "pareto_candidates": [],
            "unordered_candidates": [row.candidate_id for row in challengers],
            "formula_action": "NO_CHANGE",
            **FALSE_ACTION_AUTHORITY,
        }

    direction = 1.0 if minimize else -1.0
    all_runs: list[dict[str, Any]] = []
    selected_outcomes: dict[str, list[float]] = {
        "random": [],
        "simple_local": [],
        "conservative_gp": [],
    }
    queried_union: dict[str, OfflineCandidateV1] = {}
    for seed in seeds:
        rng = random.Random(seed)
        shuffled = list(challengers)
        rng.shuffle(shuffled)
        random_rows = shuffled[:budget_per_arm]

        local_rows: list[OfflineCandidateV1] = []
        remaining = set(row.candidate_id for row in challengers)
        current = baseline
        while len(local_rows) < budget_per_arm:
            candidate = min(
                (row for row in challengers if row.candidate_id in remaining),
                key=lambda row: (
                    _distance(current, row, bounds),
                    direction * row.endpoint_value,
                    row.candidate_id,
                ),
            )
            local_rows.append(candidate)
            remaining.remove(candidate.candidate_id)
            best = min(local_rows, key=lambda row: (direction * row.endpoint_value, row.candidate_id))
            current = best

        gp_rows: list[OfflineCandidateV1] = []
        gp_remaining = {row.candidate_id: row for row in challengers}
        initial = min(
            challengers,
            key=lambda row: (_distance(baseline, row, bounds), rng.random()),
        )
        gp_rows.append(initial)
        gp_remaining.pop(initial.candidate_id)
        while len(gp_rows) < budget_per_arm:
            acquisitions: list[tuple[float, str, OfflineCandidateV1]] = []
            for candidate in gp_remaining.values():
                predicted, standard_deviation = _gp_prediction(gp_rows, candidate, bounds)
                # Upper confidence bound for minimization (lower for maximization)
                # penalizes unsupported extrapolation instead of rewarding it.
                conservative = (
                    predicted + 1.96 * standard_deviation
                    if minimize
                    else -(predicted - 1.96 * standard_deviation)
                )
                acquisitions.append((conservative, candidate.candidate_id, candidate))
            _score, _candidate_id, chosen = min(acquisitions)
            gp_rows.append(chosen)
            gp_remaining.pop(chosen.candidate_id)

        arm_rows = {
            "random": random_rows,
            "simple_local": local_rows,
            "conservative_gp": gp_rows,
        }
        run: dict[str, Any] = {"seed": seed, "arms": {}}
        for arm, rows in arm_rows.items():
            best = min(rows, key=lambda row: (direction * row.endpoint_value, row.candidate_id))
            selected_outcomes[arm].append(best.endpoint_value)
            queried_union.update({row.candidate_id: row for row in rows})
            run["arms"][arm] = {
                "queried_candidate_ids": [row.candidate_id for row in rows],
                "unique_feasible_nonbaseline_evaluations": len({row.candidate_id for row in rows}),
                "selected_candidate_id": best.candidate_id,
                "selected_endpoint_value": best.endpoint_value,
            }
        all_runs.append(run)

    expected = budget_per_arm
    equal_budget = all(
        arm["unique_feasible_nonbaseline_evaluations"] == expected
        for run in all_runs
        for arm in run["arms"].values()
    )
    gp_median = median(selected_outcomes["conservative_gp"])
    adaptive_beats_baselines = (
        gp_median < median(selected_outcomes["random"])
        and gp_median < median(selected_outcomes["simple_local"])
        if minimize
        else gp_median > median(selected_outcomes["random"])
        and gp_median > median(selected_outcomes["simple_local"])
    )

    queried = list(queried_union.values())
    coverage_values = {row.coverage_decimal for row in queried}
    out_of_domain = any(row.applicability_state != "APPLICABLE" for row in queried)
    signs_disagree = any(
        len({sign for sign in row.model_signs.values() if sign != 0}) > 1
        for row in queried
    )
    diagnostic_order = sorted(
        queried,
        key=lambda row: (
            direction * row.endpoint_value,
            row.candidate_id,
        ),
    )
    robust_order = all(
        (
            left.prediction_interval[1] < right.prediction_interval[0]
            if minimize
            else left.prediction_interval[0] > right.prediction_interval[1]
        )
        for left, right in zip(diagnostic_order, diagnostic_order[1:])
    )
    reasons: list[str] = []
    if not equal_budget:
        reasons.append("UNEQUAL_SEARCH_BUDGET")
    if not adaptive_beats_baselines:
        reasons.append("ADAPTIVE_NOT_BETTER_THAN_BASELINES")
    if len(coverage_values) != 1:
        reasons.append("CANDIDATE_COVERAGE_DIFFERS")
    if out_of_domain:
        reasons.append("CANDIDATE_OUT_OF_DOMAIN")
    if signs_disagree:
        reasons.append("MODEL_SIGNS_DISAGREE")
    if not robust_order:
        reasons.append("UNCERTAINTY_INTERVALS_NONDISCRIMINATING")
    withheld = bool(reasons)
    ranked = [] if withheld else [row.as_dict() for row in diagnostic_order]
    return {
        "schema_version": "conservative-search-comparison-v1",
        "selection_status": (
            "WITHHELD_NONDISCRIMINATING_EVIDENCE"
            if withheld
            else "SUPPORTED_ENDPOINT_ORDERING"
        ),
        "endpoint_id": endpoint_id,
        "baseline": baseline.as_dict(),
        "ranked_candidates": ranked,
        "pareto_candidates": [],
        "unordered_candidates": (
            sorted(queried_union) if withheld else []
        ),
        "best_observed_candidate": ranked[0] if ranked else None,
        "experimental_recommendation": (
            {"candidate_id": ranked[0]["candidate_id"], "scope": "ENDPOINT_ONLY_PROPOSE_ONLY"}
            if ranked
            else None
        ),
        "shortlist_ordering": "UNORDERED_DIVERSE_SET" if withheld else "ENDPOINT_ONLY",
        "formula_action": "NO_CHANGE" if withheld else "PROPOSE_ONLY",
        "reason_codes": reasons,
        "budget_per_arm_per_seed": budget_per_arm,
        "seeds": list(seeds),
        "benchmark_equal_budget": equal_budget,
        "adaptive_beats_random_and_simple_local": adaptive_beats_baselines,
        "selected_outcomes": selected_outcomes,
        "runs": all_runs,
        "algorithm_versions": {
            "random": "seeded-uniform-finite-pool-v1",
            "simple_local": "deterministic-nearest-pattern-v1",
            "conservative_gp": "rbf-gp-upper-confidence-support-penalty-v1",
        },
        **FALSE_ACTION_AUTHORITY,
    }


def lavender_ambrox_search_contract(
    *,
    accounting_result: Mapping[str, Any],
    lavender_component_ids: Sequence[str],
    ambrox_component_id: str,
    lavender_split: tuple[int, int] = (70, 30),
) -> dict[str, Any]:
    """Create the two-variable search contract or hold on unresolved mass."""

    if tuple(lavender_split) != (70, 30):
        raise ValueError("the admitted lavender block is fixed at 70:30")
    if len(tuple(lavender_component_ids)) != 2:
        raise ValueError("the lavender block requires exactly two component IDs")
    if not accounting_result.get("common_active_mass_basis_available"):
        return {
            "schema_version": "lavender-ambrox-search-contract-v1",
            "selection_status": "HOLD_CONSTANT_TOTAL_BASIS_UNRESOLVED",
            "variables": [],
            "frozen_non_target_rows": True,
            "lavender_block_split": [70, 30],
            "crystal_ambrox_unit": "mg",
            "ranked_candidates": [],
            "best_observed_candidate": None,
            "experimental_recommendation": None,
            "formula_action": "NO_CHANGE",
            **FALSE_ACTION_AUTHORITY,
        }
    return {
        "schema_version": "lavender-ambrox-search-contract-v1",
        "selection_status": "SEARCH_SPACE_ADMITTED_EVALUATOR_REQUIRED",
        "constant_total_basis": "active_mass_g",
        "constant_total_decimal": accounting_result["total_active_mass_g_decimal"],
        "variables": [
            {
                "variable_id": "lavender_block_active_mass_g",
                "component_ids": list(lavender_component_ids),
                "fixed_internal_split": [70, 30],
            },
            {
                "variable_id": "crystal_ambrox_active_mass_g",
                "component_ids": [ambrox_component_id],
                "physical_command_unit": "mg",
            },
        ],
        "frozen_non_target_rows": True,
        "formula_action": "NO_CHANGE",
        **FALSE_ACTION_AUTHORITY,
    }


__all__ = [
    "OfflineCandidateV1",
    "compare_search_arms",
    "lavender_ambrox_search_contract",
]
