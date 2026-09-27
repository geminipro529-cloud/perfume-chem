import hashlib
import json
from pathlib import Path

import pytest

from engine.experiments.checkpoint7_readiness import (
    DEFAULT_PROTOCOL_PATH,
    Checkpoint7ContractError,
    evaluate_r6_checkpoint7_readiness,
)

EXPECTED_BLOCKERS = [
    "HOLD_CP7_CP6_PHYSICAL_READINESS_INCOMPLETE",
    "HOLD_CP7_RESEARCH_SAMPLE_NOT_COMPOUNDED",
    "HOLD_CP7_MEASUREMENT_EXECUTION_PARAMETERS_UNRESOLVED",
    "HOLD_CP7_MEASURED_GAS_INPUTS_UNAVAILABLE",
    "HOLD_EXACT_CURVE_APPLICABILITY",
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def report() -> dict[str, object]:
    return evaluate_r6_checkpoint7_readiness()


def test_checkpoint7_completes_software_intake_but_holds_research_execution(
    report,
) -> None:
    assert report["status"] == "HOLD"
    assert report["checkpoint7_state"] == (
        "SOFTWARE_COMPLETE_RESEARCH_APPLICABILITY_INTAKE_HOLD"
    )
    assert report["research_applicability_state"] == (
        "HOLD_CP7_BUILD_MEASUREMENT_OR_APPLICABILITY_INCOMPLETE"
    )
    assert report["input_integrity_state"] == "VERIFIED"
    assert report["formula_action"] == "DESIGN_SUCCESSOR_UNCHANGED"
    assert report["physical_build_state"] == "NOT_BOUND"
    assert report["research_sample_state"] == "NOT_COMPOUNDED"
    assert report["measurement_execution_state"] == "NOT_STARTED"
    assert report["exact_curve_applicability_state"] == (
        "HOLD_EXACT_CURVE_APPLICABILITY"
    )
    assert report["blockers"] == EXPECTED_BLOCKERS


def test_checkpoint7_requires_checkpoint6_physical_pass_without_bypass(
    report,
) -> None:
    assert report["checkpoint6_prerequisite"] == {
        "required_state": "PASS_CP6_PHYSICAL_READINESS_BOUND_NOT_COMPOUNDED",
        "observed_state": "HOLD_CP6_PHYSICAL_LINEAGE_INPUTS_INCOMPLETE",
        "satisfied": False,
        "bypass_allowed": False,
    }


def test_checkpoint7_curve_inventory_is_mathematical_not_admitted(report) -> None:
    capability = report["measured_intensity_capability"]
    assert capability["status"] == "HOLD"
    assert capability["reasons"] == [
        "HOLD_EXACT_IDENTITY_RANGE_MATRIX_BINDING"
    ]
    assert capability["curve_inventory"] == {
        "source_parameter_row_count": 314,
        "positive_evaluable_curve_count": 313,
        "nonpositive_slope_curve_count": 1,
        "nonpositive_slope_identity": "121-33-5",
        "identity_exact_count": 0,
        "identity_unadjudicated_count": 313,
        "identity_conflict_count": 1,
        "observed_range_bound_count": 0,
        "exact_material_binding_count": 0,
        "current_admission_state": "HOLD_EXACT_IDENTITY_RANGE_MATRIX_BINDING",
    }
    source = capability["literature_source_contract"]
    assert source["doi"] == "10.1021/acs.iecr.9b01225"
    assert source["correction_doi"] == "10.1021/acs.iecr.0c05822"
    assert source["commercial_use_authorized"] is False
    assert source["source_fit_overlap"] == "UNKNOWN"


def test_checkpoint7_abstains_for_every_r6_row(report) -> None:
    census = report["applicability_census"]
    assert census == {
        "formula_row_count": 63,
        "physical_sample_available_row_count": 0,
        "measured_gas_input_available_row_count": 0,
        "exact_curve_applicable_row_count": 0,
        "exact_curve_with_observed_range_row_count": 0,
        "exact_curve_with_matrix_delivery_scenario_row_count": 0,
        "whole_formula_curve_applicable": False,
        "mixture_challenger_executable": False,
    }
    rows = report["row_curve_applicability"]
    assert len(rows) == 63
    assert len({row["source_row"] for row in rows}) == 63
    assert all(row["physical_sample_available"] is False for row in rows)
    assert all(
        row["measured_gas_concentration_available"] is False for row in rows
    )
    assert all(row["exact_curve_binding_available"] is False for row in rows)
    assert all(
        row["curve_applicability_state"] == "HOLD_EXACT_CURVE_APPLICABILITY"
        for row in rows
    )


def test_checkpoint7_preserves_gas_input_and_release_model_boundaries(report) -> None:
    curve_input = report["curve_input_contract"]
    assert curve_input["physical_quantity"] == "GAS_MASS_CONCENTRATION"
    assert curve_input["phase"] == "AIR"
    assert curve_input["unit"] == "ug/L_air"
    assert curve_input["liquid_dose_allowed"] is False
    assert curve_input["stock_fraction_allowed"] is False
    assert curve_input["oav_allowed"] is False
    assert curve_input["modeled_unvalidated_release_as_measured_input_allowed"] is False
    assert curve_input["extrapolation_authorized"] is False

    boundary = report["release_model_boundary"]
    assert boundary["dynamic_release_authority"] == (
        "SIMULATION_ONLY_UNCALIBRATED"
    )
    assert boundary["dynamic_release_is_measured_headspace"] is False
    assert boundary["dynamic_release_is_calibrated_release"] is False
    assert boundary["dynamic_release_may_establish_curve_input"] is False
    assert boundary["headspace_oav_is_intensity"] is False
    assert boundary["headspace_oav_is_pleasantness"] is False
    assert boundary["headspace_oav_is_formula_quality"] is False


def test_checkpoint7_keeps_measurement_parameters_unresolved(report) -> None:
    measurement = report["measurement_protocol"]
    assert measurement["execution_ready"] is False
    assert measurement["domains_must_remain_separate"] == ["BLOTTER", "SKIN"]
    assert measurement["resolved_execution_parameters"] == {}
    assert measurement["unresolved_execution_parameter_count"] == 25
    assert len(measurement["unresolved_execution_parameters"]) == 25
    assert len(measurement["required_physical_parameters"]) == 17
    assert len(measurement["required_sensory_controls"]) == 8


def test_checkpoint7_keeps_mixture_models_and_endpoints_separate(report) -> None:
    mixture = report["mixture_challenger_contract"]
    assert mixture["models"] == [
        "STRONGEST_COMPONENT",
        "FITTED_PARTIAL_ADDITION",
        "PRIMACY_TRANSFER",
    ]
    assert mixture["models_remain_separate"] is True
    assert mixture["averaging_authorized"] is False
    assert mixture["missing_component_calibration_abstains_whole_mixture"] is True
    assert mixture["current_execution_authorized"] is False
    assert mixture["formula_optimization_authority"] is False
    assert report["endpoint_contract"] == {
        "physical_release": "NOT_MEASURED",
        "sensory_intensity": "NOT_ESTABLISHED",
        "character": "NOT_ESTABLISHED",
        "pleasantness": "NOT_ESTABLISHED",
        "personal_liking": "NOT_TESTED",
        "population_liking": "NOT_TESTED",
        "beauty": "PROHIBITED_DERIVED_ENDPOINT",
    }


def test_checkpoint7_is_deterministic_read_only_and_authority_safe(report) -> None:
    before = _sha256(DEFAULT_PROTOCOL_PATH)
    repeated = evaluate_r6_checkpoint7_readiness()
    after = _sha256(DEFAULT_PROTOCOL_PATH)
    assert repeated == report
    assert before == after
    authority = report["authority"]
    assert authority["checkpoint7_intake_contract_record_authorized"] is True
    assert all(
        value is False
        for key, value in authority.items()
        if key != "checkpoint7_intake_contract_record_authorized"
    )
    assert all(value is False for value in report["side_effects"].values())
    assert repeated["report_sha256"] == report["report_sha256"]


def test_checkpoint7_rejects_authority_escalation(tmp_path: Path) -> None:
    changed = json.loads(DEFAULT_PROTOCOL_PATH.read_text(encoding="utf-8"))
    changed["authority"]["measurement_execution_authorized"] = True
    path = tmp_path / "authority-escalation.json"
    path.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(Checkpoint7ContractError, match="authority boundary"):
        evaluate_r6_checkpoint7_readiness(protocol_path=path)


def test_checkpoint7_rejects_reduced_authority_or_side_effect_schema(
    tmp_path: Path,
) -> None:
    changed = json.loads(DEFAULT_PROTOCOL_PATH.read_text(encoding="utf-8"))
    changed["authority"].pop("measurement_execution_authorized")
    path = tmp_path / "missing-authority-field.json"
    path.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(Checkpoint7ContractError, match="authority boundary"):
        evaluate_r6_checkpoint7_readiness(protocol_path=path)

    changed = json.loads(DEFAULT_PROTOCOL_PATH.read_text(encoding="utf-8"))
    changed["side_effects"].pop("measurement_executed")
    path = tmp_path / "missing-side-effect-field.json"
    path.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(Checkpoint7ContractError, match="side-effect boundary"):
        evaluate_r6_checkpoint7_readiness(protocol_path=path)


def test_checkpoint7_rejects_injected_measurement_evidence(tmp_path: Path) -> None:
    changed = json.loads(DEFAULT_PROTOCOL_PATH.read_text(encoding="utf-8"))
    changed["canonical_current_evidence"]["measured_gas_observations"] = [
        {"unreviewed": True}
    ]
    path = tmp_path / "injected-evidence.json"
    path.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(Checkpoint7ContractError, match="must remain empty"):
        evaluate_r6_checkpoint7_readiness(protocol_path=path)


def test_checkpoint7_rejects_scientific_implementation_drift(
    tmp_path: Path,
) -> None:
    changed = json.loads(DEFAULT_PROTOCOL_PATH.read_text(encoding="utf-8"))
    changed["scientific_surface"]["dose_response_implementation"]["sha256"] = (
        "0" * 64
    )
    path = tmp_path / "scientific-drift.json"
    path.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(Checkpoint7ContractError, match="implementation hash drift"):
        evaluate_r6_checkpoint7_readiness(protocol_path=path)


def test_checkpoint7_rejects_proxy_promotion(tmp_path: Path) -> None:
    changed = json.loads(DEFAULT_PROTOCOL_PATH.read_text(encoding="utf-8"))
    changed["applicability_contract"]["proxy_curve_may_clear_checkpoint7"] = True
    path = tmp_path / "proxy-promotion.json"
    path.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(Checkpoint7ContractError, match="applicability authority"):
        evaluate_r6_checkpoint7_readiness(protocol_path=path)
