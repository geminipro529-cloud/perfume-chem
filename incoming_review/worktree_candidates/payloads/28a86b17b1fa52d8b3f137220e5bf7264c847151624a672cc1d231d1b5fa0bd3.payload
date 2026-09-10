from __future__ import annotations

from typing import Any

from consultant_core import sha256_json


def _normalize_row(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return {
            "domain": row.get("domain") or row.get("Domain"),
            "direction": row.get("direction") or row.get("Artistic direction"),
            "state": row.get("state") or row.get("Current project state"),
            "project_evidence": row.get("project_evidence") or row.get("Project evidence"),
            "missing_piece": row.get("missing_piece") or row.get("Missing piece"),
            "implementation": row.get("implementation") or row.get("Recommended implementation"),
            "priority": row.get("priority") or row.get("Priority"),
            "first_test": row.get("first_test") or row.get("First discriminator"),
        }
    if isinstance(row, (list, tuple)):
        vals = list(row) + [None] * 8
        return {
            "domain": vals[0], "direction": vals[1], "state": vals[2], "project_evidence": vals[3],
            "missing_piece": vals[4], "implementation": vals[5], "priority": vals[6], "first_test": vals[7],
        }
    return {"direction": str(row), "state": "UNKNOWN", "priority": "P3"}


def propose_missing_directions(atlas: list[Any], *, limit: int = 20) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    state_markers = ("NOT FOUND", "MISSING", "EVIDENCE GAP", "PARTIAL", "CONCEPT ONLY", "TEST INFRASTRUCTURE ONLY", "TECHNIQUE ONLY")
    priority_rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    for raw in atlas:
        row = _normalize_row(raw)
        state = str(row.get("state") or "").upper()
        if not any(marker in state for marker in state_markers):
            continue
        priority = str(row.get("priority") or "P3").upper()
        gap_kind = (
            "MISSING_FORMAL_MODEL" if "NOT FOUND" in state or "MISSING" in state
            else "EVIDENCE_OR_CALIBRATION_GAP" if "EVIDENCE GAP" in state or "PARTIAL" in state
            else "UNDERFORMALIZED_DIRECTION"
        )
        candidates.append({**row, "priority": priority, "gap_kind": gap_kind})

    candidates.sort(key=lambda r: (priority_rank.get(str(r.get("priority")), 9), str(r.get("domain")), str(r.get("direction"))))
    chosen = candidates[: max(0, limit)]
    result = {
        "state": "CANDIDATES_FOUND" if chosen else "NO_CANDIDATES_IN_SCOPE",
        "candidate_count": len(chosen),
        "total_gap_directions": len(candidates),
        "candidates": chosen,
        "generation_rule": "Generate model briefs from empty or weak morphology cells before generating full formulas.",
        "global_exhaustiveness_claim": False,
    }
    result["result_hash"] = sha256_json(result)
    return result


def evaluate_research_saturation(log: dict[str, Any]) -> dict[str, Any]:
    rounds = list(log.get("rounds") or [])
    last_two = rounds[-2:] if len(rounds) >= 2 else []
    zero_high_priority = len(last_two) == 2 and all(int(r.get("new_p0_p1_gaps", 0)) == 0 for r in last_two)
    source_classes = {str(x).upper() for x in log.get("source_classes_checked") or []}
    core_classes = {"PROJECT", "PRIMARY", "OFFICIAL_STANDARD"}
    source_coverage = core_classes.issubset(source_classes)

    if zero_high_priority and source_coverage:
        state = "SATURATED_FOR_REVIEWED_SCOPE"
    elif rounds:
        state = "ACTIVE_FRONTIER_REMAINS"
    else:
        state = "NOT_EVALUABLE"

    result = {
        "state": state,
        "scope": log.get("scope"),
        "round_count": len(rounds),
        "last_two_rounds_zero_new_p0_p1": zero_high_priority,
        "source_classes_checked": sorted(source_classes),
        "unresolved_authority_holds": list(log.get("unresolved_authority_holds") or []),
        "global_exhaustiveness_claim": False,
        "stop_rule": (
            "Stop the current desk-research cycle after two successive deduplicated rounds add no new P0/P1 root gap. "
            "Reopen when new sources, physical data, repository state, or target scope appears."
        ),
        "open_frontiers": [
            "physical causal-isolate observations",
            "population-scoped sensory and hedonic data",
            "new source releases and citation neighborhoods",
            "new inventory lots and matrix conditions",
            "repository integration and target-engine qualification",
        ],
    }
    result["result_hash"] = sha256_json(result)
    return result
