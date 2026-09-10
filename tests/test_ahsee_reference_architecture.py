"""AHSEE reference coverage is not ingredient identity or perfume performance.

Fixture quantities are arbitrary software inputs, not a proposed formula.
"""

from __future__ import annotations

import pytest

from engine.pipeline.formula_state import build_formula_state
from engine.reference_contracts import (
    detect_reference_claim,
    evaluate_reference_contract,
)


CONTRACT_ID = "chanel_allure_homme_sport_eau_extreme_edp_official_architecture_v1"
SOURCE_URL = (
    "https://www.chanel.com/gb/fragrance/p/123560/"
    "allure-homme-sport-eau-extreme-eau-de-parfum-spray/"
)
SOURCE_CEILING = (
    "Official source supports four named facets only; composition and likeness remain unknown."
)
CORE = {
    "Red Mandarin EO": 100.0,
    "Cypress EO": 100.0,
    "Galaxolide": 100.0,
    "Coumarin": 100.0,
}


def formula(scope: str = "architecture", contract: str = CONTRACT_ID) -> dict:
    return {
        "name": "AHSEE Architecture Study",
        "body": (
            "**Claim mode:** named_reference\n"
            f"**Reference contract:** {contract}\n"
            f"**Reference scope:** {scope}\n"
            f"{SOURCE_CEILING}\n"
        ),
    }


def evaluate(materials: dict[str, float] | None = None, scope: str = "architecture") -> dict:
    state = build_formula_state(CORE if materials is None else materials)
    return evaluate_reference_contract(formula(scope), state)


def ahsee_evaluation(result: dict) -> dict:
    evaluations = result["data"].get("evaluations", [])
    matching = [item for item in evaluations if item["contract_id"] == CONTRACT_ID]
    assert len(matching) == 1, result
    return matching[0]


@pytest.mark.parametrize(
    "alias",
    [CONTRACT_ID, "AHSEE", "Chanel Allure Homme Sport Eau Extreme", "Allure Homme Sport Eau Extrême"],
)
def test_exact_ahsee_names_resolve_without_promoting_source_ceiling(alias):
    detection = detect_reference_claim(formula(contract=alias))
    assert detection.status == "PASS"
    assert detection.contract_ids == (CONTRACT_ID,)
    assert detection.scope == "architecture"
    assert detection.quantitative_requested is False


@pytest.mark.parametrize(
    "other_name",
    ["AHS", "Allure Homme Sport", "Allure Homme Sport EDT", "Chanel Allure Homme", "Bleu de Chanel", "Dior Homme Intense"],
)
def test_edt_and_other_perfume_names_do_not_acquire_ahsee_reference(other_name):
    detection = detect_reference_claim({"name": other_name, "body": "Reference architecture study."})
    assert CONTRACT_ID not in detection.detected_targets
    explicit = detect_reference_claim(formula(contract=other_name))
    assert CONTRACT_ID not in explicit.contract_ids


def test_complete_name_coverage_reports_no_performance_or_dose_authority():
    result = evaluate()
    assert result["status"] == "PASS"
    item = ahsee_evaluation(result)
    assert set(item["matched_groups"]) == {"mandarin", "cypress", "white_musk", "almond_tonka"}
    assert item["missing_groups"] == []
    assert item["coverage_basis"] == "NAME_FACET_COVERAGE_ONLY"
    assert item["relational_performance"] == "NOT_TESTED"
    assert item["sensory_performance"] == "NOT_TESTED"
    assert item["authority"] == {
        "source_ingredient_identity": False,
        "source_formula_proportions": False,
        "dose": False,
        "quantitative_similarity": False,
        "sensory_similarity": False,
        "relational_performance": False,
        "physical_compounding": False,
        "safety": False,
    }
    assert "coverage only" in result["detail"].lower()
    assert "untested" in result["detail"].lower()


@pytest.mark.parametrize(
    "removed,missing",
    [("Red Mandarin EO", "mandarin"), ("Cypress EO", "cypress"), ("Galaxolide", "white_musk"), ("Coumarin", "almond_tonka")],
)
def test_missing_each_official_facet_fails_coverage(removed, missing):
    result = evaluate({name: amount for name, amount in CORE.items() if name != removed})
    assert result["status"] == "FAIL"
    assert ahsee_evaluation(result)["missing_groups"] == [missing]


@pytest.mark.parametrize(
    "removed,replacement,missing",
    [
        ("Red Mandarin EO", "Bergamot FCF oil Sicilian", "mandarin"),
        ("Cypress EO", "Cedarwood oil Virginia", "cypress"),
        ("Galaxolide", "Hedione", "white_musk"),
        ("Coumarin", "Vanillin", "almond_tonka"),
    ],
)
def test_unrelated_role_candidates_cannot_replace_official_facets(removed, replacement, missing):
    materials = {name: amount for name, amount in CORE.items() if name != removed}
    materials[replacement] = 100.0
    result = evaluate(materials)
    assert result["status"] == "FAIL"
    assert missing in ahsee_evaluation(result)["missing_groups"]


@pytest.mark.parametrize("scope", ["sensory_similarity", "quantitative_similarity"])
def test_official_facets_cannot_authorize_stronger_reference_scope(scope):
    result = evaluate(scope=scope)
    assert result["status"] == "FAIL"
    item = ahsee_evaluation(result)
    assert "cannot authorize" in item["scope_error"]
    assert item["authority"][scope] is False


def test_spearmint_declaration_is_recorded_separately_from_required_facets():
    result = evaluate()
    item = ahsee_evaluation(result)
    assert result["status"] == "PASS"
    assert item["all_group_names"] == ["mandarin", "cypress", "white_musk", "almond_tonka"]
    declaration = item["ingredient_declarations"][0]
    assert declaration["inci_name"] == "MENTHA VIRIDIS LEAF OIL"
    assert declaration["source_url"] == SOURCE_URL
    assert declaration["label_code"] == "PS000069A"
    assert declaration["evidence_class"] == "OFFICIAL_INGREDIENT_DECLARATION_ONLY"
    assert declaration["required_architecture_facet"] is False
    assert declaration["matched_materials"] == []
    assert item["non_equivalent_mappings"] == []


def test_peppermint_is_reported_as_non_equivalent_and_never_matches_spearmint():
    result = evaluate({**CORE, "Peppermint Essential Oil": 100.0})
    item = ahsee_evaluation(result)
    assert result["status"] == "PASS"  # Four facets only; mint identity remains separate.
    assert item["ingredient_declarations"][0]["matched_materials"] == []
    mapping = item["non_equivalent_mappings"][0]
    assert mapping["source_target"] == "MENTHA VIRIDIS LEAF OIL"
    assert mapping["build_materials"] == ["peppermint essential oil"]
    assert mapping["status"] == "NON_EQUIVALENT_FUNCTIONAL_SUBSTITUTION_UNTESTED"
    assert mapping["identity_equivalent"] is False
    assert mapping["sensory_equivalent"] is False


def test_spearmint_name_presence_does_not_promote_ingredient_or_dose_authority():
    result = evaluate({**CORE, "Spearmint EO": 100.0})
    item = ahsee_evaluation(result)
    assert item["ingredient_declarations"][0]["matched_materials"] == ["spearmint eo"]
    assert item["authority"]["source_ingredient_identity"] is False
    assert item["authority"]["dose"] is False
    assert item["sensory_performance"] == "NOT_TESTED"


def test_changed_fixture_amounts_cannot_promote_name_coverage_to_performance():
    item = ahsee_evaluation(evaluate({name: amount * 10 for name, amount in CORE.items()}))
    assert item["coverage_basis"] == "NAME_FACET_COVERAGE_ONLY"
    assert item["relational_performance"] == "NOT_TESTED"
    assert item["authority"]["source_formula_proportions"] is False
    assert item["authority"]["quantitative_similarity"] is False
