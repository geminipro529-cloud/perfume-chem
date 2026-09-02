from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from consultant_core import sha256_json


def validate_nary_interaction(record: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    participants = list(record.get("participants") or [])
    if len(participants) < 3:
        failures.append("An n-ary interaction requires at least three participants.")

    ids = [str(p.get("participant_id") or "") for p in participants]
    if any(not x for x in ids):
        failures.append("Every participant requires participant_id.")
    if len(set(ids)) != len(ids):
        failures.append("Participants must be unique.")

    ratio_total = Decimal("0")
    for p in participants:
        try:
            ratio = Decimal(str(p.get("ratio")))
        except (InvalidOperation, TypeError, ValueError):
            failures.append(f"{p.get('participant_id')}: ratio must be numeric.")
            continue
        if ratio <= 0:
            failures.append(f"{p.get('participant_id')}: ratio must be positive.")
        ratio_total += ratio
        if not p.get("role"):
            failures.append(f"{p.get('participant_id')}: role is required.")
    if participants and abs(ratio_total - Decimal("1")) > Decimal("0.000001"):
        failures.append(f"Participant ratios total {ratio_total}; required total is 1.")

    evidence = str(record.get("evidence_state") or "PROPOSED").upper()
    experiments = list(record.get("experiment_ids") or [])
    decision = record.get("decision_id")
    pair_ids = list(record.get("source_pair_ids") or [])

    evidence_upgrade_rejected = False
    if evidence in {"OBSERVED", "MEASURED", "TRAINED_SENSORY"}:
        if not experiments or not decision:
            evidence_upgrade_rejected = True
            failures.append(
                "Pair records cannot be composed into n-ary empirical evidence; an exact n-ary experiment and Decision are required."
            )
        if pair_ids and not record.get("nary_observation_ids"):
            evidence_upgrade_rejected = True
            failures.append("Source pair IDs are hypotheses or priors, not an n-ary observation.")

    if evidence_upgrade_rejected:
        state = "REJECTED_EVIDENCE_UPGRADE"
    elif failures:
        state = "REBUILD"
    elif evidence in {"PROPOSED", "DESIGNED", "SOURCE_SUPPORTED_HYPOTHESIS", "NOT_RUN"}:
        state = "DESIGN_VALID"
    else:
        state = "EMPIRICAL_RECORD_VALID"

    result = {
        "state": state,
        "interaction_id": record.get("interaction_id"),
        "arity": len(participants),
        "ratio_total": str(ratio_total),
        "effect_type": record.get("effect_type"),
        "evidence_state": evidence,
        "source_pair_count": len(pair_ids),
        "pairwise_inference_authorized": False,
        "failures": failures,
        "formula_mutation_authorized": False,
        "boundary": "Higher-order effects require higher-order interventions; pair scores are never multiplied into authority.",
        "input_hash": sha256_json(record),
    }
    result["result_hash"] = sha256_json(result)
    return result
