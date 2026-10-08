"""Regressions from the frozen 56-case run; no sensory quality assertions."""

import copy
import json
from dataclasses import replace
from functools import lru_cache

import pytest

from engine.formulation_intelligence import formula_design_runtime as runtime
from engine.research.subtype_benchmark import (
    architecture_pair_is_safe,
    architecture_protocol,
    audit_architectures,
    viable_architectures_are_distinct,
)


def _case(case_id):
    return next(c for c in json.loads(architecture_protocol(3)[0].read_bytes())["cases"]
                if c["case_id"] == case_id)


def _kwargs(case_id):
    case = _case(case_id)
    return dict(formula_name=f"Architecture diagnostic {case_id}", idea=case["brief"],
                design_mode="DEEP_COMPOSE", variant_count=3, max_materials=12,
                must_avoid=tuple(case["must_avoid"]), must_preserve=tuple(case["must_preserve"]))


@lru_cache(maxsize=3)
def _result(case_id):
    return runtime.design_formula(**_kwargs(case_id))


def test_explicit_cyclamen_is_not_displaced_by_muguet_in_diagnostic_name():
    result = _result("muguet_cyclamen")
    assert {v["architecture"].get("subtype_id") for v in result["design_variants"][1:]} == {
        "MUGUET_CYCLAMEN",
    }


def test_soft_lavender_keeps_distinct_alternatives_with_current_inventory():
    result = _result("lav_soft_musk")
    audit = audit_architectures(result)
    assert viable_architectures_are_distinct(audit)
    assert 2 <= len(result["design_variants"]) <= 3
    assert audit["attempts_verified"]
    assert audit["execution_verified"]


@lru_cache(maxsize=1)
def _duplicate_result():
    """Two valid assignments share stocks; real allocation and critique still run."""
    from engine.formulation_intelligence import formula_solver as solver

    original = solver._solve_assignments
    assignments = []

    def duplicate_third(**kwargs):
        chosen, missing = original(**kwargs)
        assignments.append(chosen)
        if len(assignments) == 3:
            chosen = tuple(replace(right, capability=left.capability)
                           for left, right in zip(assignments[1], chosen, strict=True))
        return chosen, missing

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(solver, "_solve_assignments", duplicate_third)
        result = runtime.design_formula(**_kwargs("lav_soft_musk"))
    assert len(assignments) == 3
    return result


def test_duplicate_physical_branch_is_suppressed_and_proven():
    result = _duplicate_result()
    audit = audit_architectures(result)
    assert viable_architectures_are_distinct(audit)
    assert audit["attempts_verified"]
    assert audit["execution_verified"]
    assert len(result["design_variants"]) == 2
    duplicate = [a for a in result["architecture_attempts"]
                 if a["state"] == "WITHHELD_DUPLICATE_PHYSICAL_COMPOSITION"]
    assert len(duplicate) == 1
    assert duplicate[0]["duplicate_of_variant_id"] == result["design_variants"][1]["variant_id"]
    assert duplicate[0]["physical_composition_sha256"] == audit["variants"][1]["physical_composition_sha256"]


def test_real_campaign_hold_is_a_verified_empty_result():
    result = _result("campaign_hold")
    audit = audit_architectures(result, expected_case=_case("campaign_hold"), variant_count=3)
    assert result["status"] == "WITHHELD_CAMPAIGN_IDENTITY"
    assert result["design_variants"] == []
    assert audit["planning_verified"]
    assert audit["request_contract_verified"]


@pytest.mark.parametrize("fault", ["hold", "manifest", "request", "formula", "action", "context", "reason"])
def test_campaign_status_alone_does_not_establish_a_valid_hold(fault):
    result = copy.deepcopy(_result("campaign_hold"))
    if fault == "hold":
        result["formulation_knowledge"]["subtype_context"]["campaign_identity_holds"] = []
    elif fault == "manifest":
        result["formulation_knowledge"]["subtype_research_sha256"] = "0" * 64
    elif fault == "request":
        result["semantic_brief"]["normalized_request"] = "A rose perfume"
    elif fault == "formula":
        result["optimized_formula"] = {"rows": []}
    elif fault == "action":
        result["formula_action"] = "PROPOSAL_ONLY"
    elif fault == "context":
        result["semantic_brief"]["knowledge_context"] = {}
    else:
        result["reason_codes"] = []
    audit = audit_architectures(result, expected_case=_case("campaign_hold"), variant_count=3)
    assert not (audit["planning_verified"] and audit["request_contract_verified"])


def test_unqualified_request_builds_index_once(monkeypatch):
    original = runtime.build_material_capability_index
    calls = []

    def count(*args, **kwargs):
        calls.append((args, kwargs))
        return original(*args, **kwargs)

    monkeypatch.setattr(runtime, "build_material_capability_index", count)
    runtime.design_formula(**{**_kwargs("lav_soft_musk"), "variant_count": 1})
    assert len(calls) == 1


def test_per_request_reuse_equals_previous_rebuilt_index_path(monkeypatch):
    from engine.formulation_intelligence.material_capability_index import MaterialCapabilityIndex

    expected = _result("lav_soft_musk")
    monkeypatch.setattr(MaterialCapabilityIndex, "with_explicit_materials",
                        lambda self, materials: runtime.build_material_capability_index(materials))
    assert runtime.design_formula(**_kwargs("lav_soft_musk")) == expected


@pytest.mark.parametrize("materials", [(), ("Hedione", "Linalool"), ("unowned exact product",)])
def test_explicit_rebinding_matches_loader_and_does_not_mutate_index(materials):
    original = runtime.build_material_capability_index()
    before = copy.deepcopy(original)
    rebound = original.with_explicit_materials(materials)
    assert rebound == runtime.build_material_capability_index(materials)
    assert original == before
    assert rebound.with_explicit_materials(()) == original


def test_stock_dose_signature_ignores_role_labels_decimal_spelling_and_row_splitting():
    formula = copy.deepcopy(_result("lav_soft_musk")["design_variants"][0]["formula"])
    signature = runtime._stock_dose_signature(formula)
    row = formula["rows"][0]
    from decimal import Decimal

    row["amount_decimal"] = str(Decimal(row["amount_decimal"]) / 2)
    formula["rows"].append(copy.deepcopy(row))
    row["amount_decimal"] += "0" if "." in row["amount_decimal"] else ".0"
    row["role"] = "a different label"
    formula["rows"].reverse()
    assert runtime._stock_dose_signature(formula) == signature
    row["carrier"] = "a different carrier"
    assert runtime._stock_dose_signature(formula) != signature


def test_campaign_hold_is_bound_to_exact_frozen_request():
    result = _result("campaign_hold")
    for changed in ({"brief": "A rose perfume"}, {"case_id": "another_campaign"},
                    {"expected_hold": None}):
        assert not audit_architectures(
            result, expected_case={**_case("campaign_hold"), **changed}, variant_count=3,
        )["request_contract_verified"]


@pytest.mark.parametrize("fault", [
    "reference", "hash", "missing", "distinct", "binding", "total", "extra",
    "state_relabel", "swapped_solved_ids",
])
def test_duplicate_suppression_is_independently_verified(fault):
    original = _duplicate_result()
    result = copy.deepcopy(original)
    attempt = result["architecture_attempts"][-1]
    if fault == "reference":
        attempt["duplicate_of_variant_id"] = "nonexistent"
    elif fault == "hash":
        attempt["physical_composition_sha256"] = "0" * 64
    elif fault == "missing":
        result["architecture_attempts"].pop()
    elif fault == "distinct":
        attempt["suppressed_formula"] = copy.deepcopy(result["design_variants"][0]["formula"])
    elif fault == "binding":
        attempt["architecture"]["option_id"] = "invented"
    elif fault == "total":
        attempt.setdefault("suppressed_formula", copy.deepcopy(result["design_variants"][1]["formula"]))
        attempt["suppressed_formula"]["separate_totals"]["liquid_total_ul"] = "1"
    elif fault == "state_relabel":
        attempt["state"] = "WITHHELD_DOSE_ALLOCATION_INFEASIBLE"
        for key in ("duplicate_of_variant_id", "physical_composition_sha256",
                    "suppressed_formula", "suppressed_critic"):
            attempt.pop(key, None)
    elif fault == "swapped_solved_ids":
        left, right = result["architecture_attempts"][:2]
        left["variant_id"], right["variant_id"] = right["variant_id"], left["variant_id"]
    else:
        result["architecture_attempts"].append(copy.deepcopy(attempt))
    assert not architecture_pair_is_safe(audit_architectures(original), audit_architectures(result))


@pytest.mark.parametrize("fault", [
    "stock", "identity", "fraction", "carrier", "role", "selected_stocks", "assigned_roles",
])
def test_valid_totals_do_not_authorize_forged_stock_or_assignment(fault):
    original = _result("lav_soft_musk")
    result = copy.deepcopy(original)
    variant = result["design_variants"][1]
    row = variant["formula"]["rows"][0]
    if fault == "stock":
        row["stock_id"] = "NONEXISTENT_AUDIT_STOCK"
    elif fault == "identity":
        row["identity_name"] = "Unowned invented product"
    elif fault == "fraction":
        row["stock_fraction_decimal"] = "0.123"
    elif fault == "carrier":
        row["carrier"] = "invented carrier"
    elif fault == "role":
        row["role"] = "unrequested role"
    elif fault == "selected_stocks":
        variant["solver"]["selected_stock_ids"] = ["NONEXISTENT_AUDIT_STOCK"]
    else:
        result["architecture_attempts"][1]["assigned_role_ids"] = []
    assert not architecture_pair_is_safe(audit_architectures(original), audit_architectures(result))


@pytest.mark.parametrize("fault", ["missing_critic", "forged_critic", "coverage_reason", "allocation_reason"])
def test_forged_suppression_or_failure_proof_is_rejected(fault):
    original = _duplicate_result()
    result = copy.deepcopy(original)
    attempt = result["architecture_attempts"][-1]
    if fault == "missing_critic":
        attempt.pop("suppressed_critic")
    elif fault == "forged_critic":
        attempt["suppressed_critic"] = {"state": "FORGED", "release_authority": True}
    else:
        for key in ("duplicate_of_variant_id", "physical_composition_sha256",
                    "suppressed_formula", "suppressed_critic"):
            attempt.pop(key)
        if fault == "coverage_reason":
            attempt["state"] = "WITHHELD_CONCEPT_COVERAGE_INCOMPLETE"
            attempt["missing_roles"] = ["not_a_real_role"]
        else:
            attempt["state"] = "WITHHELD_DOSE_ALLOCATION_INFEASIBLE"
            attempt["holds"] = ["DOSE_ALLOCATION_INFEASIBLE:forged"]
    assert not architecture_pair_is_safe(audit_architectures(original), audit_architectures(result))


def test_self_consistent_empty_assignment_cannot_forge_a_coverage_failure():
    import hashlib

    result = copy.deepcopy(_duplicate_result())
    attempt = result["architecture_attempts"][-1]
    for key in ("duplicate_of_variant_id", "physical_composition_sha256",
                "suppressed_formula", "suppressed_critic"):
        attempt.pop(key)
    from engine.research.subtype_benchmark import _replay_planning

    valid, briefs = _replay_planning(result)
    assert valid
    missing = [role.label for role in briefs[-1].roles if role.required]
    attempt.update(state="WITHHELD_CONCEPT_COVERAGE_INCOMPLETE", assigned_role_ids=[],
                   assignment_bindings=[], missing_roles=missing, holds=[],
                   variant_id=f"semantic-variant-3-{hashlib.sha256(b'').hexdigest()[:16]}")
    attempt["solver"].update(selected_stock_ids=[], assigned_role_count=0,
                             role_fit_diagnostics={}, missing_roles=missing)
    audit = audit_architectures(result)
    assert audit["attempts_verified"]
    assert not audit["execution_verified"]
