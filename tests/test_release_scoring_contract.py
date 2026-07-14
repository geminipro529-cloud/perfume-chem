from engine.pipeline.gates import ReleaseGateConfig, gate_formula
from engine.pipeline.oav_authority import OAVAuthorityRequest, analyze_oav_authority
from engine.pipeline.release_scoring import compute_unified_release_scores


def _formula():
    return {
        "number": 1,
        "name": "Unified Score Test",
        "ingredients_ul": {
            "Lavender EO": 700.0,
            "Hedione": 900.0,
            "Coumarin": 300.0,
            "Iso E Super": 1500.0,
        },
        "dilutions": {
            "Lavender EO": 1.0,
            "Hedione": 1.0,
            "Coumarin": 0.2,
            "Iso E Super": 1.0,
        },
    }


def test_unified_release_scoring_contract_has_provenance():
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
    payload = compute_unified_release_scores(formula, authority, gate_report).as_dict()

    assert "scores" in payload
    assert "industry_10" in payload
    assert "provenance" in payload
    assert "impact" in payload["industry_10"]
    assert "authority_rank_score" in payload["provenance"]
    assert "deterministic_sources" in payload["provenance"]
    assert "authoritative_inputs_used" in payload["provenance"]
    assert "heuristic_inputs_used" in payload["provenance"]
    assert "confidence_penalties" in payload["provenance"]
    assert "repairability" in payload["provenance"]
