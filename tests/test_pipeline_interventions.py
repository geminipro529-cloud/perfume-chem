from engine.knowledge.literature_rules import build_knowledge_rule_quality_contract
from engine.pipeline.gates import ReleaseGateConfig, gate_formula
from engine.pipeline.interventions import (
    build_intervention_contract,
    diagnose_data_quality,
    diagnose_industry,
    diagnose_oav_table,
    diagnose_vp_pairs,
)
from engine.pipeline.oav_authority import OAVAuthorityRequest, analyze_oav_authority
from engine.pipeline.release_scoring import compute_unified_release_scores


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


def test_intervention_contract_advisory_generation_is_explicitly_selectable(monkeypatch):
    formula = _formula()
    report = {
        "industry_10": {},
        "oav_table": [],
        "gates": [],
        "scores": {},
        "confidence": {},
        "preflight": {},
    }
    calls = []

    def fake_generate(*args, **kwargs):
        calls.append((args, kwargs))
        return []

    monkeypatch.setattr(
        "engine.pipeline.interventions.generate_intervention_recommendations",
        fake_generate,
    )

    # Release and optimizer callers use the fast diagnostic-only mode. The
    # comparatively expensive heuristic search is an explicit opt-in.
    fast_contract = build_intervention_contract(
        formula,
        report,
        include_advisory_recommendations=False,
    )
    assert calls == []
    assert fast_contract["advisory_repairs"] == []
    assert fast_contract["swap_candidates"] == []
    assert fast_contract["provenance"]["advisory_status"] == "SKIPPED_NOT_REQUESTED"
    assert fast_contract["provenance"]["advisory_recommendations_requested"] is False

    full_contract = build_intervention_contract(
        formula,
        report,
        include_advisory_recommendations=True,
    )
    assert len(calls) == 1
    assert calls[0][1]["include_unvalidated_advisory"] is True
    assert full_contract["provenance"]["advisory_status"] == "COMPUTED"
    assert full_contract["provenance"]["advisory_recommendations_requested"] is True

    default_contract = build_intervention_contract(formula, report)
    assert len(calls) == 1
    assert default_contract["provenance"]["advisory_status"] == "SKIPPED_NOT_REQUESTED"


def test_diagnostic_scores_cannot_authorize_recompounding():
    formula = _formula()
    report = {
        "industry_10": {"tenacity": 0.0, "lift": 99.0},
        "oav_table": [
            {"name": "Ambrox Super", "oav": 20000.0, "note": "base"},
        ],
        "gates": [],
        "scores": {"total": 99.0},
        "confidence": {},
        "preflight": {},
        "ranking": {
            "status": "WITHHELD",
            "value": None,
            "formula_optimization_authority": False,
        },
    }

    contract = build_intervention_contract(
        formula,
        report,
        include_advisory_recommendations=False,
    )

    assert contract["blocking_issues"] == []
    assert contract["swap_candidates"] == []
    assert contract["provenance"]["formula_optimization_authority"] is False
    assert contract["provenance"]["ranking_status"] == "WITHHELD"


def test_gate_failure_blocks_release_without_authorizing_physical_change():
    report = {
        "industry_10": {},
        "oav_table": [],
        "gates": [
            {
                "gate": "safety_ifra_allergen",
                "status": "FAIL",
                "detail": "Finished-product safety assessment failed.",
            }
        ],
        "scores": {},
        "confidence": {},
        "preflight": {},
        "ranking": {
            "status": "WITHHELD",
            "formula_optimization_authority": False,
        },
    }

    contract = build_intervention_contract(
        _formula(),
        report,
        include_advisory_recommendations=False,
    )

    issue = contract["blocking_issues"][0]
    assert issue["blocks_release"] is True
    assert issue["remediation_required"] is True
    assert issue["compounding_action_authority"] is False
    assert issue["physical_change_authority"] is False
    repair = contract["deterministic_repairs"][0]
    assert repair["action"] == "cap_ifra_and_rebalance"
    assert repair["blocks_release"] is True
    assert repair["compounding_action_authority"] is False
    assert repair["physical_change_authority"] is False
    assert repair["requires_new_formula_version"] is True


def test_high_oav_is_not_called_overdose_or_used_as_dose_reduction_advice():
    issues = diagnose_oav_table(
        [
            {
                "name": "Ambrox Super",
                "oav": 20000.0,
                "screening_oav": 20000.0,
                "canonical_oav": None,
                "note": "base",
            }
        ]
    )

    assert len(issues) == 1
    issue = issues[0]
    assert issue["axis"] == "high_oav_screen"
    assert issue["compounding_action_authority"] is False
    assert issue["requires_controlled_comparison"] is True
    assert "does not by itself establish overdose" in issue["detail"]
    assert "Do not change" in issue["suggestion"]
    assert "reduce" not in issue["suggestion"].casefold()


def test_missing_diagnostic_values_are_unknown_not_neutral_or_zero():
    assert diagnose_industry({}) == []
    assert diagnose_industry(
        {
            "tenacity": None,
            "lift": None,
            "bloom": None,
            "character": None,
            "balance": None,
        }
    ) == []
    assert diagnose_oav_table(
        [{"name": "Unknown row", "oav": None, "note": "base", "role": "character"}]
    ) == []


def test_low_oav_screen_does_not_claim_functional_invisibility_or_auto_increase():
    issues = diagnose_oav_table(
        [
            {
                "name": "Quiet Character",
                "oav": 0.4,
                "canonical_oav": None,
                "active_ul": 10.0,
                "note": "heart",
                "role": "character",
            }
        ]
    )

    assert len(issues) == 1
    issue = issues[0]
    assert issue["axis"] == "modeled_detection_screen"
    assert issue["compounding_action_authority"] is False
    assert "not proof" in issue["detail"]
    assert "functionally invisible" in issue["detail"]
    assert "before increasing or replacing" in issue["suggestion"]


def test_vp_pair_diagnostic_requires_explicit_vp_and_canonical_oav():
    incomplete_rows = [
        {"name": "Missing VP", "vp_pa": None, "oav": 0.1, "canonical_oav": None},
        {"name": "Screening only", "vp_pa": 0.01, "oav": 0.1, "canonical_oav": None},
    ]
    assert diagnose_vp_pairs(incomplete_rows) == []

    issues = diagnose_vp_pairs(
        [
            {"name": "A", "vp_pa": 0.01, "canonical_oav": 0.2},
            {"name": "B", "vp_pa": 0.02, "canonical_oav": 0.3},
        ]
    )
    assert len(issues) == 1
    assert issues[0]["compounding_action_authority"] is False
    assert "does not establish" in issues[0]["detail"]
    assert "cannot volatilize" not in issues[0]["detail"].casefold()


def test_missing_bulk_odt_does_not_erase_an_available_composite_oav():
    assert diagnose_data_quality(
        [
            {
                "name": "Natural composite",
                "odt_air_ppm": None,
                "canonical_oav": 2.0,
            }
        ]
    ) == []

    issues = diagnose_data_quality(
        [{"name": "Unsupported", "odt_air_ppm": None, "canonical_oav": None}]
    )
    assert len(issues) == 1
    assert issues[0]["compounding_action_authority"] is False
    assert "does not block every formulation hypothesis" in issues[0]["detail"]


def test_knowledge_rule_quality_contract_flags_degraded_entries():
    contract = build_knowledge_rule_quality_contract().as_dict()

    assert "status" in contract
    assert "total_entries" in contract
    assert "valid_entries" in contract
    assert "invalid_entries" in contract
    assert "generic_material_refs" in contract
    assert contract["total_entries"] > 0
