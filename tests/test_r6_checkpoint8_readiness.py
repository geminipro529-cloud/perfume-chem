import hashlib
import json
from pathlib import Path

import pytest

from engine.experiments.checkpoint8_readiness import (
    DEFAULT_PROTOCOL_PATH,
    Checkpoint8ContractError,
    evaluate_r6_checkpoint8_readiness,
)

EXPECTED_BLOCKERS = [
    "HOLD_CP8_CP7_RESEARCH_CHARACTERIZATION_INCOMPLETE",
    "HOLD_CP8_PHYSICAL_SENSORY_SAMPLES_UNAVAILABLE",
    "HOLD_CP8_SENSORY_PROTOCOL_BINDINGS_INCOMPLETE",
    "HOLD_CP8_EXACT_CONDITION_HUMAN_OBSERVATIONS_UNAVAILABLE",
    "PLEASANTNESS_NOT_ESTABLISHED",
    "PHYSICAL_LIKING_NOT_TESTED",
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def report() -> dict[str, object]:
    return evaluate_r6_checkpoint8_readiness()


def test_checkpoint8_finishes_software_sequence_but_holds_external_validation(
    report,
) -> None:
    assert report["status"] == "HOLD"
    assert report["checkpoint8_state"] == (
        "SOFTWARE_COMPLETE_SENSORY_EVIDENCE_INTAKE_HOLD"
    )
    assert report["sensory_evidence_state"] == (
        "HOLD_CP8_PHYSICAL_STUDY_OR_EXACT_SCOPE_EVIDENCE_INCOMPLETE"
    )
    assert report["project_phase"] == (
        "SOFTWARE_CHECKPOINT_SEQUENCE_COMPLETE_EXTERNAL_VALIDATION_PENDING"
    )
    assert report["input_integrity_state"] == "VERIFIED"
    assert report["formula_action"] == "NO_CHANGE"
    assert report["ranked_candidates"] == []
    assert report["best_observed_candidate"] is None
    assert report["experimental_recommendation"] is None
    assert report["shortlist_ordering"] == "UNORDERED_DIVERSE_SET"
    assert report["blockers"] == EXPECTED_BLOCKERS


def test_checkpoint8_requires_checkpoint7_pass_without_bypass(report) -> None:
    assert report["checkpoint7_prerequisite"] == {
        "required_state": "PASS_CP7_R6_RESEARCH_SAMPLE_CHARACTERIZED",
        "observed_state": (
            "HOLD_CP7_BUILD_MEASUREMENT_OR_APPLICABILITY_INCOMPLETE"
        ),
        "satisfied": False,
        "bypass_allowed": False,
    }


def test_checkpoint8_preserves_public_data_transfer_boundaries(report) -> None:
    external = report["external_evidence_boundary"]
    bierling = external["bierling_2025"]
    assert bierling["license"] == "CC BY 4.0"
    assert bierling["included_participant_codes"] == 1227
    assert bierling["included_odor_codes"] == 73
    assert bierling["published_headline_odor_count"] == 74
    assert bierling["included_nonempty_numeric_pleasantness_rows"] == 12005
    assert bierling["scope"] == "MONOMOLECULAR_ODORS_POPULATION_DATA"
    assert bierling["mixture_level_liking_data"] is False
    assert bierling["r6_formula_transfer_authorized"] is False
    assert bierling["r6_personal_liking_established"] is False

    ma = external["ma_2021"]
    assert ma["claim"] == "SOURCE_INTERNAL_CALIBRATION_ONLY"
    assert ma["unique_mixture_groups"] == 198
    assert ma["source_trial_rows"] == 222
    assert ma["best_predefined_pleasantness_rmse"] == "0.394525286290"
    assert ma["formula_prediction_authorized"] is False
    assert ma["cross_study_generalization_authorized"] is False
    assert ma["participant_level_inference_authorized"] is False
    assert ma["sensory_claim_authorized"] is False
    assert ma["r6_formula_transfer_authorized"] is False


def test_checkpoint8_real_hedonic_platform_abstains(report) -> None:
    platform = report["hedonic_platform"]
    assert platform["schema_version"] == "hedonic_evidence_platform_v4"
    assert platform["authority_ceiling"] == "withheld"
    assert platform["view_count"] == 0
    assert platform["decision_count"] == 0
    assert platform["unknown_fact_count"] == 1
    assert platform["native_criterion_count"] == 12
    assert platform["all_native_criteria_unknown"] is True
    assert platform["ranked_winner_available"] is False
    assert platform["claims_count"] == 8
    assert platform["prohibition_claim_count"] == 8
    assert "hedonic.liking" in platform["native_criterion_ids"]
    assert "hedonic.target_fidelity" in platform["native_criterion_ids"]


def test_checkpoint8_real_panel_contract_remains_unlocked(report) -> None:
    panel = report["panel_intake"]
    assert panel["exit_decision"] == "hold"
    assert panel["protocol_locked"] is False
    assert panel["required_binding_count"] == 9
    assert panel["bound_binding_count"] == 0
    assert panel["panel_gate_ids"] == [
        "discrimination",
        "agreement",
        "repeatability",
    ]
    assert panel["locked_panel_gate_count"] == 0
    assert panel["timepoints_seconds"] == []
    assert panel["repeat_count"] == 0
    assert panel["c0_exit_satisfied"] is False
    assert len(panel["binding_states"]) == 9
    assert all(
        item["state"] == "required_unbound" for item in panel["binding_states"]
    )
    assert panel["study_authorized"] is False
    assert panel["release_authority"] is False
    assert panel["model_calibration_authority"] is False


def test_checkpoint8_keeps_endpoints_separate(report) -> None:
    endpoint = report["endpoint_contract"]
    assert endpoint["pleasantness_endpoint"] == "pleasantness"
    assert endpoint["pairwise_liking_endpoint"] == (
        "exact_condition_preference_outcome"
    )
    assert endpoint["aversion_and_defect_endpoints_remain_separate"] is True
    assert endpoint["blotter_and_skin_domains_remain_separate"] is True
    assert endpoint["individual_and_population_liking_remain_separate"] is True
    assert endpoint["unlike_endpoints_may_not_be_summed"] is True
    assert endpoint["beauty_endpoint"] == "PROHIBITED_DERIVED_ENDPOINT"
    assert endpoint["pleasantness_state"] == "NOT_ESTABLISHED"
    assert endpoint["personal_liking_state"] == "NOT_TESTED"
    assert endpoint["population_liking_state"] == "NOT_TESTED"


def test_checkpoint8_quarantines_legacy_score_50(report) -> None:
    legacy = report["legacy_heuristic_quarantine"]
    assert legacy == {
        "empty_input_score": 50,
        "empty_input_class": "unknown",
        "coverage_status": "NO_ACTIVE_MATERIALS",
        "classification": "HEURISTIC_DIAGNOSTIC_INDEX",
        "ranking_status": "WITHHELD",
        "formula_optimization_authority": False,
        "sensory_validation_status": "NOT_ESTABLISHED",
        "full_formula_pleasantness_status": "NOT_ESTABLISHED",
        "pleasantness_class_scope": "FIXED_VALENCE_TABLE_SUBSET_ONLY",
        "may_populate_hedonic_platform_observations": False,
        "may_select_or_rank_r6": False,
    }


def test_checkpoint8_evidence_census_is_exactly_empty(report) -> None:
    assert report["evidence_census"] == {
        "physical_sample_receipt_count": 0,
        "locked_protocol_receipt_count": 0,
        "participant_qualification_receipt_count": 0,
        "exact_condition_observation_count": 0,
        "panel_performance_result_count": 0,
        "criterion_preference_view_count": 0,
        "population_preference_view_count": 0,
        "pareto_decision_state_count": 0,
        "ranked_candidate_count": 0,
    }
    assert all(not values for values in report["canonical_current_evidence"].values())


def test_checkpoint8_is_deterministic_read_only_and_authority_safe(report) -> None:
    before = _sha256(DEFAULT_PROTOCOL_PATH)
    repeated = evaluate_r6_checkpoint8_readiness()
    after = _sha256(DEFAULT_PROTOCOL_PATH)
    assert repeated == report
    assert before == after
    authority = report["authority"]
    assert authority["checkpoint8_intake_contract_record_authorized"] is True
    assert all(
        value is False
        for key, value in authority.items()
        if key != "checkpoint8_intake_contract_record_authorized"
    )
    assert all(value is False for value in report["side_effects"].values())
    assert repeated["report_sha256"] == report["report_sha256"]


def test_checkpoint8_rejects_authority_escalation(tmp_path: Path) -> None:
    changed = json.loads(DEFAULT_PROTOCOL_PATH.read_text(encoding="utf-8"))
    changed["authority"]["human_study_authorized"] = True
    path = tmp_path / "authority-escalation.json"
    path.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(Checkpoint8ContractError, match="authority boundary"):
        evaluate_r6_checkpoint8_readiness(protocol_path=path)


def test_checkpoint8_rejects_reduced_authority_or_side_effect_schema(
    tmp_path: Path,
) -> None:
    changed = json.loads(DEFAULT_PROTOCOL_PATH.read_text(encoding="utf-8"))
    changed["authority"].pop("participant_recruitment_authorized")
    path = tmp_path / "missing-authority-field.json"
    path.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(Checkpoint8ContractError, match="authority boundary"):
        evaluate_r6_checkpoint8_readiness(protocol_path=path)

    changed = json.loads(DEFAULT_PROTOCOL_PATH.read_text(encoding="utf-8"))
    changed["side_effects"].pop("human_observation_created")
    path = tmp_path / "missing-side-effect-field.json"
    path.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(Checkpoint8ContractError, match="side-effect boundary"):
        evaluate_r6_checkpoint8_readiness(protocol_path=path)


def test_checkpoint8_rejects_injected_human_evidence(tmp_path: Path) -> None:
    changed = json.loads(DEFAULT_PROTOCOL_PATH.read_text(encoding="utf-8"))
    changed["canonical_current_evidence"]["exact_condition_observations"] = [
        {"unreviewed": True}
    ]
    path = tmp_path / "injected-human-evidence.json"
    path.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(Checkpoint8ContractError, match="must remain empty"):
        evaluate_r6_checkpoint8_readiness(protocol_path=path)


def test_checkpoint8_rejects_public_dataset_transfer_promotion(
    tmp_path: Path,
) -> None:
    changed = json.loads(DEFAULT_PROTOCOL_PATH.read_text(encoding="utf-8"))
    changed["external_evidence_boundary"]["bierling_2025"][
        "r6_formula_transfer_authorized"
    ] = True
    path = tmp_path / "bierling-transfer-promotion.json"
    path.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(Checkpoint8ContractError, match="Bierling transfer boundary"):
        evaluate_r6_checkpoint8_readiness(protocol_path=path)

    changed = json.loads(DEFAULT_PROTOCOL_PATH.read_text(encoding="utf-8"))
    changed["external_evidence_boundary"]["ma_2021"][
        "formula_prediction_authorized"
    ] = True
    path = tmp_path / "ma-transfer-promotion.json"
    path.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(Checkpoint8ContractError, match="Ma transfer boundary"):
        evaluate_r6_checkpoint8_readiness(protocol_path=path)


def test_checkpoint8_rejects_legacy_heuristic_promotion(tmp_path: Path) -> None:
    changed = json.loads(DEFAULT_PROTOCOL_PATH.read_text(encoding="utf-8"))
    changed["legacy_heuristic_quarantine"]["may_select_or_rank_r6"] = True
    path = tmp_path / "legacy-promotion.json"
    path.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(Checkpoint8ContractError, match="legacy heuristic authority"):
        evaluate_r6_checkpoint8_readiness(protocol_path=path)


def test_checkpoint8_rejects_scientific_implementation_drift(
    tmp_path: Path,
) -> None:
    changed = json.loads(DEFAULT_PROTOCOL_PATH.read_text(encoding="utf-8"))
    changed["scientific_surface"]["hedonic_platform"]["sha256"] = "0" * 64
    path = tmp_path / "scientific-drift.json"
    path.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(Checkpoint8ContractError, match="hash drift"):
        evaluate_r6_checkpoint8_readiness(protocol_path=path)


def test_checkpoint8_rejects_winner_or_formula_action_promotion(
    tmp_path: Path,
) -> None:
    changed = json.loads(DEFAULT_PROTOCOL_PATH.read_text(encoding="utf-8"))
    changed["checkpoint8_contract"]["ranked_candidates"] = ["R6"]
    changed["checkpoint8_contract"]["best_observed_candidate"] = "R6"
    path = tmp_path / "winner-promotion.json"
    path.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(Checkpoint8ContractError, match="outcome contract"):
        evaluate_r6_checkpoint8_readiness(protocol_path=path)
