from engine.pipeline.gates import ReleaseGateConfig, gate_formula
from engine.pipeline.interventions import build_intervention_contract
from engine.pipeline.oav_authority import OAVAuthorityRequest, analyze_oav_authority
from engine.pipeline.release_scoring import compute_unified_release_scores
from engine.knowledge.literature_rules import build_knowledge_rule_quality_contract


def _formula():
    return {
        "number": 1,
        "name": "Intervention Contract Test",
        "ingredients_ul": {
            "Bergamot FCF": 1800.0,
            "Lavender EO": 1200.0,
            "Hedione": 1200.0,
            "Iso E Super": 900.0,
            "Coumarin": 300.0,
            "Evernyl": 600.0,
        },
        "dilutions": {
            "Bergamot FCF": 1.0,
            "Lavender EO": 1.0,
            "Hedione": 1.0,
            "Iso E Super": 1.0,
            "Coumarin": 0.2,
            "Evernyl": 1.0,
        },
    }


def test_intervention_contract_exposes_required_sections():
    formula = _formula()
    authority = analyze_oav_authority(
        OAVAuthorityRequest(
            formula_name=formula["name"],
            ingredients_ul=formula["ingredients_ul"],
            dilutions=formula["dilutions"],
            batch_volume_ml=30.0,
        )
    )
    gate_report = gate_formula(formula, ReleaseGateConfig(audit_enabled=False)).as_dict()
    scoring = compute_unified_release_scores(formula, authority, gate_report).as_dict()
    report = {
        **gate_report,
        "scores": scoring["scores"],
        "industry_10": scoring["industry_10"],
    }

    contract = build_intervention_contract(formula, report, batch_volume_ml=30.0)

    assert "blocking_issues" in contract
    assert "deterministic_repairs" in contract
    assert "advisory_repairs" in contract
    assert "swap_candidates" in contract
    assert "confidence" in contract
    assert "provenance" in contract


def test_knowledge_rule_quality_contract_flags_degraded_entries():
    contract = build_knowledge_rule_quality_contract().as_dict()

    assert "status" in contract
    assert "total_entries" in contract
    assert "valid_entries" in contract
    assert "invalid_entries" in contract
    assert "generic_material_refs" in contract
    assert contract["total_entries"] > 0
