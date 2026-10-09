"""Adversarial binding checks for executable comparison receipts, not scent scores."""

import copy
from dataclasses import fields
from functools import lru_cache

import pytest

from engine.formulation_intelligence import architecture_bridge as bridge
from engine.formulation_intelligence.semantic_brief_adapter import SemanticRole
from engine.research.subtype_benchmark import architecture_pair_is_safe, audit_architectures


@lru_cache(maxsize=1)
def _design():
    from engine.research.formula_design import design_inventory_formula

    return design_inventory_formula(
        idea="A juicy lychee fruit perfume", design_mode="DEEP_COMPOSE", max_materials=12,
    )


@pytest.mark.parametrize("fault", [
    "missing_kind", "unknown_kind", "stock_kind", "option", "template",
    "template_hash", "policy_hash", "lineage", "label", "plan_hash",
    "candidate_binding", "protected_role",
])
def test_internally_consistent_but_unbound_branch_cannot_pass(fault):
    original = _design()
    result = copy.deepcopy(original)
    variant = result["design_variants"][1]
    binding = variant["architecture"]
    if fault == "missing_kind":
        binding.pop("kind")
    elif fault == "unknown_kind":
        binding["kind"] = "SELF_ATTESTED"
    elif fault == "stock_kind":
        binding["kind"] = "STOCK_ALTERNATIVE_SAME_ROLE_PLAN"
    elif fault == "option":
        binding["option_id"] = "not_a_registered_option"
    elif fault == "template":
        binding["template_id"] = "skin_musk"
    elif fault == "template_hash":
        binding["template_sha256"] = "0" * 64
    elif fault == "policy_hash":
        binding["allocation_policy_sha256"] = "0" * 64
    elif fault == "lineage":
        binding["predecessor_sha256"] = "0" * 64
    elif fault == "label":
        binding["comparison_question"] = "A forged sensory claim"
    elif fault == "plan_hash":
        result["architecture_planning"]["plan_sha256"] = "0" * 64
    elif fault == "candidate_binding":
        result["architecture_planning"]["candidates"][0]["role_id"] = "forged"
    else:
        variant["role_plan"][0]["share"] += 0.013
        # Rehash the forgery and keep the self-attested preservation boolean.
        signature = bridge.role_plan_signature(tuple(SemanticRole(**r) for r in variant["role_plan"]))
        variant["role_plan_sha256"] = signature
        binding["role_plan_sha256"] = signature
        binding["protected_and_prompt_roles_unchanged"] = True
    assert set(variant["role_plan"][0]) == {f.name for f in fields(SemanticRole)}
    assert not architecture_pair_is_safe(audit_architectures(original), audit_architectures(result))


@pytest.mark.parametrize("field", ["basis_state", "separate_totals", "solver", "critic"])
def test_full_control_preservation_detects_non_dose_mutations(field):
    from engine.research.subtype_benchmark import control_is_preserved

    result = copy.deepcopy(_design())
    before = audit_architectures(result)
    control = result["design_variants"][0]
    if field in {"basis_state", "separate_totals"}:
        control["formula"][field] = {"forged": True}
    else:
        control[field]["forged"] = True
    after = audit_architectures(result)
    assert before["variants"][0]["physical_composition_sha256"] == after["variants"][0]["physical_composition_sha256"]
    assert not control_is_preserved(before, after)


@pytest.mark.parametrize("duplicate_of", [0, 1])
def test_relabelled_physical_duplicate_cannot_count_as_a_distinct_alternative(duplicate_of):
    from engine.research.subtype_benchmark import viable_architectures_are_distinct

    result = copy.deepcopy(_design())
    assert viable_architectures_are_distinct(audit_architectures(result))
    result["design_variants"][2]["formula"] = copy.deepcopy(result["design_variants"][duplicate_of]["formula"])
    assert not viable_architectures_are_distinct(audit_architectures(result))


def test_self_reported_withholding_does_not_replace_a_replayed_critic():
    from engine.research.subtype_benchmark import viable_architectures_are_distinct

    result = copy.deepcopy(_design())
    baseline = audit_architectures(result)
    assert architecture_pair_is_safe(baseline, baseline)
    for variant in result["design_variants"][1:]:
        variant["critic"]["state"] = "WITHHELD"
        variant["formula_action"] = "NO_CHANGE"
    audited = audit_architectures(result)
    assert not architecture_pair_is_safe(audited, audited)
    assert not audited["execution_verified"]
    assert all(v["viable_comparison"] is False for v in audited["variants"][1:])
    assert not viable_architectures_are_distinct(audited)
    result["design_variants"][1]["formula_action"] = "PROPOSAL_ONLY"
    assert not architecture_pair_is_safe(audited, audit_architectures(result))


def test_semantic_control_and_output_evidence_must_agree():
    result = copy.deepcopy(_design())
    result["semantic_brief"] = copy.deepcopy(result["semantic_brief"])
    result["semantic_brief"]["knowledge_context"]["pack_sha256"] = "0" * 64
    assert audit_architectures(result)["planning_verified"] is False


@pytest.mark.parametrize("fault", [
    "empty_rows", "liquid_total", "mass_total", "basis", "nan", "boolean",
    "negative", "zero", "fraction", "unit", "operation", "missing_stock",
])
def test_empty_or_inconsistent_physical_formula_cannot_count_as_viable(fault):
    result = copy.deepcopy(_design())
    formula = result["design_variants"][1]["formula"]
    row = formula["rows"][0]
    if fault == "empty_rows":
        formula["rows"] = []
    elif fault in {"liquid_total", "mass_total"}:
        formula["separate_totals"]["liquid_total_ul" if fault == "liquid_total" else "mass_total_mg"] = "1"
    elif fault == "basis":
        formula["basis_state"] = "MIXED_MASS_AND_VOLUME_SUM"
    elif fault in {"nan", "boolean", "negative", "zero"}:
        row["amount_decimal"] = {"nan": "NaN", "boolean": True, "negative": "-1", "zero": "0"}[fault]
    elif fault == "fraction":
        row["stock_fraction_decimal"] = "1.01"
    elif fault == "unit":
        row["amount_unit"] = "mg"
    elif fault == "operation":
        row["operation"] = "INFER_CRYSTAL_VOLUME"
    else:
        row["stock_id"] = ""
    audited = audit_architectures(result)
    assert not audited["variants"][1]["physical_formula_verified"]
    assert not audited["variants"][1]["viable_comparison"]
    assert not architecture_pair_is_safe(audited, audited)


@pytest.mark.parametrize("split", [False, True])
def test_equal_decimal_spellings_and_split_rows_are_the_same_composition(split):
    from decimal import Decimal

    from engine.research.subtype_benchmark import viable_architectures_are_distinct

    result = copy.deepcopy(_design())
    formula = copy.deepcopy(result["design_variants"][0]["formula"])
    row = formula["rows"][0]
    if split:
        row["amount_decimal"] = str(Decimal(row["amount_decimal"]) / 2)
        formula["rows"].append(copy.deepcopy(row))
    def respell(value: str) -> str:
        # Same number, more digits: a 1/3 stock must not be rounded to 0.3333.
        plain = format(Decimal(value), "f")
        return plain + ("0000" if "." in plain else ".0000")

    for row in formula["rows"]:
        row["amount_decimal"] = respell(row["amount_decimal"])
        row["stock_fraction_decimal"] = respell(row["stock_fraction_decimal"])
    result["design_variants"][2]["formula"] = formula
    receipt = audit_architectures(result)
    assert receipt["variants"][2]["physical_formula_verified"]
    assert receipt["variants"][2]["physical_composition_sha256"] == receipt["variants"][0]["physical_composition_sha256"]
    assert not viable_architectures_are_distinct(receipt)


def test_frozen_case_binds_interpretation_not_only_returned_plan():
    from engine.formulation_intelligence.formula_design_runtime import design_formula

    case = {
        "case_id": "request_binding", "brief": "A honeyed orange blossom perfume",
        "must_avoid": ["indole", "indolic"], "must_preserve": ["orange blossom"],
    }
    result = design_formula(
        formula_name="Architecture diagnostic request_binding", idea=case["brief"],
        design_mode="DEEP_COMPOSE", variant_count=3, max_materials=12,
        liquid_concentrate_ul_decimal="6000", must_avoid=tuple(case["must_avoid"]),
        must_preserve=tuple(case["must_preserve"]),
    )
    assert audit_architectures(result, expected_case=case, variant_count=3)["request_contract_verified"]
    for key, value in (
        ("must_avoid", ["rose"]), ("must_preserve", ["jasmine"]),
        ("brief", "A different request"), ("case_id", "a_different_case"),
    ):
        changed = {**case, key: value}
        assert not audit_architectures(result, expected_case=changed, variant_count=3)["request_contract_verified"]
    assert not audit_architectures(result, expected_case=case, variant_count=1)["request_contract_verified"]
