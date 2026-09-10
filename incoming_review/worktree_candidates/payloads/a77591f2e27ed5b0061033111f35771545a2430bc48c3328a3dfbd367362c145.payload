from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Any

from consultant_core import sha256_json

_REQUIRED_PREFIXES = {
    "observation_id": "OBS-",
    "sample_id": "CS-",
    "condition_id": "COND-",
    "assessor_id": "ASR-",
    "timepoint_id": "TP-",
    "replicate_id": "REP-",
}


def validate_observation(record: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    for field, prefix in _REQUIRED_PREFIXES.items():
        value = str(record.get(field) or "")
        if not value:
            failures.append(f"{field} is required.")
        elif not value.upper().startswith(prefix):
            failures.append(f"{field} must use {prefix} identity.")

    evidence = str(record.get("evidence_state") or "").upper()
    if evidence != "OBSERVED":
        failures.append("A sensory observation record must be OBSERVED, never PROPOSED, DESIGNED, or inferred.")

    status = str(record.get("value_status") or "").upper()
    if status not in {
        "PRESENT", "NOT_COLLECTED", "NOT_APPLICABLE", "BELOW_DETECTION_LIMIT",
        "BELOW_QUANTIFICATION_LIMIT", "INVALIDATED", "LOST", "WITHHELD_BLIND", "UNKNOWN",
    }:
        failures.append("value_status must be an explicit canonical missingness/value state.")
    if status == "PRESENT" and record.get("value") is None:
        failures.append("PRESENT value_status requires value.")
    if status != "PRESENT" and not record.get("missing_reason"):
        failures.append("A non-present value requires missing_reason.")

    if not record.get("dimension"):
        failures.append("dimension is required.")

    blind = str(record.get("blind_state") or "").upper()
    if blind not in {"LOCKED", "DECODED", "COMPROMISED"}:
        failures.append("blind_state must be LOCKED, DECODED, or COMPROMISED.")
    if blind == "LOCKED" and any(k in record for k in ("formula_id", "true_origin", "decode_label")):
        failures.append("A locked evaluator observation may not contain true sample origin.")

    state = "PASS" if not failures else "REJECTED"
    result = {
        "state": state,
        "observation_id": record.get("observation_id"),
        "evidence_state": evidence or None,
        "failures": failures,
        "broad_appeal_claim_authorized": False,
        "input_hash": sha256_json(record),
    }
    result["result_hash"] = sha256_json(result)
    return result


def summarize_observations(
    records: list[dict[str, Any]],
    *,
    experiment_mode: str,
    population_definition: dict[str, Any] | None = None,
    preregistered_broad_appeal_rule: dict[str, Any] | None = None,
) -> dict[str, Any]:
    valid: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for row in records:
        check = validate_observation(row)
        if check["state"] == "PASS":
            valid.append(row)
        else:
            rejected.append({"observation_id": row.get("observation_id"), "failures": check["failures"]})

    grouped: dict[str, dict[str, dict[str, list[float]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    assessor_ids: set[str] = set()
    samples: set[str] = set()
    for row in valid:
        assessor_ids.add(str(row["assessor_id"]))
        sample = str(row["sample_id"])
        samples.add(sample)
        if str(row.get("value_status")).upper() != "PRESENT":
            continue
        try:
            value = float(row["value"])
        except (TypeError, ValueError):
            continue
        grouped[sample][str(row["dimension"])][str(row["timepoint_id"])].append(value)

    def summarize_sample(by_dimension: dict[str, dict[str, list[float]]]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for dim, by_time in sorted(by_dimension.items()):
            all_values = [v for values in by_time.values() for v in values]
            output[dim] = {
                "median": statistics.median(all_values) if all_values else None,
                "n": len(all_values),
                "timepoints": {
                    tp: {
                        "median": statistics.median(values),
                        "minimum": min(values),
                        "maximum": max(values),
                        "n": len(values),
                    }
                    for tp, values in sorted(by_time.items())
                },
            }
        return output

    sample_profiles = {sample: summarize_sample(by_dim) for sample, by_dim in sorted(grouped.items())}
    if len(sample_profiles) == 1:
        dimensions = next(iter(sample_profiles.values()))
        pooling_state = "SINGLE_SAMPLE_PROFILE"
    elif len(sample_profiles) > 1:
        dimensions = {}
        pooling_state = "WITHHELD_MULTI_SAMPLE"
    else:
        dimensions = {}
        pooling_state = "NO_PRESENT_VALUES"

    mode = str(experiment_mode).upper()
    broad_state = "INSUFFICIENT_EVIDENCE"
    if mode == "TARGET_CONSUMER_PANEL":
        if population_definition and preregistered_broad_appeal_rule and len(assessor_ids) >= 2:
            broad_state = "PANEL_DATA_RECORDED__DECISION_PENDING"
        else:
            broad_state = "HOLD"

    result = {
        "state": "PASS" if valid and not rejected else "PARTIAL" if valid else "REJECTED",
        "experiment_mode": mode,
        "valid_observation_count": len(valid),
        "rejected_observation_count": len(rejected),
        "assessor_count": len(assessor_ids),
        "sample_count": len(samples),
        "pooling_state": pooling_state,
        "dimensions": dimensions,
        "sample_profiles": sample_profiles,
        "rejected": rejected,
        "broad_appeal_state": broad_state,
        "separations": {
            "liking_vs_similarity": "SEPARATE",
            "descriptive_quality_vs_cost": "SEPARATE",
            "fatigue_and_annoyance": "NONCOMPENSATORY_NEGATIVE_TAILS",
            "sample_profiles": "NEVER_POOLED_WITHOUT_AN_EXPLICIT_ANALYSIS_PLAN",
        },
        "boundary": (
            "No arithmetic average across identity, liking, quality, artistry, fatigue, annoyance, and manufacturing is permitted. "
            "Multiple coded samples remain separate unless a preregistered model explicitly estimates a shared effect."
        ),
    }
    result["summary_hash"] = sha256_json(result)
    return result

