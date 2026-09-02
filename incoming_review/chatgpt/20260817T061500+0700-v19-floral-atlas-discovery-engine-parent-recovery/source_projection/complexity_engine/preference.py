from __future__ import annotations

import itertools
import math
from typing import Any

from consultant_core import sha256_json


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-min(x, 50))
        return 1 / (1 + z)
    z = math.exp(max(x, -50))
    return z / (1 + z)


def fit_preference_model(
    features: dict[str, dict[str, float]],
    comparisons: list[dict[str, str]],
    *,
    learning_rate: float = 0.08,
    iterations: int = 600,
    l2: float = 0.02,
) -> dict[str, Any]:
    """Fit a small individual Bradley-Terry feature model.

    This is an experiment-selection aid, not a beauty or broad-appeal model.
    """
    names = sorted({k for vals in features.values() for k in vals})
    weights = {name: 0.0 for name in names}
    assessor_ids = {str(c.get("assessor_id")) for c in comparisons if c.get("assessor_id")}
    if len(assessor_ids) > 1:
        result = {
            "state": "REJECTED_MIXED_ASSESSORS",
            "scope": "INDIVIDUAL_PREFERENCE_ONLY",
            "assessor_ids": sorted(assessor_ids),
            "comparison_count": 0,
            "broad_appeal_claim": "PROHIBITED",
            "boundary": "One individual preference model cannot pool multiple assessors. Use separate models or a population model with an explicit protocol.",
        }
        result["model_hash"] = sha256_json(result)
        return result
    assessor_scope = next(iter(assessor_ids), "UNSPECIFIED_SINGLE_ASSESSOR_REQUIRED_BEFORE_EMPIRICAL_USE")
    usable = []
    for comp in comparisons:
        left, right, winner = comp.get("left"), comp.get("right"), comp.get("winner")
        if left in features and right in features and winner in {left, right} and left != right:
            usable.append((left, right, winner))

    for _ in range(iterations):
        grad = {name: -l2 * weights[name] for name in names}
        for left, right, winner in usable:
            diff = {name: float(features[left].get(name, 0.0)) - float(features[right].get(name, 0.0)) for name in names}
            score = sum(weights[name] * diff[name] for name in names)
            p_left = _sigmoid(score)
            y = 1.0 if winner == left else 0.0
            err = y - p_left
            for name in names:
                grad[name] += err * diff[name]
        scale = max(1, len(usable))
        for name in names:
            weights[name] += learning_rate * grad[name] / scale

    item_scores = {
        item: sum(weights[name] * float(vals.get(name, 0.0)) for name in names)
        for item, vals in features.items()
    }
    model = {
        "state": "FITTED" if usable else "PRIOR_ONLY",
        "scope": "INDIVIDUAL_PREFERENCE_ONLY",
        "assessor_scope": assessor_scope,
        "feature_names": names,
        "weights": {k: round(v, 10) for k, v in weights.items()},
        "item_scores": {k: round(v, 10) for k, v in sorted(item_scores.items())},
        "comparison_count": len(usable),
        "broad_appeal_claim": "PROHIBITED",
        "boundary": "This model learns one assessor's observed choices only; it does not compute universal beauty.",
    }
    model["model_hash"] = sha256_json(model)
    return model


def select_next_pair(
    features: dict[str, dict[str, float]],
    comparisons: list[dict[str, str]],
    model: dict[str, Any],
) -> dict[str, Any]:
    tested = {frozenset((str(c.get("left")), str(c.get("right")))) for c in comparisons}
    names = list(model.get("feature_names") or [])
    weights = {k: float(v) for k, v in (model.get("weights") or {}).items()}
    candidates: list[tuple[float, str, str, float, float]] = []

    for left, right in itertools.combinations(sorted(features), 2):
        if frozenset((left, right)) in tested:
            continue
        diff = [float(features[left].get(name, 0.0)) - float(features[right].get(name, 0.0)) for name in names]
        score = sum(weights.get(name, 0.0) * d for name, d in zip(names, diff))
        p = _sigmoid(score)
        uncertainty = 1.0 - abs(p - 0.5) * 2.0
        novelty = math.sqrt(sum(d * d for d in diff))
        priority = uncertainty + 0.15 * novelty
        candidates.append((priority, left, right, p, novelty))

    if not candidates:
        result = {
            "state": "NO_UNTESTED_PAIR",
            "broad_appeal_claim": "PROHIBITED",
            "reason": "Every candidate pair has already been compared or fewer than two candidates exist.",
        }
    else:
        priority, left, right, p, novelty = max(candidates, key=lambda x: (x[0], x[1], x[2]))
        result = {
            "state": "PAIR_SELECTED",
            "left": left,
            "right": right,
            "predicted_left_preference_probability": round(p, 9),
            "selection_uncertainty": round(1.0 - abs(p - 0.5) * 2.0, 9),
            "feature_novelty": round(novelty, 9),
            "selection_priority": round(priority, 9),
            "decision_enabled": "Update the individual preference surface and discriminate among currently plausible feature weights.",
            "broad_appeal_claim": "PROHIBITED",
        }
    result["result_hash"] = sha256_json(result)
    return result
