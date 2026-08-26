from engine.pipeline import preflight as preflight_module
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.gates import (
    GateResult,
    ReleaseGateConfig,
    _apply_preflight_confidence_penalty,
)
from engine.pipeline.preflight import run_release_preflight


def _formula():
    return {
        "name": "Preflight Test",
        "ingredients_ul": {
            "Lavender EO (BONTAUX SAS)": 700.0,
            "Hedione": 900.0,
            "Coumarin": 300.0,
            "Iso E Super": 1500.0,
        },
        "dilutions": {
            "Lavender EO (BONTAUX SAS)": 1.0,
            "Hedione": 1.0,
            "Coumarin": 0.3,
            "Iso E Super": 1.0,
        },
    }


def test_release_preflight_contract_has_expected_checks():
    formula = _formula()
    state = build_formula_state(formula["ingredients_ul"], formula["dilutions"], batch_volume_ml=30.0)
    report = run_release_preflight(formula, state).as_dict()

    assert report["status"] in {"PASS", "WARN"}
    names = [check.get("check_name") for check in report["checks"]]
    assert "input_normalization" in names
    assert "knowledge_graph_schema" in names
    assert "literature_rule_contract" in names
    assert "knowledge_rule_quality" in names
    assert "odt_authority" in names
    assert "data_authority" in names
    assert "science_coverage" in names
    assert "material_identity_and_physics" in names
    assert report["confidence_penalty"] >= 0.0
    science = next(
        check for check in report["checks"]
        if check.get("check_name") == "science_coverage"
    )
    assert science["data"]["scope"] == "formula_runtime"
    assert science["data"]["confidence_penalty"] == 0.0
    assert (
        science["data"]["catalogue_context"]["formula_penalty_authority"]
        is False
    )


def test_formula_science_check_does_not_build_catalogue_audit(monkeypatch):
    from engine import science_audit

    formula = _formula()
    state = build_formula_state(
        formula["ingredients_ul"],
        formula["dilutions"],
        batch_volume_ml=30.0,
    )
    monkeypatch.setattr(
        science_audit,
        "build_science_audit_contract",
        lambda: (_ for _ in ()).throw(
            AssertionError("formula preflight must not scan the catalogue")
        ),
    )

    check, penalty = preflight_module._science_check(state)

    assert check.data["scope"] == "formula_runtime"
    assert check.data["catalogue_context"]["evaluated_in_formula_preflight"] is False
    assert penalty == 0.0
    assert check.data["confidence_penalty"] == 0.0


def test_total_preflight_penalty_is_not_mislabeled_as_science():
    confidence = {
        "combined_confidence": 60.0,
        "required_minimum": 25.0,
    }
    gate = GateResult(
        gate="confidence_minimum",
        status="PASS",
        detail="combined confidence 60.0",
        data=confidence,
    )
    preflight = {
        "confidence_penalty": 16.0,
        "checks": [
            {
                "check_name": "science_coverage",
                "data": {"confidence_penalty": 0.0},
            }
        ],
    }

    updated_gate, updated = _apply_preflight_confidence_penalty(
        gate,
        confidence,
        preflight,
        ReleaseGateConfig(),
    )

    assert updated["preflight_evidence_penalty"] == 16.0
    assert updated["science_preflight_penalty"] == 0.0
    assert updated["preflight_penalty_components"] == {
        "science_coverage": 0.0,
        "other_formula_evidence": 16.0,
    }
    assert "preflight evidence penalty 16.0" in updated_gate.detail
    assert "science penalty" not in updated_gate.detail


def test_release_preflight_fails_negative_input():
    formula = _formula()
    formula["ingredients_ul"]["Iso E Super"] = -1.0
    state = build_formula_state(formula["ingredients_ul"], formula["dilutions"], batch_volume_ml=30.0)
    report = run_release_preflight(formula, state).as_dict()
    normalization = next(check for check in report["checks"] if check.get("check_name") == "input_normalization")
    assert normalization["status"] == "FAIL"
