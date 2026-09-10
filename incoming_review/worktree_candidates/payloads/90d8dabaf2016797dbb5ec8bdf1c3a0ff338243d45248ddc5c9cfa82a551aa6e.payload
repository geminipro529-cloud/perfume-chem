from __future__ import annotations

import re
from typing import Any

from consultant_core import sha256_json

MODEL_LEVELS = {
    "MEASUREMENT_MODEL",
    "TECHNIQUE",
    "ARTISTIC_GENERATOR",
    "FORMULA_ARCHITECTURE",
    "FORMULA_INSTANCE",
    "ENVIRONMENT_MODEL",
    "EVALUATOR",
    "DECISION_MODEL",
    "OVERLAY",
    "META_MODEL",
}

EVIDENCE_STATES = {
    "PROPOSED",
    "DESIGNED",
    "SOURCE_SUPPORTED_HYPOTHESIS",
    "NOT_RUN",
    "NOT_TESTED",
    "OBSERVED",
    "MEASURED",
    "INFERRED_FROM_LOCKED_DATA",
    "INVALIDATED",
}

_REQUIRED = {
    "model_id",
    "version",
    "name",
    "model_level",
    "target_identity",
    "artistic_contract",
    "manipulated_axes",
    "invariants",
    "null_model_id",
    "outputs",
    "failure_boundaries",
    "evidence_state",
    "source_refs",
}


def _nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(str(x).strip() for x in value)


def validate_model_definition(model: dict[str, Any]) -> dict[str, Any]:
    """Validate one artistic/measurement model without mixing ontology layers."""
    failures: list[str] = []
    warnings: list[str] = []

    missing = sorted(k for k in _REQUIRED if k not in model or model[k] in (None, "", []))
    if missing:
        failures.append("Missing required fields: " + ", ".join(missing))

    level = model.get("model_level")
    if not isinstance(level, str):
        failures.append("A model must declare exactly one model_level string; one model_level per record is required.")
        normalized_level = None
    else:
        normalized_level = level.strip().upper()
        if normalized_level not in MODEL_LEVELS:
            failures.append(f"Unknown model_level: {level!r}.")

    model_id = str(model.get("model_id") or "")
    if model_id and not re.fullmatch(r"[A-Z][A-Z0-9_-]{2,63}", model_id):
        warnings.append("model_id is not in the recommended immutable uppercase identifier form.")

    version = str(model.get("version") or "")
    if version and not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", version):
        failures.append("version must be semantic-version shaped, for example 1.0.0.")

    for key in ("manipulated_axes", "invariants", "outputs", "failure_boundaries", "source_refs"):
        if key in model and not _nonempty_list(model.get(key)):
            failures.append(f"{key} must be a non-empty list of non-empty values.")

    axes = {str(x).strip().casefold() for x in model.get("manipulated_axes", []) if str(x).strip()}
    invariants = {str(x).strip().casefold() for x in model.get("invariants", []) if str(x).strip()}
    overlap = sorted(axes & invariants)
    if overlap:
        failures.append("A field cannot be both manipulated and invariant: " + ", ".join(overlap))

    if model.get("null_model_id") == model.get("model_id"):
        failures.append("null_model_id cannot equal model_id.")

    evidence_state = str(model.get("evidence_state") or "").upper()
    if evidence_state and evidence_state not in EVIDENCE_STATES:
        failures.append(f"Unknown evidence_state: {evidence_state!r}.")

    if evidence_state in {"OBSERVED", "MEASURED"} and not model.get("evidence_links"):
        failures.append("OBSERVED or MEASURED model state requires atomic evidence_links.")

    state = "PASS" if not failures else "REBUILD"
    result = {
        "state": state,
        "model_id": model.get("model_id"),
        "model_level": normalized_level,
        "evidence_state": evidence_state or None,
        "failures": failures,
        "warnings": warnings,
        "ontology_boundary": (
            "One record occupies one model layer. Cross-layer relationships are links, not mixed model_level values."
        ),
        "canonical_promotion_authorized": False,
        "input_hash": sha256_json(model),
    }
    result["result_hash"] = sha256_json(result)
    return result
