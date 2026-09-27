"""Low-capacity Davidson paired-preference model with explicit ties.

Utilities are scoped to one user, criterion, protocol, and connected candidate
set.  The result is diagnostic evidence and never authorizes compounding or a
formula change.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Sequence

from engine.preference import PairwisePreference

from .contracts import FALSE_ACTION_AUTHORITY


@dataclass(frozen=True, slots=True)
class DavidsonFitConfigV1:
    minimum_comparisons: int = 10
    minimum_sessions: int = 3
    regularization: float = 0.1
    learning_rate: float = 0.15
    maximum_iterations: int = 4000
    bootstrap_replicates: int = 0
    bootstrap_seed: int = 17

    def __post_init__(self) -> None:
        if self.minimum_comparisons < 1 or self.minimum_sessions < 1:
            raise ValueError("minimum gates must be positive")
        if self.maximum_iterations < 1 or self.bootstrap_replicates < 0:
            raise ValueError("iteration and bootstrap counts are invalid")
        if not math.isfinite(self.regularization) or self.regularization < 0:
            raise ValueError("regularization must be finite and non-negative")
        if not math.isfinite(self.learning_rate) or self.learning_rate <= 0:
            raise ValueError("learning_rate must be finite and positive")


def _connected(items: Sequence[str], rows: Sequence[PairwisePreference]) -> bool:
    if len(items) < 2:
        return False
    graph: dict[str, set[str]] = {item: set() for item in items}
    for row in rows:
        graph[row.left_item].add(row.right_item)
        graph[row.right_item].add(row.left_item)
    seen = {items[0]}
    pending = [items[0]]
    while pending:
        node = pending.pop()
        for neighbour in graph[node] - seen:
            seen.add(neighbour)
            pending.append(neighbour)
    return len(seen) == len(items)


def _probabilities(left: float, right: float, tie_log: float) -> tuple[float, float, float]:
    difference = max(-50.0, min(50.0, left - right))
    a = math.exp(difference / 2.0)
    b = math.exp(-difference / 2.0)
    nu = math.exp(max(-20.0, min(20.0, tie_log)))
    denominator = a + b + 2.0 * nu
    return a / denominator, b / denominator, 2.0 * nu / denominator


def _fit(
    rows: Sequence[PairwisePreference], config: DavidsonFitConfigV1
) -> tuple[dict[str, float], float]:
    items = sorted({row.left_item for row in rows} | {row.right_item for row in rows})
    utilities = {item: 0.0 for item in items}
    tie_log = -1.0
    scale = max(1, len(rows))
    for iteration in range(config.maximum_iterations):
        gradient = {item: -config.regularization * utilities[item] for item in items}
        tie_gradient = -config.regularization * tie_log
        for row in rows:
            left = utilities[row.left_item]
            right = utilities[row.right_item]
            difference = max(-50.0, min(50.0, left - right))
            a = math.exp(difference / 2.0)
            b = math.exp(-difference / 2.0)
            nu = math.exp(max(-20.0, min(20.0, tie_log)))
            denominator = a + b + 2.0 * nu
            denom_d = 0.5 * (a - b) / denominator
            if row.preferred_item == row.left_item:
                difference_gradient = 0.5 - denom_d
            elif row.preferred_item == row.right_item:
                difference_gradient = -0.5 - denom_d
            else:
                difference_gradient = -denom_d
            gradient[row.left_item] += difference_gradient
            gradient[row.right_item] -= difference_gradient
            tie_share = 2.0 * nu / denominator
            tie_gradient += (1.0 if row.preferred_item is None else 0.0) - tie_share
        step_scale = config.learning_rate / (scale * (1.0 + iteration / 250.0) ** 0.5)
        max_step = 0.0
        for item in items:
            step = step_scale * gradient[item]
            utilities[item] += step
            max_step = max(max_step, abs(step))
        tie_step = step_scale * tie_gradient
        tie_log = max(-20.0, min(20.0, tie_log + tie_step))
        max_step = max(max_step, abs(tie_step))
        mean = math.fsum(utilities.values()) / len(utilities)
        for item in items:
            utilities[item] -= mean
        if max_step < 1e-10:
            break
    return utilities, math.exp(tie_log)


def _percentile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("percentile requires observations")
    position = (len(ordered) - 1) * probability
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def fit_davidson_personal_preference(
    comparisons: Sequence[PairwisePreference],
    *,
    criterion_id: str,
    config: DavidsonFitConfigV1 = DavidsonFitConfigV1(),
) -> dict[str, Any]:
    """Fit personal pairwise utilities with session-clustered uncertainty."""

    rows = tuple(comparisons)
    if not isinstance(criterion_id, str) or not criterion_id.strip():
        raise ValueError("criterion_id must be non-empty text")
    failures: list[str] = []
    if len(rows) < config.minimum_comparisons:
        failures.append("MINIMUM_COMPARISONS_NOT_MET")
    if any(row.criterion_id != criterion_id for row in rows):
        failures.append("CRITERION_SCOPE_MISMATCH")
    if any(row.protocol_id is None for row in rows):
        failures.append("PROTOCOL_SCOPE_MISSING")
    protocols = {row.protocol_id for row in rows if row.protocol_id is not None}
    if len(protocols) > 1:
        failures.append("MULTIPLE_PROTOCOLS_MIXED")
    if any(row.assessor_id is None for row in rows):
        failures.append("ASSESSOR_SCOPE_MISSING")
    assessors = {row.assessor_id for row in rows if row.assessor_id is not None}
    if len(assessors) > 1:
        failures.append("MULTIPLE_ASSESSORS_MIXED")
    if any(row.comparison_id is None for row in rows):
        failures.append("COMPARISON_ID_MISSING")
    ids = [row.comparison_id for row in rows if row.comparison_id is not None]
    if len(ids) != len(set(ids)):
        failures.append("DUPLICATE_COMPARISON_ID")
    # Existing PairwisePreference lacks a dedicated session field; protocol_id
    # is not overloaded. Session identity is carried in comparison_id as the
    # stable prefix before the first colon for this v1 adapter.
    session_ids = {
        str(row.comparison_id).split(":", 1)[0]
        for row in rows
        if row.comparison_id is not None
    }
    if len(session_ids) < config.minimum_sessions:
        failures.append("MINIMUM_SESSIONS_NOT_MET")
    items = sorted({row.left_item for row in rows} | {row.right_item for row in rows})
    if not _connected(items, rows):
        failures.append("COMPARISON_GRAPH_DISCONNECTED")
    if failures:
        return {
            "schema_version": "davidson-personal-preference-v1",
            "status": "WITHHELD",
            "criterion_id": criterion_id,
            "utilities": {},
            "tie_parameter": None,
            "utility_intervals": {},
            "comparison_count": len(rows),
            "session_count": len(session_ids),
            "reason_codes": sorted(set(failures)),
            "population_claim_authorized": False,
            "formula_action": "NO_CHANGE",
            **FALSE_ACTION_AUTHORITY,
        }

    utilities, tie_parameter = _fit(rows, config)
    draws: dict[str, list[float]] = defaultdict(list)
    if config.bootstrap_replicates:
        by_session: dict[str, list[PairwisePreference]] = defaultdict(list)
        for row in rows:
            assert row.comparison_id is not None
            by_session[row.comparison_id.split(":", 1)[0]].append(row)
        sessions = sorted(by_session)
        rng = random.Random(config.bootstrap_seed)
        bootstrap_config = DavidsonFitConfigV1(
            minimum_comparisons=1,
            minimum_sessions=1,
            regularization=config.regularization,
            learning_rate=config.learning_rate,
            maximum_iterations=config.maximum_iterations,
            bootstrap_replicates=0,
            bootstrap_seed=config.bootstrap_seed,
        )
        for _ in range(config.bootstrap_replicates):
            sampled: list[PairwisePreference] = []
            for _slot in sessions:
                sampled.extend(by_session[rng.choice(sessions)])
            if _connected(items, sampled):
                fitted, _tie = _fit(sampled, bootstrap_config)
                for item in items:
                    draws[item].append(fitted[item])
    intervals = {
        item: [
            _percentile(draws[item], 0.025),
            _percentile(draws[item], 0.975),
        ]
        for item in items
        if draws[item]
    }
    tie_count = sum(row.preferred_item is None for row in rows)
    pair_probabilities = {
        f"{left}|{right}": dict(
            zip(
                ("left", "right", "tie"),
                _probabilities(utilities[left], utilities[right], math.log(tie_parameter)),
                strict=True,
            )
        )
        for index, left in enumerate(items)
        for right in items[index + 1 :]
    }
    return {
        "schema_version": "davidson-personal-preference-v1",
        "status": "DIAGNOSTIC_PERSONAL_EVIDENCE",
        "criterion_id": criterion_id,
        "utilities": {key: utilities[key] for key in sorted(utilities)},
        "tie_parameter": tie_parameter,
        "tie_rate": tie_count / len(rows),
        "utility_intervals": intervals,
        "pair_probabilities": pair_probabilities,
        "comparison_count": len(rows),
        "session_count": len(session_ids),
        "bootstrap_replicates_requested": config.bootstrap_replicates,
        "bootstrap_replicates_usable": min(
            (len(value) for value in draws.values()), default=0
        ),
        "reason_codes": ["PERSONAL_SCOPE_ONLY", "NO_FORMULA_ACTION_AUTHORITY"],
        "population_claim_authorized": False,
        "formula_action": "NO_CHANGE",
        **FALSE_ACTION_AUTHORITY,
    }


__all__ = ["DavidsonFitConfigV1", "fit_davidson_personal_preference"]
