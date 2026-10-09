"""Offline paired subtype-manifest ablation, never a sensory-quality benchmark.

Run in its own process with ``python -m engine.research.subtype_benchmark``.
It prints one JSON artifact (or exclusively creates an explicit output artifact)
and restores the active manifest. Formula and inventory inputs are never edited.
Both arms use the same current code, inventory and literature. This is not a
replay of an old installation and must not be presented as one.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import socket
import sys
import time
from contextlib import contextmanager
from dataclasses import asdict, fields
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Iterator
from unittest.mock import patch

from engine.formulation_intelligence import architecture_bridge, subtype_research
from engine.formulation_intelligence import formula_solver as solver
from engine.formulation_intelligence.formula_critic import critique_formula
from engine.formulation_intelligence.detection_pass import solver_formula
from engine.formulation_intelligence.formula_design_runtime import design_formula
from engine.formulation_intelligence.literature_knowledge import retrieve_formulation_knowledge
from engine.formulation_intelligence.material_capability_index import (
    MaterialCapabilityIndex,
    build_material_capability_index,
)
from engine.formulation_intelligence.semantic_brief_adapter import SemanticBrief, SemanticRole
from engine.formulation_intelligence.source_review import source_record_hash
from engine.research.composition_planner import Choice, _formula_rows

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "tests/fixtures/subtype_comparison_v1.json"
ARCHITECTURE_CORPUS = ROOT / "tests/fixtures/architecture_comparison_v1.json"
ARCHITECTURE_CORPUS_V2 = ROOT / "tests/fixtures/architecture_comparison_v2.json"
ARCHITECTURE_CORPUS_V3 = ROOT / "tests/fixtures/architecture_comparison_v3.json"
ARCHITECTURE_CORPUS_V4 = ROOT / "tests/fixtures/architecture_comparison_v4.json"
ARCHITECTURE_CORPUS_V5 = ROOT / "tests/fixtures/architecture_comparison_v5.json"
_V5_CORPUS_SHA256 = "573bb9ebe737e958c0ecf69395a7e090608fbe6f31f91b8e6dba8b733d29870e"
_V3_CORPUS_SHA256 = "999810479674a7f7f041def9e992c4bdfc88a9eda20f7e6b4700612f75dfe34c"
_V4_CORPUS_SHA256 = "4e3e24bd12fa968d60e35576f06c1729f72f528794fff7f4ed31ed44db20b79f"
_V4_CONFIGURATION = {
    "max_materials": 12, "liquid_concentrate_ul": "6000", "design_mode": "DEEP_COMPOSE",
    "control_variants": 1, "comparison_variants": 3, "network_allowed": False,
    "reverse_replay_required": True, "ranking_allowed": False,
    "adapter_schema": "source-bound-architecture-adapters-v4",
    "purpose": "Chypre and citrus-wood option coverage with verified empty-pool holds; not sensory evidence",
}
_V5_CONFIGURATION = {
    **_V4_CONFIGURATION, "adapter_schema": "source-bound-architecture-adapters-v5",
    "purpose": "Remaining subtype architecture operation coverage; all verified holds and duplicates separate from viable coverage",
}
_V5_OUTCOMES = ["VIABLE_COMPARISON", "EMPTY_ADMISSIBLE_POOL", "BOUNDED_SOLVER_WITHHOLD",
                "DUPLICATE_PHYSICAL_COMPOSITION", "CRITIC_WITHHOLD"]
AUTHORITY = {
    "release_authority": False,
    "safety_authority": False,
    "compounding_authority": False,
    "evidence_admission_authorized": False,
}


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _snapshot() -> dict[str, str]:
    paths = {CORPUS, ROOT / "inventory.txt"}
    for relative, pattern in (
        ("engine", "*.py"), ("data/formulation_knowledge", "*.json"),
        ("data/materials", "*.yaml"), ("data/governance", "*inventory*.json"),
        ("data/inventory_receipts", "*.json"),
        ("formulas", "*"),
    ):
        paths.update(p for p in (ROOT / relative).rglob(pattern) if p.is_file())
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths)}


@contextmanager
def _arm(path: Path) -> Iterator[None]:
    # This diagnostic is deliberately single-process and sequential. A mutable
    # registry override must never be used in a shared server request handler.
    previous = subtype_research.SUBTYPE_PATH
    subtype_research.SUBTYPE_PATH = path
    try:
        yield
    finally:
        subtype_research.SUBTYPE_PATH = previous


def _forbid_network(*args: Any, **kwargs: Any) -> None:
    raise RuntimeError("BENCHMARK_NETWORK_FORBIDDEN")


def _design(case: dict[str, Any]) -> dict[str, Any]:
    return design_formula(
        formula_name=f"Subtype comparison {case['case_id']}", idea=case["brief"],
        design_mode="DEEP_COMPOSE", variant_count=1, max_materials=12,
        liquid_concentrate_ul_decimal="6000", previous_stock_ids=(),
        conversation_context=(), comparison_evidence="DOCUMENT_ONLY",
        must_avoid=tuple(case["must_avoid"]),
    )


def audit_answer(result: dict[str, Any], required_avoids: list[str]) -> dict[str, Any]:
    """Separate composition, role assignment, advice and authority receipts."""
    knowledge = result.get("formulation_knowledge", {})
    cards = knowledge.get("subtype_context", {}).get("cards", [])
    sources = {s["source_id"]: s for s in knowledge.get("sources", [])}
    allowed = {r["source_id"] for r in knowledge.get("source_reviews", []) if r["allowed"]}
    bindings = [b for c in cards for b in c["source_bindings"]]
    closure = all(b["source_id"] in allowed and b["source_id"] in sources
                  and source_record_hash(sources[b["source_id"]]) == b["source_record_sha256"]
                  for b in bindings)
    formula = result.get("optimized_formula")
    rows = (formula or {}).get("rows", [])
    row_fields = ("row_id", "slot", "material", "identity_name", "stock_id", "stock_label",
                  "stock_fraction_decimal", "fraction_basis", "carrier", "amount_decimal",
                  "amount_unit", "operation", "stock_binding_state", "active_quantity_state")
    physical = [{k: r.get(k) for k in row_fields} for r in rows]
    roles = {k: result.get("composition_plan", {}).get(k)
             for k in ("roles_requested", "roles_filled")}
    constraints = result.get("request_interpretation", {}).get("must_avoid", [])
    return {
        "status": result.get("status"), "request_sha256": result.get("request_sha256"),
        "formula_available": formula is not None,
        "complete_formula_sha256": _hash(formula), "physical_rows_sha256": _hash(physical),
        "role_assignment_sha256": _hash(roles), "physical_rows": physical,
        "row_count": len(rows), "inventory": result.get("inventory", {}),
        "subtype_ids": [c["subtype_id"] for c in cards], "advice_sha256": _hash(cards),
        "advice_source_closure": closure,
        "explicit_avoids_preserved": all(a.casefold() in {str(v).casefold() for v in constraints}
                                         for a in required_avoids),
        "comparison_contracts_present": all(
            c["status"] == "UNTESTED_SUBTYPE_HYPOTHESIS" and c["identity_limits"]
            and c["negative_space"] and all(c["comparison"].values()) for c in cards
        ),
        "authority_safe": all(result.get(k) is False for k in AUTHORITY)
        and all(result.get(k) is False for k in
                ("formula_modified", "inventory_modified", "physical_compounding_performed")),
        "sensory_scores_absent": all(result.get(k) is None for k in
                                     ("pleasantness", "personal_liking", "population_liking", "beauty_score")),
        "network_used": knowledge.get("network_used"),
    }


def compare_answers(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    return {
        "complete_formula_changed": before["complete_formula_sha256"] != after["complete_formula_sha256"],
        "physical_rows_changed": before["physical_rows_sha256"] != after["physical_rows_sha256"],
        "role_assignment_changed": before["role_assignment_sha256"] != after["role_assignment_sha256"],
        "advice_changed": before["advice_sha256"] != after["advice_sha256"],
        "new_subtype_ids": sorted(set(after["subtype_ids"]) - set(before["subtype_ids"])),
        "sensory_improvement": "NOT_TESTED",
    }


def run_comparison() -> dict[str, Any]:
    corpus = json.loads(CORPUS.read_bytes())
    if corpus.get("schema_version") != "subtype-comparison-corpus-v1" or not corpus.get("frozen_before_execution"):
        raise ValueError("unfrozen or invalid benchmark corpus")
    cases = corpus["cases"]
    if len(cases) != 12 or len({c["case_id"] for c in cases}) != 12:
        raise ValueError("comparison corpus changed; review a new protocol")
    opening = _snapshot()
    arms = {"IMMUTABLE_V2": subtype_research.V2_PATH,
            "CURRENT_V3": subtype_research.V2_PATH.with_name("subtype_research_v3.json")}
    receipts: dict[str, dict[str, Any]] = {c["case_id"]: {} for c in cases}
    timings: dict[str, list[float]] = {name: [] for name in arms}
    repeat_equal = True
    with patch.object(socket, "create_connection", _forbid_network), \
            patch.object(socket.socket, "connect", _forbid_network), \
            patch.object(socket.socket, "connect_ex", _forbid_network), \
            patch.object(socket, "getaddrinfo", _forbid_network):
        for name, path in arms.items():
            with _arm(path):
                for case in cases:
                    start = time.perf_counter()
                    receipt = audit_answer(_design(case), case["must_avoid"])
                    timings[name].append(time.perf_counter() - start)
                    receipts[case["case_id"]][name] = receipt
        # Reverse both arm and case order to detect order/cache contamination.
        for name, path in reversed(list(arms.items())):
            with _arm(path):
                for case in reversed(cases):
                    repeat_equal &= audit_answer(_design(case), case["must_avoid"]) == receipts[case["case_id"]][name]
    closing = _snapshot()
    changed = sorted(k for k in opening.keys() | closing.keys() if opening.get(k) != closing.get(k))
    rows = [{"case_id": c["case_id"], "brief": c["brief"], "review_topics": c["review_topics"],
             "arms": receipts[c["case_id"]],
             "comparison": compare_answers(receipts[c["case_id"]]["IMMUTABLE_V2"],
                                           receipts[c["case_id"]]["CURRENT_V3"])} for c in cases]
    all_receipts = [r for pair in receipts.values() for r in pair.values()]
    same_inventory = len({_hash(r["inventory"]) for r in all_receipts}) == 1
    safe = all(r["network_used"] is False for r in all_receipts) and all(r[k] for r in all_receipts for k in
               ("advice_source_closure", "explicit_avoids_preserved", "comparison_contracts_present",
                "authority_safe", "sensory_scores_absent"))
    return {
        "schema_version": "subtype-paired-comparison-result-v1",
        "scope": corpus["scope"], "status": "PASS" if safe and not changed and repeat_equal and same_inventory else "FAIL",
        "corpus_sha256": hashlib.sha256(CORPUS.read_bytes()).hexdigest(),
        "configuration": corpus["configuration"],
        "arm_manifest_sha256": {name: hashlib.sha256(p.read_bytes()).hexdigest() for name, p in arms.items()},
        "opening_snapshot_sha256": _hash(opening), "closing_snapshot_sha256": _hash(closing),
        "snapshot_file_count": len(opening), "changed_paths": changed,
        "same_inventory_in_both_arms": same_inventory, "reverse_order_repeat_identical": repeat_equal,
        "case_count": len(rows), "design_calls": len(rows) * 4,
        "composition_changes": sum(r["comparison"]["complete_formula_changed"] for r in rows),
        "physical_row_changes": sum(r["comparison"]["physical_rows_changed"] for r in rows),
        "role_changes": sum(r["comparison"]["role_assignment_changed"] for r in rows),
        "advice_changes": sum(r["comparison"]["advice_changed"] for r in rows),
        "formula_available_count": {name: sum(receipts[c["case_id"]][name]["formula_available"] for c in cases) for name in arms},
        "warm_p95_seconds": {name: sorted(values[1:])[math.ceil(0.95 * len(values[1:])) - 1] for name, values in timings.items()},
        "first_call_seconds": {name: values[0] for name, values in timings.items()},
        "cases": rows, "network_used": False, "authority": dict(AUTHORITY),
        "limitations": [
            "Paired manifest ablation with common CURRENT literature, code and inventory; not old-system replay.",
            "Additional sourced advice is not empirical proof of improved composition or sensory success.",
            "Twelve frozen diagnostic prompts do not establish all-family or general prompt superiority.",
            "Topics are qualitative audit aids, not a beauty score. All physical and consumer outcomes are NOT_TESTED.",
        ],
    }


def _read_roles(value: Any) -> tuple[SemanticRole, ...]:
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError("missing executable role data")
    required = {f.name for f in fields(SemanticRole)}
    roles = []
    for row in value:
        if not isinstance(row, dict) or set(row) != required:
            raise ValueError("incomplete or unknown executable role fields")
        roles.append(SemanticRole(**{
            **row, "query_terms": tuple(row["query_terms"]),
            "character_weights": tuple(tuple(w) for w in row["character_weights"]),
        }))
    if len({r.role_id for r in roles}) != len(roles):
        raise ValueError("duplicate executable roles")
    # Reject nonfinite data as well as incomplete fields.
    architecture_bridge.role_plan_signature(roles)
    return tuple(roles)


def _campaign_hold_verified(result: dict[str, Any]) -> bool:
    """Require the current canonical hold, not merely a caller's empty result."""
    try:
        raw = result["semantic_brief"]
        interpretation = result["request_interpretation"]
        request = raw["normalized_request"]
        knowledge = retrieve_formulation_knowledge(
            f"{result['formula_name']}; {request}", avoid=tuple(interpretation.get("must_avoid", ())),
        )
        return (
            result.get("status") == "WITHHELD_CAMPAIGN_IDENTITY"
            and result.get("design_variants") == []
            and result.get("initial_formula") is None and result.get("optimized_formula") is None
            and result.get("formula_action") == "NO_CHANGE"
            and "HOLD_EXACT_BRIEF_OR_FORMULA_REQUIRED" in result["reason_codes"]
            and request == interpretation["original_request"]
            and raw["formula_name"] == result["formula_name"]
            and bool(knowledge["subtype_context"]["campaign_identity_holds"])
            and _hash(raw["knowledge_context"]) == _hash(knowledge) == _hash(result["formulation_knowledge"])
            and all(result.get(k) is False for k in (*AUTHORITY, "formula_modified",
                                                    "inventory_modified", "physical_compounding_performed"))
        )
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return False


def _replay_planning(result: dict[str, Any]) -> tuple[bool, tuple[SemanticBrief, ...]]:
    """Replay only the pure bounded planner, not the inventory solver.

    Self-consistent role hashes alone are insufficient: the serialized roles
    must be the registered option applied to the actual unchanged control.
    """
    planning = result.get("architecture_planning")
    if planning is None:
        return _campaign_hold_verified(result), ()
    try:
        raw = result["semantic_brief"]
        if set(raw) != {f.name for f in fields(SemanticBrief)} or raw["architecture_plan"]:
            raise ValueError("missing or non-control semantic brief")
        if _hash(raw["knowledge_context"]) != _hash(result["formulation_knowledge"]):
            raise ValueError("control and output evidence disagree")
        canonical_knowledge = retrieve_formulation_knowledge(
            f"{raw['formula_name']}; {raw['normalized_request']}",
            avoid=tuple(result["request_interpretation"].get("must_avoid", ())),
        )
        if _hash(raw["knowledge_context"]) != _hash(canonical_knowledge):
            raise ValueError("serialized evidence does not match canonical current retrieval")
        control = SemanticBrief(**{**raw, "roles": _read_roles(raw["roles"])})
        maximum = result["effective_material_limit"]
        if planning["max_materials"] != maximum:
            raise ValueError("material ceiling not bound")
        replay = architecture_bridge.derive_architecture_briefs(
            control=control, interpretation=result["request_interpretation"],
            max_materials=maximum, max_architectures=planning["comparison_budget"],
        )
        return _hash(planning) == _hash(replay.receipt), replay.briefs
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return False, ()


def _false_authority(value: Any) -> bool:
    return (
        isinstance(value, dict) and set(value) == set(AUTHORITY)
        and all(value[k] is False for k in AUTHORITY)
    )


def _decimal(value: Any, *, positive: bool = False) -> Decimal:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("physical quantity must be a decimal string")
    number = Decimal(value)
    if not number.is_finite() or number < 0 or (positive and number == 0):
        raise ValueError("invalid physical quantity")
    return number


def _physical_formula(formula: Any, expected_liquid: str | None) -> tuple[bool, list[dict[str, Any]]]:
    """Canonical physical identity and independent conservation; never sensory truth."""
    physical: list[dict[str, Any]] = []
    try:
        rows = formula["rows"]
        if not isinstance(rows, list) or not rows:
            raise ValueError("empty physical formula")
        amounts: dict[str, Decimal] = {}
        identities: dict[str, dict[str, Any]] = {}
        totals = {"uL": Decimal(0), "mg": Decimal(0)}
        for row in rows:
            amount = _decimal(row["amount_decimal"], positive=True)
            fraction = _decimal(row["stock_fraction_decimal"], positive=True)
            if fraction > 1 or not all(isinstance(row[k], str) and row[k] for k in (
                "stock_id", "identity_name", "fraction_basis",
            )):
                raise ValueError("invalid stock identity or fraction")
            unit, operation = row["amount_unit"], row["operation"]
            if (unit, operation) not in {
                ("uL", "DIRECT_ADD"), ("uL", "PREPARED_DILUTION_REQUIRED"), ("mg", "MASS_ADD"),
            }:
                raise ValueError("incompatible dose unit or operation")
            identity = {k: row[k] for k in (
                "stock_id", "identity_name", "fraction_basis", "carrier", "amount_unit", "operation",
            )}
            identity["stock_fraction_decimal"] = format(fraction.normalize(), "f")
            key = _hash(identity)
            identities[key] = identity
            amounts[key] = amounts.get(key, Decimal(0)) + amount
            totals[unit] += amount
        physical = sorted(({
            **identities[key], "amount_decimal": format(amount.normalize(), "f"),
        } for key, amount in amounts.items()), key=_hash)
        declared = formula["separate_totals"]
        if set(declared) != {"liquid_total_ul", "mass_total_mg"}:
            raise ValueError("invalid separate totals")
        valid = (
            totals["uL"] == _decimal(declared["liquid_total_ul"])
            and totals["mg"] == _decimal(declared["mass_total_mg"])
            and (expected_liquid is None or totals["uL"] == _decimal(expected_liquid))
            and formula["basis_state"] == (
                "SEPARATE_LIQUID_AND_SOLID_TOTALS" if totals["mg"] else "LIQUID_STOCK_VOLUME_ONLY"
            )
        )
        return valid, physical
    except (ValueError, InvalidOperation, TypeError, KeyError, AttributeError):
        return False, physical


def _request_matches_case(result: dict[str, Any], case: dict[str, Any] | None, variant_count: int | None) -> bool:
    if case is None:
        return True
    interpretation = result.get("request_interpretation") or {}
    if not all(set(case[key]) <= set(interpretation.get(key, ())) for key in ("must_avoid", "must_preserve")):
        return False
    semantic = result.get("semantic_brief") or {}
    if semantic.get("normalized_request") != case["brief"] or result.get("formula_name") != f"Architecture diagnostic {case['case_id']}":
        return False
    if not result.get("design_variants"):
        return case.get("expected_hold") == "WITHHELD_CAMPAIGN_IDENTITY" and _campaign_hold_verified(result)
    return (
        semantic.get("normalized_request") == case["brief"]
        and result.get("formula_name") == f"Architecture diagnostic {case['case_id']}"
        and result.get("effective_material_limit") == 12
        and (result.get("architecture_planning") or {}).get("comparison_budget") == variant_count - 1
    ) if variant_count is not None else False


def _execution_verified(
    result: dict[str, Any], briefs: tuple[SemanticBrief, ...],
    index: MaterialCapabilityIndex | None, expected_liquid: str | None,
) -> bool:
    """Replay allocation/critique against live stocks; a receipt cannot certify itself.

    The beam search is replayed only for a claimed coverage failure. Ordinary
    successful and duplicate branches need only the deterministic allocation.
    This is a diagnostic, never an extra calculation in normal Formula Studio.
    """
    try:
        if not briefs:
            return not result.get("architecture_attempts")
        index = index or build_material_capability_index()
        interpretation = result["request_interpretation"]
        index = index.with_explicit_materials(tuple(interpretation.get("explicit_materials", ())))
        inputs = result["architecture_execution_inputs"]
        if (set(inputs) != {"schema_version", "liquid_total_ul_decimal", "explicit_quantities",
                            "previous_stock_ids", "effective_inventory_sha256"}
                or inputs["schema_version"] != "architecture-execution-inputs-v1"
                or inputs["effective_inventory_sha256"] != index.effective_inventory_sha256
                or inputs["explicit_quantities"] != interpretation.get("explicit_quantities", [])):
            return False
        total = _decimal(inputs["liquid_total_ul_decimal"], positive=True)
        if total != total.to_integral_value() or total > 100_000 or (
            expected_liquid is not None and total != _decimal(expected_liquid)
        ):
            return False
        if not isinstance(inputs["previous_stock_ids"], list) or not all(
            isinstance(x, str) for x in inputs["previous_stock_ids"]
        ):
            return False
        stocks = {c.stock_id: c for c in index.capabilities}
        returned = {v["variant_id"]: v for v in result["design_variants"]}
        liking = solver._liking_lookup()
        prior: set[str] = set()
        for position, attempt in enumerate(result["architecture_attempts"]):
            brief = briefs[position] if len(briefs) > 1 else briefs[0]
            role_map = {r.role_id: r for r in brief.roles}
            bindings = attempt["assignment_bindings"]
            if not isinstance(bindings, list) or any(set(b) != {"role_id", "stock_id"} for b in bindings):
                return False
            role_ids = [b["role_id"] for b in bindings]
            stock_ids = [b["stock_id"] for b in bindings]
            if (role_ids != attempt["assigned_role_ids"] or len(set(role_ids)) != len(role_ids)
                    or role_ids != [r.role_id for r in brief.roles if r.role_id in role_ids]
                    or any(s not in stocks for s in stock_ids)):
                return False
            receipt = attempt["solver"]
            missing = [r.label for r in brief.roles if r.required and r.role_id not in role_ids]
            if (receipt["schema_version"] != "formula-constraint-solver-receipt-v1"
                    or receipt["selected_stock_ids"] != stock_ids
                    or receipt["assigned_role_count"] != len(bindings)
                    or receipt["role_count"] != len(brief.roles)
                    or receipt["variant_index"] != position
                    or set(receipt["role_fit_diagnostics"]) != set(role_ids)
                    or receipt["missing_roles"] != missing or attempt["missing_roles"] != missing
                    or _hash(receipt["architecture_plan"]) != _hash(brief.architecture_plan)):
                return False
            assignments = tuple(solver.SolvedAssignment(role_map[b["role_id"]], stocks[b["stock_id"]], 0.0, ())
                                for b in bindings)
            signature = hashlib.sha256("|".join(f"{r}:{s}" for r, s in zip(role_ids, stock_ids)).encode()).hexdigest()[:16]
            if attempt["variant_id"] != f"semantic-variant-{position + 1}-{signature}":
                return False
            state = solver._BeamState((), frozenset(), (), 0.0)
            for assigned in assignments:
                role, cap = assigned.role, assigned.capability
                if role.exact_material and cap.stock_id not in {c.stock_id for c in index.exact_matches(role.exact_material)}:
                    return False
                if not solver._allowed(cap, role, state, avoid=interpretation.get("must_avoid", ()),
                                       allow_multiple_musks=solver._allows_multiple_musks(brief.normalized_request, brief.roles),
                                       enforce_own_odor_avoid=bool(brief.architecture_plan.get("operation"))):
                    return False
                groups = state.groups()
                groups[cap.group] = groups.get(cap.group, 0) + 1
                family = solver._family_bucket(cap)
                if family:
                    groups[f"family:{family}"] = groups.get(f"family:{family}", 0) + 1
                state = solver._BeamState((*state.assignments, (role, cap, 0.0)),
                                          state.used_identities | {solver._chemical_identity(cap)},
                                          tuple(sorted(groups.items())), 0.0)
            status = "SOLVED"
            rows: list[dict[str, Any]] = []
            totals = {"liquid_total_ul": "0", "mass_total_mg": "0"}
            holds: list[str] = []
            if missing or len(assignments) < min(6, len(brief.roles)):
                replay = solver.solve_formula(
                    brief=brief, index=index, liquid_total_ul=int(total),
                    explicit_quantities=inputs["explicit_quantities"], avoid=interpretation.get("must_avoid", ()),
                    previous_stock_ids=inputs["previous_stock_ids"],
                    prior_variant_stock_ids=() if brief.architecture_plan else tuple(prior),
                    variant_index=position, beam_width=48,
                )
                if (replay.status != "WITHHELD_CONCEPT_COVERAGE_INCOMPLETE"
                        or replay.variant_id != attempt["variant_id"] or list(replay.missing_roles) != missing):
                    return False
                status = replay.status
            else:
                try:
                    rows, totals, holds = _formula_rows(
                        solver._allocation_choices(
                            assignments,
                            tuple(Choice(solver._role_spec(a.role), a.capability.candidate, 0.0, ()) for a in assignments),
                            int(total), inputs["explicit_quantities"],
                            solver._has_exact_material_count(interpretation),
                        ),
                        liquid_total_ul=int(total), quantities=inputs["explicit_quantities"],
                    )
                except ValueError as exc:
                    status = "WITHHELD_DOSE_ALLOCATION_INFEASIBLE"
                    holds = [f"DOSE_ALLOCATION_INFEASIBLE:{exc}"]
                # Rows carry the solver's liking annotation; replay it from the
                # live lookup rather than trusting the recorded values.
                solver._annotate_liking(rows, assignments, liking)
            if attempt["holds"] != sorted(set(holds)):
                return False
            duplicate = attempt["state"] == "WITHHELD_DUPLICATE_PHYSICAL_COMPOSITION"
            if status != ("SOLVED" if duplicate else attempt["state"]):
                return False
            if rows:
                variant = returned.get(attempt["variant_id"], {})
                # Compare the solver's allocation: the detection pass's recorded
                # dose raises are undone (and checked to conserve the total).
                formula = attempt["suppressed_formula"] if duplicate else solver_formula(variant["formula"])
                # Alternatives are rank diagnostics, not dose/stock authority.
                def trim(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
                    return [{k: v for k, v in row.items() if k != "alternatives_considered"} for row in values]
                if _hash(trim(formula["rows"])) != _hash(trim(rows)) or formula["separate_totals"] != totals:
                    return False
                solved = solver.FormulaSolveResult(status, attempt["variant_id"], assignments,
                                                  tuple(missing), tuple(rows), totals, tuple(holds), receipt)
                critic = critique_formula(brief=brief, solve=solved, interpretation=interpretation,
                                          max_materials=result["effective_material_limit"], liquid_total_ul=int(total)).as_dict()
                if _hash(attempt["suppressed_critic"] if duplicate else variant["critic"]) != _hash(critic):
                    return False
                if not duplicate and _hash(variant["solver"]) != _hash(receipt):
                    return False
            prior.update(stock_ids)
        return True
    except (OSError, ValueError, InvalidOperation, TypeError, KeyError, AttributeError, IndexError):
        return False


def _attempts_verified(
    result: dict[str, Any], expected: tuple[SemanticBrief, ...],
    variants: list[dict[str, Any]], expected_liquid: str | None,
) -> bool:
    """Account for every branch, including physical proof for suppression."""
    try:
        attempts = result.get("architecture_attempts", [])
        if not expected:
            return not attempts and not variants
        count = len(expected) if len(expected) > 1 else 1 + result["architecture_planning"]["comparison_budget"]
        if not isinstance(attempts, list) or len(attempts) != count:
            return False
        ids = [a["variant_id"] for a in attempts]
        if len(set(ids)) != len(ids) or any(not isinstance(i, str) or not i for i in ids):
            return False
        retained = {v["variant_id"]: v for v in variants}
        returned = {v["variant_id"]: v for v in result.get("design_variants", [])}
        if not set(retained) <= set(ids):
            return False
        for i, attempt in enumerate(attempts):
            brief = expected[i] if len(expected) > 1 else expected[0]
            binding = brief.architecture_plan or {"kind": "UNCHANGED_CONTROL_OR_STOCK_ALTERNATIVE"}
            if (
                _hash(attempt["architecture"]) != _hash(binding)
                or attempt["role_count"] != len(brief.roles)
                or attempt["role_plan_sha256"] != architecture_bridge.role_plan_signature(brief.roles)
            ):
                return False
            identity = attempt["variant_id"]
            state = attempt["state"]
            duplicate_fields = {"suppressed_formula", "suppressed_critic",
                                "duplicate_of_variant_id", "physical_composition_sha256"}
            if state != "WITHHELD_DUPLICATE_PHYSICAL_COMPOSITION" and duplicate_fields.intersection(attempt):
                return False
            assigned = attempt["assigned_role_ids"]
            if not isinstance(assigned, list) or len(set(assigned)) != len(assigned) or not set(assigned) <= {r.role_id for r in brief.roles}:
                return False
            if state == "WITHHELD_DUPLICATE_PHYSICAL_COMPOSITION":
                reference_id = attempt["duplicate_of_variant_id"]
                reference = retained.get(reference_id)
                valid, physical = _physical_formula(attempt.get("suppressed_formula"), expected_liquid)
                if (
                    not brief.architecture_plan or identity in retained
                    or reference_id not in ids[:i] or reference is None
                    or not reference["viable_comparison"] or not valid
                    or _hash(physical) != attempt["physical_composition_sha256"]
                    or _hash(physical) != reference["physical_composition_sha256"]
                ):
                    return False
            elif state == "SOLVED":
                if identity not in retained or retained[identity]["role_plan_sha256"] != attempt["role_plan_sha256"]:
                    return False
                expected_binding = brief.architecture_plan or {
                    "kind": "UNCHANGED_CONTROL" if i == 0 else "STOCK_ALTERNATIVE_SAME_ROLE_PLAN",
                }
                if _hash(returned[identity]["architecture"]) != _hash(expected_binding):
                    return False
            elif state in {"WITHHELD_CONCEPT_COVERAGE_INCOMPLETE", "WITHHELD_DOSE_ALLOCATION_INFEASIBLE"}:
                if identity in retained:
                    return False
                if state == "WITHHELD_DOSE_ALLOCATION_INFEASIBLE" and not any(
                    isinstance(reason, str) and reason.startswith("DOSE_ALLOCATION_INFEASIBLE:")
                    for reason in attempt["holds"]
                ):
                    return False
                if state == "WITHHELD_CONCEPT_COVERAGE_INCOMPLETE" and not (
                    attempt["missing_roles"] or len(assigned) < min(6, len(brief.roles))
                ):
                    return False
            else:
                return False
        return True
    except (ValueError, TypeError, KeyError, AttributeError, IndexError):
        return False


def _admissible_role_pool(
    index: MaterialCapabilityIndex, role: SemanticRole, brief: SemanticBrief,
    avoid: list[str],
) -> list[str]:
    """Exhaustive unary admission, not a truncated beam or already-consumed pool."""
    empty = solver._BeamState((), frozenset(), (), 0.0)
    eligible = []
    for cap in index.capabilities:
        if role.exact_material and cap.stock_id not in {
            c.stock_id for c in index.exact_matches(role.exact_material)
        }:
            continue
        if not solver._allowed(
            cap, role, empty, avoid=avoid,
            allow_multiple_musks=solver._allows_multiple_musks(brief.normalized_request, brief.roles),
            enforce_own_odor_avoid=bool(brief.architecture_plan.get("operation")),
        ):
            continue
        score = solver.capability_role_score(
            cap, query_terms=role.query_terms, character_weights=role.character_weights,
            note=role.note, function=role.function, exact_material=role.exact_material,
            selected=(), previous_stock_ids=frozenset(),
        )
        if score is not None:
            eligible.append(cap.stock_id)
    return sorted(set(eligible))


def _option_coverage(
    result: dict[str, Any], expected: tuple[SemanticBrief, ...], variants: list[dict[str, Any]],
    index: MaterialCapabilityIndex | None, *, verified: bool,
) -> dict[str, Any]:
    """Planning and executable coverage are different; do not hide a failed option."""
    rows: list[dict[str, Any]] = []
    valid = verified
    try:
        if len(expected) > 1:
            index = index or build_material_capability_index()
            interpretation = result["request_interpretation"]
            index = index.with_explicit_materials(tuple(interpretation.get("explicit_materials", ())))
            inventory_hash = index.effective_inventory_sha256
            valid &= result["architecture_execution_inputs"]["effective_inventory_sha256"] == inventory_hash
            returned = {v["variant_id"]: v for v in variants}
            for position, brief in enumerate(expected[1:], 1):
                binding = brief.architecture_plan
                role = next(r for r in brief.roles if r.role_id == binding["role_id"])
                attempt = result["architecture_attempts"][position]
                pool = _admissible_role_pool(index, role, brief, interpretation.get("must_avoid", []))
                variant = returned.get(attempt["variant_id"])
                empty = bool(
                    valid and role.required and role.descriptor_requirement and not pool
                    and role.label in attempt["missing_roles"] and variant is None
                    and attempt["state"] == "WITHHELD_CONCEPT_COVERAGE_INCOMPLETE"
                )
                rows.append({
                    "option_key": f"{binding['adapter_id']}:{binding['option_id']}",
                    "subtype_id": binding["subtype_id"], "role_id": role.role_id,
                    "descriptor_requirement": role.descriptor_requirement,
                    "variant_id": attempt["variant_id"], "attempt_state": attempt["state"],
                    "returned": variant is not None,
                    "viable": variant is not None and variant["viable_comparison"],
                    "eligible_stock_ids": pool, "effective_inventory_sha256": inventory_hash,
                    "empty_role_pool_verified": empty,
                    "verified_outcome": (
                        "UNVERIFIED" if not valid else
                        "VIABLE_COMPARISON" if variant and variant["viable_comparison"] else
                        "EMPTY_ADMISSIBLE_POOL" if empty else
                        "DUPLICATE_PHYSICAL_COMPOSITION" if attempt["state"] == "WITHHELD_DUPLICATE_PHYSICAL_COMPOSITION" else
                        "BOUNDED_SOLVER_WITHHOLD" if variant is None and attempt["state"] in {
                            "WITHHELD_CONCEPT_COVERAGE_INCOMPLETE", "WITHHELD_DOSE_ALLOCATION_INFEASIBLE",
                        } else
                        "CRITIC_WITHHOLD" if variant and variant["critic_state"] == "WITHHELD" else "UNVERIFIED"
                    ),
                })
    except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError, StopIteration):
        valid = False
    return {
        "option_coverage_verified": bool(valid),
        "planned_options": [row["option_key"] for row in rows],
        "returned_options": [row["option_key"] for row in rows if row["returned"]],
        "viable_options": [row["option_key"] for row in rows if row["viable"]],
        "empty_role_pool_options": [row["option_key"] for row in rows if row["empty_role_pool_verified"]],
        "option_outcomes": rows,
    }


def audit_architectures(
    result: dict[str, Any], *, expected_case: dict[str, Any] | None = None,
    variant_count: int | None = None,
    inventory_index: MaterialCapabilityIndex | None = None,
) -> dict[str, Any]:
    """Bind receipts to planning; physical signatures exclude role labels."""
    knowledge = result.get("formulation_knowledge", {})
    source_map = {s["source_id"]: s for s in knowledge.get("sources", [])}
    allowed = {r["source_id"] for r in knowledge.get("source_reviews", []) if r.get("allowed") is True}
    adapters = {}
    manifest_hash = None
    try:
        manifest_bytes = architecture_bridge.ADAPTER_PATH.read_bytes()
        manifest = json.loads(manifest_bytes)
        architecture_bridge.validate_adapter_manifest(
            manifest, expected_schema=architecture_bridge.ADAPTER_SCHEMA,
        )
        adapters = {a["adapter_id"]: a for a in manifest["adapters"]}
        manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        pass
    cards = {c["subtype_id"]: c for c in knowledge.get("subtype_context", {}).get("cards", [])}
    planning_verified, expected = _replay_planning(result)
    control = expected[0] if expected else None
    protected = architecture_bridge.protected_role_set(
        control.roles, result.get("request_interpretation", {}).get("must_preserve", ()),
        control.protected_recognizers,
    ) if control else ()
    planned = {_hash(b.architecture_plan): b for b in expected[1:]}
    variants: list[dict[str, Any]] = []
    seen_bindings: set[str] = set()
    seen_variant_ids: set[str] = set()
    for variant in result.get("design_variants", []):
        binding = variant.get("architecture", {})
        bindings = binding.get("source_bindings", [])
        kind = binding.get("kind")
        source_bound = kind == "SOURCE_BOUND_ARCHITECTURE_COMPARISON"
        roles: tuple[SemanticRole, ...] = ()
        role_signature = None
        try:
            roles = _read_roles(variant["role_plan"])
            role_signature = architecture_bridge.role_plan_signature(roles)
        except (ValueError, TypeError, KeyError, AttributeError):
            pass
        role_verified = role_signature is not None and role_signature == variant.get("role_plan_sha256")
        expected_brief = planned.get(_hash(binding)) if source_bound else control
        if source_bound:
            binding_verified = _hash(binding) in planned and _hash(binding) not in seen_bindings
            seen_bindings.add(_hash(binding))
            role_verified &= role_signature == binding.get("role_plan_sha256")
        else:
            binding_verified = (
                binding == {"kind": kind}
                and kind in {"UNCHANGED_CONTROL", "STOCK_ALTERNATIVE_SAME_ROLE_PLAN"}
                and (kind != "UNCHANGED_CONTROL" or not variants)
                and (kind != "STOCK_ALTERNATIVE_SAME_ROLE_PLAN" or len(expected) == 1)
            )
        binding_verified &= planning_verified and expected_brief is not None
        exact_roles = expected_brief is not None and _hash([asdict(r) for r in roles]) == _hash(
            [asdict(r) for r in expected_brief.roles]
        )
        binding_verified &= exact_roles and variant.get("roles_requested") == [r.role_id for r in roles]
        binding_verified &= variant.get("variant_id") not in seen_variant_ids
        seen_variant_ids.add(variant.get("variant_id"))
        preserved = control is not None and architecture_bridge.protected_roles_preserved(
            control.roles, roles, protected, binding,
        )
        authority_safe = (
            _false_authority(binding.get("authority")) if source_bound else bool(binding_verified)
        )
        adapter = adapters.get(binding.get("adapter_id"))
        card = cards.get(binding.get("subtype_id"))
        complete_bindings = (
            isinstance(adapter, dict) and isinstance(card, dict)
            and bindings == adapter["source_bindings"]
            and binding.get("adapter_manifest_sha256") == manifest_hash
            and binding.get("subtype_id") == adapter["subtype_id"]
            and binding.get("subtype_card_sha256") == adapter["subtype_card_sha256"]
            and architecture_bridge._support_error(adapter, card, knowledge) is None
        ) if source_bound else False
        source_closure = (complete_bindings and bool(bindings) and all(
            b["source_id"] in allowed and b["source_id"] in source_map
            and source_record_hash(source_map[b["source_id"]]) == b["source_record_sha256"]
            for b in bindings
        )) if source_bound else None
        try:
            # Physical identity is the solver's allocation (duplicate suppression
            # compares it), before the detection pass's recorded raises.
            solved_formula: Any = solver_formula(variant["formula"])
        except (ValueError, TypeError, KeyError, IndexError):
            solved_formula = None
        physical_valid, physical = _physical_formula(
            solved_formula, "6000" if expected_case is not None else None,
        )
        critic = variant["critic"]["state"]
        action = variant.get("formula_action")
        viable = (
            critic in {"ACCEPTED_WITH_HOLDS", "ACCEPTED_AS_DESIGN_HYPOTHESIS"}
            and action == "PROPOSAL_ONLY" and physical_valid
        )
        critic_safe = viable or (critic == "WITHHELD" and action == "NO_CHANGE")
        variants.append({
            "variant_id": variant["variant_id"], "label": variant["label"],
            "architecture_kind": kind,
            "adapter_id": binding.get("adapter_id"), "option_id": binding.get("option_id"),
            "subtype_id": binding.get("subtype_id"),
            "role_plan_sha256": role_signature,
            "claimed_role_plan_sha256": variant.get("role_plan_sha256"),
            "role_plan_verified": bool(role_verified),
            "registered_option_verified": bool(binding_verified),
            "physical_composition_sha256": _hash(physical),
            "physical_formula_verified": physical_valid,
            # Entire returned control variant, including formula metadata,
            # constraints, solver, critic, temporal and reference payloads.
            # No wrapper/label fields within the variant are excluded.
            "full_variant_sha256": _hash(variant),
            "stock_doses": [{"stock_id": r["stock_id"], "material": r["identity_name"],
                             "amount": r["amount_decimal"], "unit": r["amount_unit"]} for r in physical],
            "role_ids": variant["roles_requested"], "critic_state": critic,
            "formula_action": action, "viable_comparison": viable, "critic_action_safe": critic_safe,
            "issues": variant["critic"]["issues"],
            "separate_totals": variant["formula"]["separate_totals"],
            "source_closure": source_closure, "source_bindings": bindings,
            "ordering": variant["ordering"],
            "protected_roles_preserved": preserved,
            "allocation_policy_sha256": binding.get("allocation_policy_sha256"),
            "authority_safe": bool(authority_safe),
        })
    planning = result.get("architecture_planning") or {}
    attempts_verified = _attempts_verified(
        result, expected, variants, "6000" if expected_case is not None else None,
    )
    execution_verified = _execution_verified(
        result, expected, inventory_index, "6000" if expected_case is not None else None,
    )
    coverage = _option_coverage(
        result, expected, variants, inventory_index,
        verified=planning_verified and attempts_verified and execution_verified,
    )
    return {
        "status": result["status"], "design_sha256": result["design_sha256"],
        "request_sha256": result.get("request_sha256"),
        "planning_state": planning.get("state"), "plan_sha256": planning.get("plan_sha256"),
        "planning_verified": planning_verified,
        "attempts_verified": attempts_verified,
        "execution_verified": execution_verified,
        "request_contract_verified": _request_matches_case(result, expected_case, variant_count),
        "planned_architecture_count": max(0, len(expected) - 1),
        **coverage,
        "withheld_options": planning.get("withheld_options", []),
        "attempts": [{k: attempt[k] for k in (
            "variant_id", "state", "role_count", "role_plan_sha256", "missing_roles", "holds",
            "assigned_role_ids", "duplicate_of_variant_id", "physical_composition_sha256",
        ) if k in attempt} for attempt in result.get("architecture_attempts", [])],
        "variants": variants,
        "authority_safe": all(result.get(k) is False for k in AUTHORITY)
        and all(result.get(k) is False for k in ("formula_modified", "inventory_modified", "physical_compounding_performed")),
        "sensory_scores_absent": all(result.get(k) is None for k in (
            "pleasantness", "personal_liking", "population_liking", "beauty_score")),
        "network_used": knowledge.get("network_used"), "inventory": result.get("inventory", {}),
        "formula_action": result.get("formula_action"),
    }


def architecture_pair_is_safe(control: dict[str, Any], comparison: dict[str, Any]) -> bool:
    """Neither arm may borrow the other arm's provenance or authority checks."""
    return all(
        receipt["authority_safe"] is True and receipt["sensory_scores_absent"] is True
        and receipt["network_used"] is False and receipt["planning_verified"] is True
        and receipt["attempts_verified"] is True
        and receipt["execution_verified"] is True
        and receipt["option_coverage_verified"] is True
        and receipt["request_contract_verified"] is True
        and all(
            variant["authority_safe"] is True and variant["role_plan_verified"] is True
            and variant["registered_option_verified"] is True
            and variant["critic_action_safe"] is True
            and variant["physical_formula_verified"] is True
            and variant["ordering"] == "UNORDERED_UNTIL_SENSORY_COMPARISON"
            and (variant["architecture_kind"] != "SOURCE_BOUND_ARCHITECTURE_COMPARISON"
                 or (variant["source_closure"] is True and variant["protected_roles_preserved"] is True))
            for variant in receipt["variants"]
        )
        for receipt in (control, comparison)
    )


def control_is_preserved(control: dict[str, Any], comparison: dict[str, Any]) -> bool:
    left = [v for v in control["variants"] if v["architecture_kind"] == "UNCHANGED_CONTROL"]
    right = [v for v in comparison["variants"] if v["architecture_kind"] == "UNCHANGED_CONTROL"]
    if not left and not right:
        return not control["variants"] and not comparison["variants"]
    return (
        len(left) == len(right) == 1
        and left[0]["full_variant_sha256"] == right[0]["full_variant_sha256"]
    )


def viable_architectures_are_distinct(receipt: dict[str, Any]) -> bool:
    """A withheld or duplicate branch cannot inflate executable coverage."""
    viable = [v for v in receipt["variants"] if v["viable_comparison"]]
    if not any(v["architecture_kind"] == "SOURCE_BOUND_ARCHITECTURE_COMPARISON" for v in viable):
        return False
    return all(len({v[key] for v in viable}) == len(viable) for key in (
        "role_plan_sha256", "physical_composition_sha256",
    ))


def option_contract_passes(receipt: dict[str, Any], expectation: dict[str, Any]) -> bool:
    """Every predeclared branch must be viable or have a verified admissible-pool hold."""
    if not receipt["option_coverage_verified"]:
        return False
    planned = receipt["planned_options"]
    returned = set(receipt["returned_options"])
    viable = set(receipt["viable_options"])
    empty = set(receipt["empty_role_pool_options"])
    return bool(
        planned == expectation["planned_options"] and len(set(planned)) == len(planned)
        and viable <= returned <= set(planned)
        and set(expectation["required_viable_options"]) <= viable
        and empty <= set(expectation["allow_empty_role_pool_options"])
        and not viable & empty and viable | empty == set(planned) and returned == viable
        and (not planned or receipt["planning_state"] == "SOURCE_BOUND_COMPARISON_READY")
        and (not viable or viable_architectures_are_distinct(receipt))
    )


def _validate_v4_corpus(raw: bytes) -> dict[str, Any]:
    """Reject protocol drift before inventory access or any expensive design call."""
    if hashlib.sha256(raw).hexdigest() != _V4_CORPUS_SHA256:
        raise ValueError("v4 frozen corpus bytes drifted")
    value = json.loads(raw)
    if not isinstance(value, dict) or set(value) != {
        "schema_version", "frozen_before_execution", "scope", "configuration", "cases",
        "predecessor_sha256", "option_expectations",
    }:
        raise ValueError("invalid v4 corpus fields")
    if (value["schema_version"] != "architecture-comparison-corpus-v4"
            or value["frozen_before_execution"] is not True
            or value["scope"] != "DIAGNOSTIC_CONTRACT_CORPUS_NOT_HELD_OUT_SENSORY_DATA"
            or _hash(value["configuration"]) != _hash(_V4_CONFIGURATION)):
        raise ValueError("v4 execution configuration mismatch")
    predecessor_bytes = ARCHITECTURE_CORPUS_V3.read_bytes()
    if (value["predecessor_sha256"] != _V3_CORPUS_SHA256
            or hashlib.sha256(predecessor_bytes).hexdigest() != _V3_CORPUS_SHA256):
        raise ValueError("v4 corpus predecessor drifted")
    cases = value["cases"]
    if not isinstance(cases, list) or len(cases) != 68 or cases[:56] != json.loads(predecessor_bytes)["cases"]:
        raise ValueError("v4 case prefix or count changed")
    ids = []
    for case in cases:
        if not isinstance(case, dict) or set(case) != {
            "case_id", "brief", "expected_subtype", "must_preserve", "must_avoid", "expected_hold",
        }:
            raise ValueError("invalid v4 case fields")
        for field in ("case_id", "brief"):
            if not isinstance(case[field], str) or not case[field].strip():
                raise ValueError("invalid v4 case text")
        for field in ("expected_subtype", "expected_hold"):
            if case[field] is not None and (not isinstance(case[field], str) or not case[field]):
                raise ValueError("invalid v4 expected state")
        for field in ("must_preserve", "must_avoid"):
            if not isinstance(case[field], list) or not all(isinstance(x, str) and x.strip() for x in case[field]):
                raise ValueError("invalid v4 constraints")
        ids.append(case["case_id"])
    if len(set(ids)) != 68 or ids[56:] != [f"v4_{i:02d}" for i in range(1, 13)]:
        raise ValueError("v4 case identities changed")
    expectations = value["option_expectations"]
    if not isinstance(expectations, dict) or set(expectations) != set(ids[56:]):
        raise ValueError("v4 option case coverage changed")
    registered = {f"{a}:{o}" for a, o in architecture_bridge._V4_REQUIREMENTS}
    for expected in expectations.values():
        if not isinstance(expected, dict) or set(expected) != {
            "planned_options", "required_viable_options", "allow_empty_role_pool_options",
        }:
            raise ValueError("invalid v4 option expectation fields")
        for items in expected.values():
            if (not isinstance(items, list) or not all(isinstance(x, str) for x in items)
                    or len(set(items)) != len(items) or not set(items) <= registered):
                raise ValueError("invalid v4 expected options")
        required, empty = set(expected["required_viable_options"]), set(expected["allow_empty_role_pool_options"])
        if required & empty or required | empty != set(expected["planned_options"]):
            raise ValueError("incomplete v4 option expectations")
    return value


def _validate_v5_corpus(raw: bytes) -> dict[str, Any]:
    """Frozen diagnostic census, not a held-out scent-performance claim."""
    if hashlib.sha256(raw).hexdigest() != _V5_CORPUS_SHA256:
        raise ValueError("v5 frozen corpus bytes drifted")
    value = json.loads(raw)
    if (not isinstance(value, dict) or set(value) != {
        "schema_version", "frozen_before_execution", "scope", "configuration",
        "predecessor_sha256", "cases", "option_expectations",
    } or value["schema_version"] != "architecture-comparison-corpus-v5"
            or value["frozen_before_execution"] is not True
            or value["scope"] != "DIAGNOSTIC_CONTRACT_CORPUS_NOT_HELD_OUT_SENSORY_DATA"
            or _hash(value["configuration"]) != _hash(_V5_CONFIGURATION)):
        raise ValueError("v5 execution configuration mismatch")
    if (value["predecessor_sha256"] != _V4_CORPUS_SHA256
            or hashlib.sha256(ARCHITECTURE_CORPUS_V4.read_bytes()).hexdigest() != _V4_CORPUS_SHA256):
        raise ValueError("v5 historical corpus reference drifted")
    cases = value["cases"]
    ids = [f"v5_{i:02d}" for i in range(1, 68)]
    if not isinstance(cases, list) or len(cases) != 67 or [c.get("case_id") for c in cases] != ids:
        raise ValueError("v5 diagnostic case census drifted")
    for case in cases:
        if (set(case) != {"case_id", "brief", "expected_subtype", "must_preserve", "must_avoid", "expected_hold"}
                or not isinstance(case["brief"], str) or not case["brief"].strip()
                or any(not isinstance(case[f], list) or not all(isinstance(x, str) and x.strip() for x in case[f])
                       for f in ("must_preserve", "must_avoid"))
                or any(case[f] is not None and (not isinstance(case[f], str) or not case[f])
                       for f in ("expected_subtype", "expected_hold"))):
            raise ValueError("invalid v5 case")
    expectations = value["option_expectations"]
    if not isinstance(expectations, dict) or set(expectations) != set(ids):
        raise ValueError("v5 option census changed")
    adapter_bytes = architecture_bridge.V5_PATH.read_bytes()
    if hashlib.sha256(adapter_bytes).hexdigest() != architecture_bridge._V5_SHA256:
        raise ValueError("v5 adapter census drifted")
    manifest = json.loads(adapter_bytes)
    registered = {f"{a['adapter_id']}:{o['option_id']}" for a in manifest["adapters"] for o in a["options"]}
    planned: set[str] = set()
    for expectation in expectations.values():
        if (not isinstance(expectation, dict) or set(expectation) != {
            "planned_options", "required_viable_options", "allowed_verified_outcomes",
        } or expectation["allowed_verified_outcomes"] != _V5_OUTCOMES):
            raise ValueError("invalid v5 outcome policy")
        for field in ("planned_options", "required_viable_options"):
            items = expectation[field]
            if (not isinstance(items, list) or not all(isinstance(x, str) for x in items)
                    or len(items) != len(set(items)) or not set(items) <= registered):
                raise ValueError("unregistered v5 expectation")
        if not set(expectation["required_viable_options"]) <= set(expectation["planned_options"]):
            raise ValueError("unplanned required option")
        planned.update(expectation["planned_options"])
    required = {f"{a}:{o}" for a, o in architecture_bridge.rules_v5.OPTIONS}
    if not required <= planned:
        raise ValueError("v5 option missing from frozen diagnostic")
    return value


def v5_option_contract_passes(receipt: dict[str, Any], expectation: dict[str, Any]) -> bool:
    """Accept verified outcomes, never count a hold/duplicate as usable coverage.

    The earlier v4 acceptance contract is deliberately unchanged. v5 covers
    unavailable exact grades and explicit operations as well as additions.
    """
    rows = receipt["option_outcomes"]
    planned = expectation["planned_options"]
    return bool(
        receipt["option_coverage_verified"] and receipt["execution_verified"]
        and receipt["attempts_verified"] and receipt["planning_verified"]
        and receipt["planned_options"] == planned
        and [r["option_key"] for r in rows] == planned and len(set(planned)) == len(planned)
        and all(r["verified_outcome"] in expectation["allowed_verified_outcomes"] for r in rows)
        and set(expectation["required_viable_options"]) <= set(receipt["viable_options"])
        and (not planned or receipt["planning_state"] == "SOURCE_BOUND_COMPARISON_READY")
        and (not receipt["viable_options"] or viable_architectures_are_distinct(receipt))
    )


def architecture_protocol(version: int) -> tuple[Path, Path, str, int]:
    """Fixed historical paths; never resolve predecessor replay via active path."""
    if type(version) is not int or version not in (1, 2, 3, 4, 5):
        raise ValueError("unknown architecture protocol")
    return {
        1: (ARCHITECTURE_CORPUS, architecture_bridge.V1_PATH, "source-bound-architecture-adapters-v1", 15),
        2: (ARCHITECTURE_CORPUS_V2, architecture_bridge.V2_PATH, "source-bound-architecture-adapters-v2", 30),
        3: (ARCHITECTURE_CORPUS_V3, architecture_bridge.V3_PATH, "source-bound-architecture-adapters-v3", 56),
        4: (ARCHITECTURE_CORPUS_V4, architecture_bridge.V4_PATH, "source-bound-architecture-adapters-v4", 68),
        5: (ARCHITECTURE_CORPUS_V5, architecture_bridge.V5_PATH, "source-bound-architecture-adapters-v5", 67),
    }[version]


def run_architecture_comparison(
    *, version: int = 1, progress: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Current-source control vs source-bound branches, then reverse replay.

    This frozen diagnostic tests behavior, not model accuracy or scent quality.
    It is separate from the historical v2/v3 subtype-manifest experiment.
    """
    corpus_path, adapter_path, expected_schema, expected_count = architecture_protocol(version)
    if version in (1, 2, 3, 4, 5) and hashlib.sha256(adapter_path.read_bytes()).hexdigest() != getattr(
        architecture_bridge, f"_V{version}_SHA256",
    ):
        raise ValueError("historical architecture manifest bytes drifted")
    raw = corpus_path.read_bytes()
    corpus = (_validate_v5_corpus(raw) if version == 5 else
              _validate_v4_corpus(raw) if version == 4 else json.loads(raw))
    if corpus.get("schema_version") != f"architecture-comparison-corpus-v{version}" or corpus.get("frozen_before_execution") is not True:
        raise ValueError("unfrozen architecture diagnostic corpus")
    cases = corpus["cases"]
    if len(cases) != expected_count or len({case["case_id"] for case in cases}) != expected_count:
        raise ValueError("architecture corpus changed; review a successor protocol")
    opening = {**_snapshot(), corpus_path.relative_to(ROOT).as_posix(): hashlib.sha256(raw).hexdigest()}
    receipts: dict[str, dict[str, Any]] = {case["case_id"]: {} for case in cases}
    timings: dict[str, list[float]] = {"CONTROL_ONLY": [], "ARCHITECTURE_COMPARISON": []}
    design_timings: dict[str, list[float]] = {arm: [] for arm in timings}
    audit_timings: dict[str, list[float]] = {arm: [] for arm in timings}
    arms = {"CONTROL_ONLY": 1, "ARCHITECTURE_COMPARISON": 3}
    completed = 0
    # One diagnostic-local frozen index, never shared with application requests.
    inventory_index = build_material_capability_index()

    def execute(case: dict[str, Any], variant_count: int, arm: str, phase: str) -> dict[str, Any]:
        nonlocal completed
        start = time.perf_counter()
        designed = design_formula(
            formula_name=f"Architecture diagnostic {case['case_id']}", idea=case["brief"],
            design_mode="DEEP_COMPOSE", variant_count=variant_count, max_materials=12,
            liquid_concentrate_ul_decimal="6000", must_avoid=tuple(case["must_avoid"]),
            must_preserve=tuple(case["must_preserve"]),
        )
        design_end = time.perf_counter()
        audited = audit_architectures(designed, expected_case=case, variant_count=variant_count,
                                      inventory_index=inventory_index)
        end = time.perf_counter()
        if phase == "forward":
            design_timings[arm].append(design_end - start)
            audit_timings[arm].append(end - design_end)
        completed += 1
        if progress:
            progress({"completed": completed, "total": len(cases) * 4, "phase": phase,
                      "arm": arm, "case_id": case["case_id"],
                      "design_seconds": design_end - start, "audit_seconds": end - design_end})
        return audited

    repeat_equal = True
    with patch.object(architecture_bridge, "ADAPTER_PATH", adapter_path), \
            patch.object(architecture_bridge, "ADAPTER_SCHEMA", expected_schema), \
            patch.object(socket, "create_connection", _forbid_network), \
            patch.object(socket.socket, "connect", _forbid_network), \
            patch.object(socket.socket, "connect_ex", _forbid_network), \
            patch.object(socket, "getaddrinfo", _forbid_network):
        for arm, count in arms.items():
            for case in cases:
                start = time.perf_counter()
                receipts[case["case_id"]][arm] = execute(case, count, arm, "forward")
                timings[arm].append(time.perf_counter() - start)
        for arm, count in reversed(list(arms.items())):
            for case in reversed(cases):
                repeat_equal &= execute(case, count, arm, "reverse") == receipts[case["case_id"]][arm]
    closing = {**_snapshot(), corpus_path.relative_to(ROOT).as_posix(): hashlib.sha256(corpus_path.read_bytes()).hexdigest()}
    changed = sorted(key for key in opening.keys() | closing.keys() if opening.get(key) != closing.get(key))
    rows = []
    for case in cases:
        pair = receipts[case["case_id"]]
        control, comparison = pair["CONTROL_ONLY"], pair["ARCHITECTURE_COMPARISON"]
        available = comparison["variants"]
        branch = [v for v in available if v["architecture_kind"] == "SOURCE_BOUND_ARCHITECTURE_COMPARISON"]
        viable_branch = [v for v in branch if v["viable_comparison"]]
        expected = case["expected_subtype"]
        control_preserved = control_is_preserved(control, comparison)
        contracts = architecture_pair_is_safe(control, comparison)
        option_expectation = corpus.get("option_expectations", {}).get(case["case_id"])
        if option_expectation is not None:
            if version == 5:
                contracts &= v5_option_contract_passes(comparison, option_expectation)
            else:
                contracts &= option_contract_passes(comparison, option_expectation)
                contracts &= all(v["subtype_id"] == expected for v in branch)
        elif expected:
            contracts &= comparison["planning_state"] == "SOURCE_BOUND_COMPARISON_READY"
            contracts &= len(viable_branch) > 0 and all(v["subtype_id"] == expected for v in branch)
            contracts &= viable_architectures_are_distinct(comparison)
        else:
            contracts &= len(branch) == 0
        if case["expected_hold"]:
            contracts &= comparison["status"] == case["expected_hold"] and not available
        rows.append({
            "case_id": case["case_id"], "brief": case["brief"], "expected_subtype": expected,
            "contract_pass": bool(contracts), "control_preserved": control_preserved,
            "distinct_role_plans": len({v["role_plan_sha256"] for v in available}),
            "distinct_physical_compositions": len({v["physical_composition_sha256"] for v in available}),
            "source_bound_returned": len(branch), "viable_source_bound_returned": len(viable_branch),
            "viable_architectures_distinct": viable_architectures_are_distinct(comparison),
            "option_execution_state": (
                "PARTIAL_CURRENT_INVENTORY" if comparison["empty_role_pool_options"] and viable_branch
                else "HOLD_NO_ELIGIBLE_CURRENT_STOCK" if comparison["empty_role_pool_options"]
                else "EXECUTABLE_COMPARISONS" if viable_branch else "NO_SOURCE_BOUND_COMPARISON"
            ),
            "control": control,
            "comparison": comparison, "sensory_improvement": "NOT_TESTED",
        })
    all_receipts = [r for pair in receipts.values() for r in pair.values()]
    inventory_hashes = {_hash(r["inventory"]) for r in all_receipts if r["inventory"]}
    safe = all(row["contract_pass"] and row["control_preserved"] for row in rows)
    same_inventory = len(inventory_hashes) == 1
    return {
        "schema_version": f"architecture-comparison-result-v{version}",
        "adapter_manifest_sha256": hashlib.sha256(adapter_path.read_bytes()).hexdigest(),
        "adapter_manifest_path": adapter_path.relative_to(ROOT).as_posix(),
        "scope": "CURRENT_SOURCE_EXECUTABLE_ARCHITECTURE_DIAGNOSTIC_NOT_SENSORY_BENCHMARK",
        "status": "PASS" if safe and repeat_equal and same_inventory and not changed else "FAIL",
        "corpus_sha256": hashlib.sha256(raw).hexdigest(), "configuration": corpus["configuration"],
        "opening_snapshot_sha256": _hash(opening), "closing_snapshot_sha256": _hash(closing),
        "snapshot_file_count": len(opening), "changed_paths": changed,
        "reverse_order_repeat_identical": repeat_equal, "same_inventory": same_inventory,
        "case_count": len(cases), "design_calls": len(cases) * 4,
        "cases_with_source_bound_variants": sum(row["source_bound_returned"] > 0 for row in rows),
        "source_bound_variants": sum(row["source_bound_returned"] for row in rows),
        "viable_source_bound_variants": sum(row["viable_source_bound_returned"] for row in rows),
        "cases_with_changed_physical_composition": sum(row["source_bound_returned"] > 0 and row["distinct_physical_compositions"] > 1 for row in rows),
        "timing_p95_seconds": {name: sorted(values)[math.ceil(.95 * len(values)) - 1] for name, values in timings.items()},
        "design_p95_seconds": {name: sorted(values)[math.ceil(.95 * len(values)) - 1] for name, values in design_timings.items()},
        "audit_p95_seconds": {name: sorted(values)[math.ceil(.95 * len(values)) - 1] for name, values in audit_timings.items()},
        "design_timings_seconds": design_timings, "audit_timings_seconds": audit_timings,
        "case_timings_seconds": timings, "cases": rows,
        "network_used": False, "authority": dict(AUTHORITY),
        "limitations": [
            "Predeclared diagnostic prompts, not a held-out generalization or preference experiment.",
            "Stock allocation and descriptor matching remain heuristic; traceability does not establish scent realism.",
            "The control and alternative planning arms share the current source, inventory, and evidence bundle.",
            "Timing covers this diagnostic corpus and workstation only, not full-system performance acceptance.",
            "Physical compounding, scent quality, diffusion, longevity, safety and consumer preference remain NOT_TESTED.",
        ],
    }


def write_result_artifact(result: dict[str, Any], destination: Path) -> dict[str, Any]:
    """Save generated evidence after the run; never overwrite an earlier result."""
    payload = (json.dumps(result, ensure_ascii=True, allow_nan=False, indent=2) + "\n").encode()
    with destination.open("xb") as artifact:
        artifact.write(payload)
    return {"status": result["status"], "artifact_path": str(destination.resolve()),
            "artifact_sha256": hashlib.sha256(payload).hexdigest(),
            "case_count": result["case_count"], "design_calls": result["design_calls"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--architecture", action="store_true", help="Run the separate frozen architecture diagnostic")
    parser.add_argument("--architecture-v2", action="store_true", help="Run the frozen floral-successor diagnostic")
    parser.add_argument("--architecture-v3", action="store_true", help="Run the frozen floral/aromatic diagnostic")
    parser.add_argument("--architecture-v4", action="store_true", help="Run the frozen chypre/citrus-wood diagnostic")
    parser.add_argument("--architecture-v5", action="store_true", help="Run the frozen remaining-coverage operation diagnostic")
    parser.add_argument("--progress", action="store_true", help="Emit diagnostic progress to stderr only")
    parser.add_argument("--output", type=Path, help="Exclusively create a new result artifact after input checks")
    arguments = parser.parse_args()
    if sum((arguments.architecture, arguments.architecture_v2, arguments.architecture_v3, arguments.architecture_v4, arguments.architecture_v5)) > 1:
        parser.error("choose one architecture protocol")
    if arguments.output and (arguments.output.exists() or not arguments.output.parent.is_dir()):
        parser.error("output must be a new path in an existing directory")
    progress = (lambda row: print(json.dumps({"progress": row}), file=sys.stderr, flush=True)) if arguments.progress else None
    output = (run_architecture_comparison(version=5, progress=progress) if arguments.architecture_v5 else
              run_architecture_comparison(version=4, progress=progress) if arguments.architecture_v4 else
              run_architecture_comparison(version=3, progress=progress) if arguments.architecture_v3 else
              run_architecture_comparison(version=2, progress=progress) if arguments.architecture_v2 else
              run_architecture_comparison(progress=progress) if arguments.architecture else run_comparison())
    print(json.dumps(write_result_artifact(output, arguments.output) if arguments.output else output,
                     ensure_ascii=True, allow_nan=False))
