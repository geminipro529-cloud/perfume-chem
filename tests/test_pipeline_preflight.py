from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.preflight import run_release_preflight


def _formula():
    return {
        "name": "Preflight Test",
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


def test_release_preflight_fails_negative_input():
    formula = _formula()
    formula["ingredients_ul"]["Iso E Super"] = -1.0
    state = build_formula_state(formula["ingredients_ul"], formula["dilutions"], batch_volume_ml=30.0)
    report = run_release_preflight(formula, state).as_dict()
    normalization = next(check for check in report["checks"] if check.get("check_name") == "input_normalization")
    assert normalization["status"] == "FAIL"
