from __future__ import annotations

import re
from typing import Any

from consultant_core import sha256_json
from complexity_engine.ontology import validate_model_definition


def _starts(value: Any, prefix: str) -> bool:
    return str(value or "").upper().startswith(prefix)


def _links(record: dict[str, Any]) -> list[str]:
    return [str(x) for x in record.get("evidence_links") or []]


def _has_link(record: dict[str, Any], prefix: str) -> bool:
    return any(x.upper().startswith(prefix) for x in _links(record))


def _decision_valid(record: Any, *, require_observation: bool = False, require_experiment: bool = False, require_sample: bool = False) -> bool:
    if not isinstance(record, dict) or not _starts(record.get("decision_id"), "DEC-"):
        return False
    if str(record.get("state") or "").upper() not in {"PASS", "DISTINCT", "PRESERVED", "SUPPORTED", "CONDITIONAL_PASS"}:
        return False
    if require_observation and not (_has_link(record, "OBS-") or _has_link(record, "AM-")):
        return False
    if require_experiment and not _has_link(record, "EXP-"):
        return False
    if require_sample and not _has_link(record, "CS-"):
        return False
    return True


def _hedonic_vector_valid(record: Any) -> bool:
    if not isinstance(record, dict):
        return False
    if str(record.get("state") or "").upper() not in {
        "OBSERVED_VECTOR_RECORDED",
        "CODED_HEDONIC_VECTOR_RECORDED",
        "PANEL_VECTOR_RECORDED",
    }:
        return False
    obs = [str(x) for x in record.get("observation_ids") or []]
    return bool(obs) and all(x.upper().startswith("OBS-") for x in obs)


def _replicate_builds_valid(records: list[Any]) -> bool:
    ids = [str(x.get("batch_id") or "") for x in records if isinstance(x, dict)]
    return len(ids) >= 2 and len(set(ids)) == len(ids) and all(x.upper().startswith("PB-") for x in ids)


def _lineage_valid(record: Any, model: dict[str, Any]) -> bool:
    if not isinstance(record, dict) or not _starts(record.get("lineage_id"), "LIN-"):
        return False
    if str(record.get("model_id") or "") != str(model.get("model_id") or ""):
        return False
    return bool(re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", str(record.get("version") or "")))


def evaluate_model_admission(payload: dict[str, Any]) -> dict[str, Any]:
    """Evaluate design and empirical admission profiles without granting canonical authority.

    The local consultant may say that an evidence profile is complete enough to be a
    review candidate. It may never promote the model, mutate formula truth, or issue
    a physical claim. Those actions require the real repository, a verified canary,
    and Sol review.
    """
    model = payload.get("model") or {}
    ontology = validate_model_definition(model)
    causal = payload.get("causal_experiment") or {}
    nonredundancy = payload.get("portfolio_nonredundancy") or {}
    physical = list(payload.get("physical_decisions") or [])
    replicates = list(payload.get("replicate_builds") or [])
    hedonic = payload.get("hedonic_evidence")
    safety = payload.get("physical_chemistry_and_safety") or {}
    dynamic = list(payload.get("temporal_spatial_matrix_decisions") or [])

    causal_state = str(causal.get("state") or "").upper()
    causal_design_valid = causal_state in {"PASS_FOR_DESIGN", "PASS_EMPIRICAL", "CONDITIONAL_EMPIRICAL"}
    causal_empirical_valid = causal_state in {"PASS_EMPIRICAL", "CONDITIONAL_EMPIRICAL"}
    structural_distinct = str(nonredundancy.get("state") or "").upper() in {"STRUCTURALLY_DISTINCT", "DISTINCT", "PASS"}
    portfolio_decision_valid = structural_distinct and _starts(nonredundancy.get("decision_id"), "DEC-")

    gates = {
        "M0_DEFINITION": ontology["state"] == "PASS",
        "M1_PROVENANCE": bool(model.get("source_refs")),
        "M2_CAUSAL_IDENTIFIABILITY": causal_design_valid,
        "M3_STRUCTURAL_NOVELTY": structural_distinct,
        "M4_PERCEPTUAL_DISTINCTION": bool(physical) and all(
            _decision_valid(x, require_observation=True, require_experiment=True, require_sample=True)
            for x in physical
        ),
        "M5_IDENTITY_PRESERVATION": _decision_valid(
            payload.get("identity_preservation_decision"), require_observation=True
        ),
        "M6_HEDONIC_EVIDENCE": _hedonic_vector_valid(hedonic),
        "M7_DYNAMIC_ROBUSTNESS": bool(dynamic) and all(
            _decision_valid(x, require_observation=True) for x in dynamic
        ),
        "M8_PORTFOLIO_NONREDUNDANCY": portfolio_decision_valid,
        "M9_REPLICATE_BUILD_RESILIENCE": _replicate_builds_valid(replicates),
        "M10_PHYSICAL_CHEMISTRY_SAFETY": (
            isinstance(safety, dict)
            and str(safety.get("state") or "").upper() == "PASS"
            and _starts(safety.get("decision_id"), "DEC-")
            and (_has_link(safety, "AM-") or _has_link(safety, "OBS-"))
        ),
        "M11_CANONICAL_LINEAGE": _lineage_valid(payload.get("lineage_record"), model),
    }

    # Design admission intentionally uses computational structural nonredundancy.
    design_gates = all(gates[k] for k in ("M0_DEFINITION", "M1_PROVENANCE", "M2_CAUSAL_IDENTIFIABILITY", "M3_STRUCTURAL_NOVELTY"))
    evidence_profile_complete = all(gates.values()) and causal_empirical_valid
    if evidence_profile_complete:
        state = "CANONICAL_MODEL_ADMISSION_CANDIDATE"
    elif design_gates:
        state = "DESIGN_REGISTRY_ADMITTED"
    else:
        state = "HOLD_OR_REBUILD"

    result = {
        "state": state,
        "model_id": model.get("model_id"),
        "gate_vector": gates,
        "causal_empirical_gate": causal_empirical_valid,
        "failed_gates": [k for k, passed in gates.items() if not passed],
        "evidence_profile_complete": evidence_profile_complete,
        "canonical_promotion_authorized": False,
        "design_registry_admission_authorized": design_gates,
        "formula_mutation_authorized": False,
        "physical_claim_authorized": False,
        "repository_install_state": "BRIDGE_BLOCKED",
        "promotion_requires": [
            "verified Perfume-Chem repository canary",
            "canonical source-byte and schema admission",
            "independent Sol scientific and code review",
            "versioned repository lineage and CI receipt",
        ],
        "boundary": (
            "A new name is not a new model. Design admission, evidence-profile completion, "
            "canonical promotion, and physical claims are separate states."
        ),
        "ontology_result": ontology,
        "input_hash": sha256_json(payload),
    }
    result["result_hash"] = sha256_json(result)
    return result
