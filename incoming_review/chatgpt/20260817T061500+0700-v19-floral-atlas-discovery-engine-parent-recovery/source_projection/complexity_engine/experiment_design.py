from __future__ import annotations

import itertools
from decimal import Decimal
from typing import Any

from consultant_core import sha256_json


def _dstr(value: Decimal) -> str:
    s = format(value.normalize(), "f")
    return "0" if s in {"", "-0"} else s


def constrained_simplex_centroid(
    components: list[str],
    *,
    lower_bounds: dict[str, float | str] | None = None,
    max_components: int = 6,
) -> dict[str, Any]:
    """Generate a constrained simplex-centroid design with all nonempty subsets.

    The transform uses pseudo-components. The result is a design geometry, not a
    sensory model or recommended perfume ratio.
    """
    if len(components) < 2:
        raise ValueError("At least two mixture components are required.")
    if len(components) > max_components:
        raise ValueError(f"At most {max_components} components are allowed in this bounded generator.")
    if len(set(components)) != len(components):
        raise ValueError("Components must be unique.")
    lower = {c: Decimal(str((lower_bounds or {}).get(c, 0))) for c in components}
    if any(v < 0 for v in lower.values()):
        raise ValueError("Lower bounds cannot be negative.")
    lower_sum = sum(lower.values())
    if lower_sum >= 1:
        raise ValueError("Lower bounds must sum to less than 1.")
    residual = Decimal("1") - lower_sum

    points: list[dict[str, Any]] = []
    for size in range(1, len(components) + 1):
        for subset in itertools.combinations(components, size):
            pseudo = {c: (Decimal("1") / Decimal(size) if c in subset else Decimal("0")) for c in components}
            original = {c: lower[c] + residual * pseudo[c] for c in components}
            points.append({
                "point_id": "SC-" + "-".join(subset),
                "subset": list(subset),
                "proportions": {c: _dstr(original[c]) for c in components},
                "pseudo_proportions": {c: _dstr(pseudo[c]) for c in components},
                "is_interior": all(original[c] > lower[c] for c in components),
            })
    result = {
        "state": "DESIGN_GENERATED",
        "components": components,
        "lower_bounds": {c: _dstr(v) for c, v in lower.items()},
        "point_count": len(points),
        "points": points,
        "interior_augmentation_advised": len(components) >= 3,
        "physical_result_state": "NOT_RUN",
        "boundary": "Mixture-design coordinates identify informative proportions; they do not establish pleasantness or interaction direction.",
    }
    result["design_hash"] = sha256_json(result)
    return result


def build_model_isolate_plan(
    model: dict[str, Any],
    *,
    invariant_values: dict[str, str],
    manipulated_values: tuple[str, str, str] = ("NULL", "INTERMEDIATE", "FULL"),
) -> dict[str, Any]:
    axes = list(model.get("manipulated_axes") or [])
    if len(axes) != 1:
        raise ValueError("The compact isolate generator requires exactly one manipulated axis.")
    invariant_names = list(model.get("invariants") or [])
    missing = [name for name in invariant_names if name not in invariant_values]
    if missing:
        raise ValueError("Missing invariant values: " + ", ".join(missing))
    axis = axes[0]
    roles = ("NULL", "INTERMEDIATE", "FULL")
    arms = []
    for role, value in zip(roles, manipulated_values):
        values = dict(invariant_values)
        values[axis] = value
        arms.append({"arm_id": f"{model['model_id']}-{role}", "role": role, "values": values})
    result = {
        "experiment_id": f"EXP-{model['model_id']}-ISOLATE-001",
        "model_id": model["model_id"],
        "workflow_state": "DESIGNED",
        "manipulated_axis": axis,
        "invariants": [{"name": name, "target": invariant_values[name], "tolerance": "0"} for name in invariant_names],
        "arms": arms,
        "decision_rule": "Retain, refine, restrict, reject, or repeat the mechanism under the preregistered identity and hedonic vectors.",
        "physical_result_state": "NOT_RUN",
        "formula_mutation_authorized": False,
        "boundary": "This plan creates coded arms only; it creates no observation, liking winner, or formula promotion.",
    }
    result["plan_hash"] = sha256_json(result)
    return result
