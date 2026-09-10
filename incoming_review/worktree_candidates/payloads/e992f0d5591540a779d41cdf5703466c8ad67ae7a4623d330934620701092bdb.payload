from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from consultant_core import sha256_json


def _dec(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"non-numeric invariant value {value!r}") from exc


def _comparison_mode(inv: dict[str, Any]) -> str:
    requested = str(inv.get("comparison") or "AUTO").upper()
    if requested not in {"AUTO", "NUMERIC", "EXACT"}:
        raise ValueError(f"unknown comparison mode {requested!r}")
    if requested != "AUTO":
        return requested
    try:
        _dec(inv.get("target"))
        return "NUMERIC"
    except ValueError:
        return "EXACT"


def validate_causal_experiment(exp: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    violations: list[str] = []
    warnings: list[str] = []

    for field in ("experiment_id", "model_id", "manipulated_axis", "decision_rule"):
        if not exp.get(field):
            failures.append(f"{field} is required.")

    arms = list(exp.get("arms") or [])
    roles = {str(a.get("role") or "").upper() for a in arms}
    if "NULL" not in roles:
        failures.append("A causal model experiment requires a NULL arm.")
    if "FULL" not in roles:
        failures.append("A causal model experiment requires a FULL arm.")
    if len(arms) < 2:
        failures.append("At least two arms are required.")

    invariant_names: list[str] = []
    invariant_comparisons: dict[str, str] = {}
    for inv in exp.get("invariants") or []:
        name = str(inv.get("name") or "").strip()
        if not name:
            failures.append("Each invariant requires a name.")
            continue
        invariant_names.append(name)
        try:
            mode = _comparison_mode(inv)
        except ValueError as exc:
            failures.append(f"{name}: {exc}")
            continue
        invariant_comparisons[name] = mode
        target_raw = inv.get("target")
        if target_raw is None:
            failures.append(f"{name}: target is required.")
            continue

        if mode == "NUMERIC":
            try:
                target = _dec(target_raw)
                tolerance = _dec(inv.get("tolerance", "0"))
            except ValueError as exc:
                failures.append(f"{name}: {exc}")
                continue
            if tolerance < 0:
                failures.append(f"{name}: tolerance cannot be negative.")
                continue
            for arm in arms:
                arm_id = str(arm.get("arm_id") or "UNNAMED")
                values = arm.get("values") or {}
                if name not in values:
                    violations.append(f"{arm_id}: invariant {name} is missing.")
                    continue
                try:
                    actual = _dec(values[name])
                except ValueError as exc:
                    violations.append(f"{arm_id}: invariant {name}: {exc}")
                    continue
                if abs(actual - target) > tolerance:
                    violations.append(
                        f"{arm_id}: invariant {name} drifted to {actual}; target {target} ± {tolerance}."
                    )
        else:
            if inv.get("tolerance") not in (None, "", 0, "0"):
                failures.append(f"{name}: EXACT invariants cannot use a nonzero tolerance.")
                continue
            target = str(target_raw)
            for arm in arms:
                arm_id = str(arm.get("arm_id") or "UNNAMED")
                values = arm.get("values") or {}
                if name not in values:
                    violations.append(f"{arm_id}: invariant {name} is missing.")
                    continue
                actual = str(values[name])
                if actual != target:
                    violations.append(
                        f"{arm_id}: invariant {name} drifted to {actual!r}; exact target is {target!r}."
                    )

    manipulated = str(exp.get("manipulated_axis") or "")
    if manipulated and arms:
        values = {str((arm.get("values") or {}).get(manipulated, "<MISSING>")) for arm in arms}
        if "<MISSING>" in values:
            failures.append("The manipulated_axis is missing from one or more arms.")
        if len(values) < 2:
            failures.append("The manipulated_axis does not vary across arms.")
        if manipulated in invariant_names:
            failures.append("The manipulated_axis cannot also be an invariant.")

    workflow = str(exp.get("workflow_state") or "DESIGNED").upper()
    if workflow in {"OBSERVED", "MEASURED", "DECIDED"} and not exp.get("evidence_links"):
        failures.append("Empirical workflow state requires atomic evidence_links.")

    if failures or violations:
        state = "REBUILD"
    else:
        state = "PASS_FOR_DESIGN" if workflow in {"DESIGNED", "NOT_RUN", "PROPOSED"} else "CONDITIONAL_EMPIRICAL"

    result = {
        "state": state,
        "experiment_id": exp.get("experiment_id"),
        "model_id": exp.get("model_id"),
        "workflow_state": workflow,
        "manipulated_axis": manipulated or None,
        "invariants": invariant_names,
        "invariant_comparisons": invariant_comparisons,
        "arm_roles": sorted(roles),
        "failures": failures,
        "invariant_violations": violations,
        "warnings": warnings,
        "formula_mutation_authorized": False,
        "physical_result_created": False,
        "boundary": "A valid design does not establish that the mechanism exists or is liked.",
        "input_hash": sha256_json(exp),
    }
    result["result_hash"] = sha256_json(result)
    return result
