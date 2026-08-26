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
    assert payload["science_penalty"] == 0.0
    assert (
        payload["provenance"]["formula_science_coverage"]["scope"]
        == "formula_runtime"
    )
    assert not any(
        row.get("reason") == "sparse_science_coverage"
        for row in payload["provenance"]["confidence_penalties"]
    )
    score_contract = payload["provenance"]["score_contract"]
    assert score_contract["classification"] == "HEURISTIC_DIAGNOSTIC_INDICES"
    assert score_contract["release_authority"] is False
    assert score_contract["release_authorized_axes"] == []
    assert (
        score_contract["axis_authority"]["longevity"]
        == "HEURISTIC_UNCALIBRATED_NOT_SKIN_LIFE"
    )
    assert (
        score_contract["axis_authority"]["sillage"]
        == "HEURISTIC_UNCALIBRATED_NOT_MEASURED_SILLAGE"
    )
    assert (
        score_contract["axis_authority"]["skin_performance"]
        == "HEURISTIC_UNVALIDATED_NOT_SKIN_OUTCOME"
    )
    assert all(
        0.0 <= value <= 100.0
        for key, value in payload["scores"].items()
        if not key.startswith("_")
    )
