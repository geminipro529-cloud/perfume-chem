from __future__ import annotations

import re
import statistics
from collections import defaultdict
from typing import Any

from consultant_core import sha256_json


def _time_key(value: str) -> tuple[int, str]:
    nums = re.findall(r"\d+", str(value))
    return (int(nums[-1]) if nums else 10**9, str(value))


def summarize_temporal_dominance(observations: list[dict[str, Any]]) -> dict[str, Any]:
    invalid = [o for o in observations if str(o.get("evidence_state") or "").upper() != "OBSERVED"]
    valid = [o for o in observations if o not in invalid and o.get("dominant_system") and o.get("timepoint_id")]
    valid.sort(key=lambda x: _time_key(str(x["timepoint_id"])))
    sequence = [str(x["dominant_system"]) for x in valid]
    switches = [
        {
            "from": sequence[i - 1],
            "to": sequence[i],
            "at_timepoint": valid[i]["timepoint_id"],
        }
        for i in range(1, len(sequence))
        if sequence[i] != sequence[i - 1]
    ]
    result = {
        "state": "OBSERVED_SUMMARY" if valid and not invalid else "PARTIAL" if valid else "INSUFFICIENT_EVIDENCE",
        "observation_count": len(valid),
        "invalid_count": len(invalid),
        "dominance_sequence": [
            {"timepoint_id": row["timepoint_id"], "dominant_system": row["dominant_system"]}
            for row in valid
        ],
        "switch_count": len(switches),
        "switches": switches,
        "recurrence_candidates": sorted({s for i, s in enumerate(sequence) if s in sequence[:i] and sequence[i - 1] != s}),
        "boundary": "This summarizes recorded dominance. Missing timepoints are not interpolated and designed time stories are not observations.",
    }
    result["result_hash"] = sha256_json(result)
    return result


def summarize_spatial_topology(observations: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [
        o for o in observations
        if str(o.get("evidence_state") or "").upper() == "OBSERVED"
        and o.get("distance_m") is not None and o.get("identity")
    ]
    distances = sorted({float(o["distance_m"]) for o in valid})
    by_distance: dict[str, list[str]] = defaultdict(list)
    for row in valid:
        by_distance[f"{float(row['distance_m']):.6g}"].append(str(row["identity"]))
    if len(distances) < 2:
        state = "INSUFFICIENT_GEOMETRY"
    elif len({x for vals in by_distance.values() for x in vals}) > 1:
        state = "DISTANCE_DEPENDENT_PROFILE_OBSERVED"
    else:
        state = "HOMOGENEOUS_PROFILE_OBSERVED"
    result = {
        "state": state,
        "distance_count": len(distances),
        "distances_m": distances,
        "identity_by_distance": dict(sorted(by_distance.items(), key=lambda x: float(x[0]))),
        "spatial_identity_change": state == "DISTANCE_DEPENDENT_PROFILE_OBSERVED",
        "instrumental_projection_claim": "NOT ESTABLISHED",
        "boundary": "Near/far identity observations are not an instrumental plume measurement and do not generalize beyond the tested geometry.",
    }
    result["result_hash"] = sha256_json(result)
    return result


def evaluate_matrix_transfer(conditions: list[dict[str, Any]]) -> dict[str, Any]:
    hashes = {str(x.get("formula_hash") or "") for x in conditions if x.get("formula_hash")}
    matrices = {str(x.get("matrix") or "") for x in conditions if x.get("matrix")}
    if len(hashes) != 1:
        state = "REBUILD_UNMATCHED_FORMULA"
    elif len(matrices) < 2:
        state = "INSUFFICIENT_MATRIX_CONTRAST"
    elif not all(x.get("decision") for x in conditions):
        state = "HOLD_MISSING_DECISIONS"
    else:
        state = "MATCHED_TRANSFER_EVIDENCE_RECORDED"
    result = {
        "state": state,
        "condition_count": len(conditions),
        "formula_hashes": sorted(hashes),
        "matrices": sorted(matrices),
        "decisions": [x.get("decision") for x in conditions],
        "universal_transfer_authorized": False,
        "boundary": "A matrix comparison is valid only for a matched formula and declared conditions.",
    }
    result["result_hash"] = sha256_json(result)
    return result


def check_applicability(*, model_domain: dict[str, Any], query: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    matched: list[str] = []
    for key, qvalue in query.items():
        if key not in model_domain:
            failures.append(f"{key}: model domain is silent.")
            continue
        domain = model_domain[key]
        if isinstance(domain, list):
            if len(domain) == 2 and all(isinstance(x, (int, float)) for x in domain) and isinstance(qvalue, (int, float)):
                if domain[0] <= qvalue <= domain[1]:
                    matched.append(key)
                else:
                    failures.append(f"{key}: {qvalue} is outside [{domain[0]}, {domain[1]}].")
            elif qvalue in domain:
                matched.append(key)
            else:
                failures.append(f"{key}: {qvalue!r} is outside enumerated domain.")
        elif isinstance(domain, dict) and {"minimum", "maximum"}.issubset(domain):
            if isinstance(qvalue, (int, float)) and domain["minimum"] <= qvalue <= domain["maximum"]:
                matched.append(key)
            else:
                failures.append(f"{key}: {qvalue!r} is outside numeric domain.")
        elif qvalue == domain:
            matched.append(key)
        else:
            failures.append(f"{key}: {qvalue!r} does not match {domain!r}.")
    result = {
        "state": "WITHIN_DOMAIN" if not failures else "ABSTAIN_OUTSIDE_DOMAIN",
        "matched_fields": sorted(matched),
        "failures": failures,
        "prediction_authorized": not failures,
        "boundary": "Applicability is scoped to declared matrix, concentration, method, population, and condition ranges.",
    }
    result["result_hash"] = sha256_json(result)
    return result


def summarize_assessor_heterogeneity(observations: list[dict[str, Any]], *, dimension: str) -> dict[str, Any]:
    by_sample: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in observations:
        if str(row.get("evidence_state") or "").upper() != "OBSERVED" or row.get("dimension") != dimension:
            continue
        if row.get("value_status") != "PRESENT":
            continue
        try:
            sample = str(row.get("sample_id") or "UNSCOPED_SAMPLE")
            by_sample[sample][str(row["assessor_id"])].append(float(row["value"]))
        except (KeyError, TypeError, ValueError):
            continue
    sample_medians = {
        sample: {assessor: statistics.median(values) for assessor, values in by_assessor.items() if values}
        for sample, by_assessor in by_sample.items()
    }
    sample_ranges = {
        sample: (max(values.values()) - min(values.values())) if len(values) >= 2 else None
        for sample, values in sample_medians.items()
    }
    informative_samples = [sample for sample, values in sample_medians.items() if len(values) >= 2]
    if len(sample_medians) > 1 and informative_samples:
        state = "HETEROGENEITY_RECORDED_BY_SAMPLE"
        assessor_medians: dict[str, float] = {}
        overall_range = None
    elif len(sample_medians) == 1 and informative_samples:
        state = "HETEROGENEITY_RECORDED"
        only = next(iter(sample_medians))
        assessor_medians = sample_medians[only]
        overall_range = sample_ranges[only]
    else:
        state = "INSUFFICIENT_ASSESSORS"
        assessor_medians = next(iter(sample_medians.values()), {}) if len(sample_medians) == 1 else {}
        overall_range = None
    result = {
        "state": state,
        "dimension": dimension,
        "assessor_medians": assessor_medians,
        "between_assessor_range": overall_range,
        "sample_assessor_medians": sample_medians,
        "between_assessor_range_by_sample": sample_ranges,
        "observations_overwritten": 0,
        "pooled_across_samples": False,
        "boundary": "Assessor profiles may explain variation but never overwrite atomic observations or pool distinct samples silently.",
    }
    result["result_hash"] = sha256_json(result)
    return result


def evaluate_resource_profile(profile: dict[str, Any]) -> dict[str, Any]:
    required = ["vials", "total_material_ul", "pipetting_steps", "maturation_days", "assessor_sessions"]
    missing = [k for k in required if profile.get(k) is None]
    burdens = {k: profile.get(k) for k in required}
    result = {
        "state": "COMPLETE_PROFILE" if not missing else "HOLD_MISSING_RESOURCE_FIELDS",
        "missing": missing,
        "burdens": burdens,
        "target_rewrite_authorized": False,
        "boundary": "Resource burden may rank experiments or create derivative edits; it may not redefine the target identity.",
    }
    result["result_hash"] = sha256_json(result)
    return result



def summarize_adaptation_reemergence(observations: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize assessor-specific adaptation and recovery without inventing a universal threshold."""
    aliases = {
        "BASELINE": "BASELINE",
        "PRE_EXPOSURE": "BASELINE",
        "PRE": "BASELINE",
        "POST_EXPOSURE": "POST_EXPOSURE",
        "ADAPTED": "POST_EXPOSURE",
        "POST": "POST_EXPOSURE",
        "RECOVERY": "RECOVERY",
        "POST_RECOVERY": "RECOVERY",
    }
    grouped: dict[tuple[str, str, str], dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    invalid_count = 0
    for row in observations:
        if str(row.get("evidence_state") or "").upper() != "OBSERVED":
            invalid_count += 1
            continue
        assessor = str(row.get("assessor_id") or "")
        sample = str(row.get("sample_id") or "")
        identity = str(row.get("identity") or row.get("dimension") or "")
        phase = aliases.get(str(row.get("phase") or "").upper())
        if not assessor.startswith("ASR-") or not sample.startswith("CS-") or not identity or phase is None:
            invalid_count += 1
            continue
        try:
            value = float(row["value"])
        except (KeyError, TypeError, ValueError):
            invalid_count += 1
            continue
        grouped[(assessor, sample, identity)][phase].append(value)

    complete: list[dict[str, Any]] = []
    for (assessor, sample, identity), phases in sorted(grouped.items()):
        if not all(phases.get(x) for x in ("BASELINE", "POST_EXPOSURE", "RECOVERY")):
            continue
        baseline = float(statistics.median(phases["BASELINE"]))
        post = float(statistics.median(phases["POST_EXPOSURE"]))
        recovery = float(statistics.median(phases["RECOVERY"]))
        complete.append({
            "assessor_id": assessor,
            "sample_id": sample,
            "identity": identity,
            "baseline": baseline,
            "post_exposure": post,
            "recovery": recovery,
            "baseline_to_post_delta": post - baseline,
            "post_to_recovery_delta": recovery - post,
            "recovery_minus_baseline": recovery - baseline,
            "directional_adaptation_candidate": post < baseline,
            "directional_reemergence_candidate": post < baseline and recovery > post,
        })

    reemergence_count = sum(bool(x["directional_reemergence_candidate"]) for x in complete)
    if not complete:
        state = "INSUFFICIENT_EVIDENCE"
    elif invalid_count:
        state = "PARTIAL_DIRECTIONAL_SUMMARY"
    else:
        state = "OBSERVED_DIRECTIONAL_SUMMARY"
    result = {
        "state": state,
        "complete_assessor_sample_identity_triplets": len(complete),
        "invalid_or_nonobserved_count": invalid_count,
        "reemergence_candidate_count": reemergence_count,
        "records": complete,
        "universal_reemergence_claim_authorized": False,
        "causal_reemergence_claim_authorized": False,
        "boundary": (
            "Directional decline and recovery are assessor-, sample-, identity-, exposure-, and protocol-scoped. "
            "A universal adaptation or reemergence threshold is not inferred."
        ),
    }
    result["result_hash"] = sha256_json(result)
    return result


def evaluate_context_effect(observations: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare blind-odor and contextual presentation while preserving odor/context separation."""
    valid: list[dict[str, Any]] = []
    invalid_count = 0
    for row in observations:
        if str(row.get("evidence_state") or "").upper() != "OBSERVED":
            invalid_count += 1
            continue
        required = ("formula_hash", "assessor_id", "dimension", "context_condition", "value")
        if any(row.get(key) in (None, "") for key in required):
            invalid_count += 1
            continue
        try:
            value = float(row["value"])
        except (TypeError, ValueError):
            invalid_count += 1
            continue
        normalized = dict(row)
        normalized["value"] = value
        normalized["context_condition"] = str(row["context_condition"]).upper()
        valid.append(normalized)

    hashes = {str(row["formula_hash"]) for row in valid}
    if len(hashes) > 1:
        state = "REBUILD_UNMATCHED_FORMULA"
        comparisons: list[dict[str, Any]] = []
    else:
        grouped: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
        for row in valid:
            grouped[(str(row["assessor_id"]), str(row["dimension"]))][str(row["context_condition"])].append(float(row["value"]))
        comparisons = []
        for (assessor, dimension), conditions in sorted(grouped.items()):
            blind = conditions.get("BLIND_ODOR")
            if not blind:
                continue
            blind_median = float(statistics.median(blind))
            for condition, values in sorted(conditions.items()):
                if condition == "BLIND_ODOR" or not values:
                    continue
                context_median = float(statistics.median(values))
                comparisons.append({
                    "assessor_id": assessor,
                    "dimension": dimension,
                    "context_condition": condition,
                    "blind_median": blind_median,
                    "context_median": context_median,
                    "context_minus_blind": context_median - blind_median,
                })
        has_blind = any(str(row["context_condition"]) == "BLIND_ODOR" for row in valid)
        if not valid:
            state = "INSUFFICIENT_EVIDENCE"
        elif not has_blind:
            state = "HOLD_NO_BLIND_ODOR_ANCHOR"
        elif comparisons:
            state = "SCOPED_CONTEXT_ASSOCIATION_RECORDED" if not invalid_count else "PARTIAL_CONTEXT_ASSOCIATION_RECORDED"
        else:
            state = "INSUFFICIENT_PAIRED_CONTEXT_CONTRAST"

    result = {
        "state": state,
        "formula_hashes": sorted(hashes),
        "valid_observation_count": len(valid),
        "invalid_or_nonobserved_count": invalid_count,
        "paired_comparison_count": len(comparisons),
        "comparisons": comparisons,
        "odor_property_rewrite_authorized": False,
        "population_generalization_authorized": False,
        "boundary": (
            "Context, naming, color, sound, packaging, and narrative effects remain presentation- and population-scoped. "
            "They do not rewrite the blind odor record or establish intrinsic perfume quality."
        ),
    }
    result["result_hash"] = sha256_json(result)
    return result
