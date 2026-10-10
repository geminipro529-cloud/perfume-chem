from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import pytest
from engine.calibration.hashing import stable_portable_file_hash as stable_file_hash

from app.services import engine_job_executor as engine_job_executor_module
from app.services import engine_jobs as engine_jobs_module
from app.services.engine_job_executor import execute_registered_engine_job
from app.services.engine_job_registry import validate_engine_payload
from app.services.engine_job_worker import (
    EngineJobChildTimeoutError,
    _execute_isolated,
)
from app.services.engine_jobs import (
    EngineJobConflictError,
    EngineJobError,
    build_engine_job_identity,
)
from app.services.lab_service import LabService


@pytest.fixture
def historical_shortlist_inventory(monkeypatch: pytest.MonkeyPatch) -> Path:
    """Exercise frozen protocols with their actual inputs, never fake hashes."""
    path = (
        Path(__file__).resolve().parents[1]
        / "fixtures/lavande_r5_shortlist_20260926/inventory.txt"
    )
    assert len(path.read_bytes().replace(b"\r\n", b"\n")) == 28251
    assert stable_file_hash(path) == (
        "1b4324da5a35cebe8c59959e58276d84"
        "ac8f2f0e0e6f3239fdef0a4250d8df71"
    )
    monkeypatch.setattr(engine_job_executor_module, "_INVENTORY_TEXT", path)
    return path


def test_shortlist_executor_rejects_real_inventory_drift(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, historical_shortlist_inventory: Path
) -> None:
    changed = tmp_path / "changed-inventory.txt"
    changed.write_bytes(historical_shortlist_inventory.read_bytes() + b"\nchanged test stock\n")
    monkeypatch.setattr(engine_job_executor_module, "_INVENTORY_TEXT", changed)
    manifest = Path(__file__).resolve().parents[3] / "data/governance/lavande_ambre_profond_r5_design_comparator_20260923.json"
    payload = validate_engine_payload("SHORTLIST_EVALUATION", {
        "endpoint_id": "measured_intensity_comparison",
        "candidates": [{"candidate_id": "controlled-drift", "lavender_share_decimal": "0.7", "ambrox_share_decimal": "0.3"}],
        "constant_total_basis": "UNRESOLVED",
        "comparator_manifest_sha256": stable_file_hash(manifest),
    })
    terminal, result, validation, _diagnostics = execute_registered_engine_job("SHORTLIST_EVALUATION", payload)
    assert terminal == "WITHHELD"
    assert validation == "HOLD_CP3_READINESS_PROTOCOL_DRIFT"
    assert result.get("ranked_candidates", []) == []
    assert result["release_authority"] is result["compounding_authority"] is False


def _formula_payload(*, amount: str = "100", reverse: bool = False) -> dict:
    rows = [
        {
            "row_id": "row-1",
            "material": "Linalool",
            "amount_decimal": amount,
            "amount_unit": "uL",
            "stock_id": "stock-linalool",
            "concentration_fraction_decimal": "1",
            "concentration_basis": "NEAT",
            "basket": "B1",
            "operation": "DIRECT_ADD",
        },
        {
            "row_id": "row-2",
            "material": "Hedione",
            "amount_decimal": "200",
            "amount_unit": "uL",
            "stock_id": "stock-hedione",
            "concentration_fraction_decimal": "1",
            "concentration_basis": "NEAT",
            "basket": "B2",
            "operation": "DIRECT_ADD",
        },
    ]
    if reverse:
        rows.reverse()
    return {
        "formula_id": "formula-fixture",
        "formula_name": "Fixture",
        "rows": rows,
        "final_volume_ml_decimal": "30.000",
    }


def test_registry_is_closed_and_row_order_participates_in_fingerprint() -> None:
    with pytest.raises(ValueError, match="UNSUPPORTED_ENGINE_JOB_TYPE"):
        validate_engine_payload("python.module:callable", {"shell": "whoami"})
    with pytest.raises(Exception):
        validate_engine_payload(
            "FORMULA_ANALYSIS", {**_formula_payload(), "module": "os"}
        )

    normal = build_engine_job_identity(
        job_type="FORMULA_ANALYSIS",
        payload=_formula_payload(),
        requester="fixture-requester",
        idempotency_key="first",
    )
    reversed_rows = build_engine_job_identity(
        job_type="FORMULA_ANALYSIS",
        payload=_formula_payload(reverse=True),
        requester="fixture-requester",
        idempotency_key="second",
    )
    assert normal["normalized_payload_sha256"] != reversed_rows[
        "normalized_payload_sha256"
    ]
    assert normal["job_fingerprint_sha256"] != reversed_rows[
        "job_fingerprint_sha256"
    ]
    assert normal["timeout_seconds"] == 90


@pytest.mark.parametrize("version", [3, 4])
def test_subtype_content_is_in_durable_job_reference_identity(monkeypatch, version) -> None:
    relative = f"data/formulation_knowledge/subtype_research_v{version}.json"
    assert relative in engine_jobs_module._research_reference_paths("FORMULA_ANALYSIS")
    assert relative in engine_jobs_module._research_reference_paths("FORMULA_DESIGN")
    before = build_engine_job_identity(
        job_type="FORMULA_ANALYSIS", payload=_formula_payload(),
        requester="fixture-requester", idempotency_key="subtype-fingerprint",
    )
    original_hash = engine_jobs_module.stable_file_hash
    exact_path = (engine_jobs_module.REPOSITORY_ROOT / relative).resolve()

    def changed_reference(path):
        return "e" * 64 if path.resolve() == exact_path else original_hash(path)

    monkeypatch.setattr(engine_jobs_module, "stable_file_hash", changed_reference)
    after = build_engine_job_identity(
        job_type="FORMULA_ANALYSIS", payload=_formula_payload(),
        requester="fixture-requester", idempotency_key="subtype-fingerprint",
    )
    assert before["normalized_payload_sha256"] == after["normalized_payload_sha256"]
    assert before["job_fingerprint_sha256"] != after["job_fingerprint_sha256"]


def test_release_gate_executor_runs_real_gate_and_mass_rows_fail_closed() -> None:
    release_payload = {
        **_formula_payload(),
        "expected_concentrate_ul_decimal": "300",
        "brief": "generic",
    }
    terminal, result, validation, _diagnostics = execute_registered_engine_job(
        "RELEASE_GATE",
        validate_engine_payload("RELEASE_GATE", release_payload),
    )
    assert terminal == "WITHHELD"
    assert validation == "WITHHOLD_RELEASE_GATE_FINDINGS"
    assert result["release_gate_diagnostic_complete"] is True
    assert result["gate_report"]["name"] == "Fixture"
    assert result["gate_report"]["gates"]
    assert result["release_authority"] is False

    mass_payload = {
        "formula_id": "r5-design",
        "formula_name": "R5 mixed physical basis",
        "rows": [
            {
                "row_id": "ambrox-solid",
                "material": "Ambrox Super",
                "amount_decimal": "300",
                "amount_unit": "mg",
                "concentration_fraction_decimal": "1",
                "concentration_basis": "NEAT",
                "basket": "W0",
                "operation": "MASS_ADD",
            }
        ],
        "expected_concentrate_ul_decimal": "5600",
        "brief": "generic",
    }
    terminal, result, validation, _diagnostics = execute_registered_engine_job(
        "RELEASE_GATE",
        validate_engine_payload("RELEASE_GATE", mass_payload),
    )
    assert terminal == "WITHHELD"
    assert validation == "HOLD_CONSTANT_TOTAL_BASIS_UNRESOLVED"
    assert result["release_gate_diagnostic_complete"] is False
    assert result["unsupported_mass_row_ids"] == ["ambrox-solid"]


def test_shortlist_executor_binds_the_exact_r5_manifest(
    historical_shortlist_inventory: Path,
) -> None:
    manifest_path = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "governance"
        / "lavande_ambre_profond_r5_design_comparator_20260923.json"
    )
    manifest_hash = stable_file_hash(manifest_path)
    readiness_path = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "governance"
        / "lavande_ambre_profond_r5_cp3_readiness_protocol_20260926_v5.json"
    )
    readiness_hash = stable_file_hash(readiness_path)
    successor_path = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "governance"
        / "lavande_ambre_profond_r6_aimi_design_successor_20260926.json"
    )
    successor_hash = stable_file_hash(successor_path)
    checkpoint5_path = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "governance"
        / "lavande_ambre_profond_r6_cp5_execution_input_protocol_20260926.json"
    )
    checkpoint5_hash = stable_file_hash(checkpoint5_path)
    checkpoint6_path = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "governance"
        / "lavande_ambre_profond_r6_cp6_physical_lineage_intake_20260926.json"
    )
    checkpoint6_hash = stable_file_hash(checkpoint6_path)
    checkpoint7_path = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "governance"
        / "lavande_ambre_profond_r6_cp7_research_applicability_intake_20260926.json"
    )
    checkpoint7_hash = stable_file_hash(checkpoint7_path)
    checkpoint8_path = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "governance"
        / "lavande_ambre_profond_r6_cp8_sensory_evidence_intake_20261009.json"
    )
    checkpoint8_hash = stable_file_hash(checkpoint8_path)
    base = {
        "endpoint_id": "measured_intensity_comparison",
        "candidates": [
            {
                "candidate_id": "candidate-1",
                "lavender_share_decimal": "0.7",
                "ambrox_share_decimal": "0.3",
            }
        ],
        "constant_total_basis": "UNRESOLVED",
    }
    terminal, result, validation, _diagnostics = execute_registered_engine_job(
        "SHORTLIST_EVALUATION",
        validate_engine_payload(
            "SHORTLIST_EVALUATION",
            {**base, "comparator_manifest_sha256": manifest_hash},
        ),
    )
    assert terminal == "WITHHELD"
    assert validation == "HOLD_CONSTANT_TOTAL_AMOUNT_AND_CONVERSION_INPUTS_MISSING"
    assert result["comparator_manifest_sha256"] == manifest_hash
    assert result["comparator_state"]["formula_action"] == "NO_CHANGE"
    assert result["checkpoint3_protocol_manifest_sha256"] == readiness_hash
    assert result["checkpoint3_readiness"]["baseline_state"] == (
        "R5_STANDALONE_BASELINE_ACCEPTED"
    )
    assert result["checkpoint3_readiness"]["parent_equivalence_state"] == (
        "NOT_CLAIMED_STANDALONE_BASELINE"
    )
    assert result["checkpoint3_readiness"]["revision_state"] == (
        "REVISED_SUCCESSOR_REQUIRED_SPECIFIC_CHANGE_UNRESOLVED"
    )
    assert result["checkpoint3_readiness"]["stock_binding_state"] == (
        "HOLD_STOCK_BINDING"
    )
    assert result["checkpoint3_readiness"]["measurement_protocol_state"] == (
        "FROZEN_SCHEMA_HOLD_EXECUTION_PARAMETERS"
    )
    assert result["checkpoint3_readiness"]["constant_total_basis_state"] == (
        "HOLD_CONSTANT_TOTAL_AMOUNT_AND_CONVERSION_INPUTS_MISSING"
    )
    assert "AMBROX_FORM_CONFLICT" not in result["checkpoint3_readiness"][
        "blockers"
    ]
    assert "VETIVERYL_STRENGTH_CONFLICT" not in result[
        "checkpoint3_readiness"
    ]["blockers"]
    assert (
        "NORLIMBANOL_BASIS_AND_DESIGN_CARRIER_MISMATCH"
        not in result["checkpoint3_readiness"]["blockers"]
    )
    assert "HOLD_REQUIRED_STOCK_DEPLETED_METHYL_IONONE_GAMMA_COEUR" in (
        result["checkpoint3_readiness"]["blockers"]
    )
    assert "HOLD_REQUIRED_WORKING_STOCKS_NOT_PREPARED" in result[
        "checkpoint3_readiness"
    ]["blockers"]
    assert "HOLD_PARENT_BYTES_MISSING" not in result["checkpoint3_readiness"][
        "blockers"
    ]
    assert all(
        value is False
        for value in result["checkpoint3_readiness"]["authority"].values()
    )
    checkpoint4 = result["checkpoint4_successor"]
    assert checkpoint4["successor_manifest_sha256"] == successor_hash
    assert checkpoint4["successor_id"] == (
        "lavande-ambre-profond-r6-aimi-design-successor-20260926"
    )
    assert checkpoint4["state"] == (
        "SOFTWARE_COMPLETE_DESIGN_SUCCESSOR_ADMITTED_PHYSICAL_READINESS_HOLD"
    )
    assert checkpoint4["formula_action"] == "DESIGN_SUCCESSOR_RECORDED"
    assert checkpoint4["substitution_state"] == (
        "AIMI_SELECTED_NOMINAL_50_UL_TRANSFER"
    )
    assert checkpoint4["active_equivalence_state"] == (
        "NOT_CLAIMED_INTENDED_MATERIAL_CHANGE"
    )
    assert checkpoint4["successor_rows_sha256"] == (
        "40889e8a43a780bf60d35a10fe4861a56f20d1a2a66e72141a5ceb8b8000eb4b"
    )
    assert checkpoint4["model_applicability"]["chemical_identity_state"] == (
        "HOLD_BOTTLE_TO_REFERENCE_IDENTITY_UNVERIFIED"
    )
    assert (
        "HOLD_REQUIRED_STOCK_DEPLETED_METHYL_IONONE_GAMMA_COEUR"
        not in checkpoint4["blockers"]
    )
    assert checkpoint4["authority"]["design_successor_record_authorized"] is True
    assert all(
        value is False
        for key, value in checkpoint4["authority"].items()
        if key != "design_successor_record_authorized"
    )
    checkpoint5 = result["checkpoint5_input_freeze"]
    assert (
        "data/governance/"
        "lavande_ambre_profond_r6_cp5_execution_input_protocol_20260926.json"
        in engine_jobs_module._CAPABILITY_PATHS
    )
    assert checkpoint5["protocol_manifest_sha256"] == checkpoint5_hash
    assert checkpoint5["protocol_state"] == (
        "FROZEN_NONEXECUTABLE_INPUT_COLLECTION_CONTRACT"
    )
    assert checkpoint5["checkpoint5_state"] == (
        "SOFTWARE_COMPLETE_INPUT_COLLECTION_HOLD"
    )
    assert checkpoint5["input_completion_state"] == "HOLD_CP5_INPUTS_INCOMPLETE"
    assert checkpoint5["formula_action"] == "DESIGN_SUCCESSOR_UNCHANGED"
    assert checkpoint5["aimi_scope"]["scope_state"] == (
        "BOTTLE_SPECIFIC_EMPIRICAL_REQUIRED"
    )
    assert checkpoint5["constant_total_basis"]["selected_basis"] == (
        "active_mass_g"
    )
    assert (
        checkpoint5["constant_total_basis"]["constant_total_amount_decimal"]
        is None
    )
    assert checkpoint5["measurement_protocol_state"] == (
        "R6_SCHEMA_FROZEN_EXECUTION_PARAMETERS_UNRESOLVED"
    )
    assert checkpoint5["blocker_ownership"] == (
        engine_job_executor_module._CP5_BLOCKER_OWNERSHIP
    )
    assert checkpoint5["authority"] == engine_job_executor_module._CP5_AUTHORITY
    checkpoint6 = result["checkpoint6_documentary_intake"]
    assert (
        "data/governance/"
        "lavande_ambre_profond_r6_cp6_physical_lineage_intake_20260926.json"
        in engine_jobs_module._CAPABILITY_PATHS
    )
    assert "engine/experiments/checkpoint6_readiness.py" in (
        engine_jobs_module._CAPABILITY_PATHS
    )
    assert checkpoint6["protocol_manifest_sha256"] == checkpoint6_hash
    assert checkpoint6["protocol_state"] == (
        "FROZEN_NONEXECUTING_DOCUMENTARY_INTAKE_CONTRACT"
    )
    assert checkpoint6["checkpoint6_state"] == (
        "SOFTWARE_COMPLETE_DOCUMENTARY_INTAKE_HOLD"
    )
    assert checkpoint6["documentary_input_completion_state"] == (
        "HOLD_CP6_PHYSICAL_LINEAGE_INPUTS_INCOMPLETE"
    )
    assert checkpoint6["documentary_census"] == {
        "candidate_stock_row_count": 63,
        "row_documentary_preconditions_complete_count": 0,
        "physical_binding_eligible_row_count": 0,
        "bottle_lot_receipt_missing_row_count": 63,
        "backend_stock_mapping_missing_row_count": 63,
        "liquid_conversion_missing_row_count": 62,
        "child_stock_preparation_missing_row_count": 3,
        "sub_10_ul_route_missing_row_count": 3,
    }
    assert checkpoint6["blockers"] == engine_job_executor_module._CP6_BLOCKERS
    assert checkpoint6["authority"] == engine_job_executor_module._CP6_AUTHORITY
    assert checkpoint6["side_effects"] == (
        engine_job_executor_module._CP6_SIDE_EFFECTS
    )
    checkpoint7 = result["checkpoint7_research_applicability_intake"]
    assert (
        "data/governance/"
        "lavande_ambre_profond_r6_cp7_research_applicability_intake_20260926.json"
        in engine_jobs_module._CAPABILITY_PATHS
    )
    assert "engine/experiments/checkpoint7_readiness.py" in (
        engine_jobs_module._CAPABILITY_PATHS
    )
    assert {
        "data/governance/measured_intensity_capabilities_20260923.json",
        "data/source_manifests/optimizer_sensory_research_20260909.json",
        "engine/dose_response.py",
        "engine/physics/dynamic_release.py",
        "engine/physics/headspace_oav.py",
        "output/optimizer_research_20260909/wakayama_2019/ie9b01225_si_001.pdf",
        "output/optimizer_research_20260909/wakayama_2019/wakayama-intensity.txt",
    }.issubset(set(engine_jobs_module._CAPABILITY_PATHS))
    assert checkpoint7["protocol_manifest_sha256"] == checkpoint7_hash
    assert checkpoint7["protocol_state"] == (
        "FROZEN_NONEXECUTING_RESEARCH_APPLICABILITY_INTAKE_CONTRACT"
    )
    assert checkpoint7["checkpoint7_state"] == (
        "SOFTWARE_COMPLETE_RESEARCH_APPLICABILITY_INTAKE_HOLD"
    )
    assert checkpoint7["research_applicability_state"] == (
        "HOLD_CP7_BUILD_MEASUREMENT_OR_APPLICABILITY_INCOMPLETE"
    )
    assert checkpoint7["applicability_census"] == {
        "formula_row_count": 63,
        "physical_sample_available_row_count": 0,
        "measured_gas_input_available_row_count": 0,
        "exact_curve_applicable_row_count": 0,
        "whole_formula_curve_applicable": False,
        "mixture_challenger_executable": False,
    }
    assert checkpoint7["curve_inventory"]["source_parameter_row_count"] == 314
    assert checkpoint7["curve_inventory"]["positive_evaluable_curve_count"] == 313
    assert checkpoint7["literature_source_contract"]["correction_doi"] == (
        "10.1021/acs.iecr.0c05822"
    )
    assert checkpoint7["literature_source_contract"][
        "commercial_use_authorized"
    ] is False
    assert checkpoint7["curve_input_contract"]["unit"] == "ug/L_air"
    assert checkpoint7["curve_input_contract"]["oav_allowed"] is False
    assert checkpoint7["release_model_boundary"][
        "dynamic_release_authority"
    ] == "SIMULATION_ONLY_UNCALIBRATED"
    assert checkpoint7["blockers"] == engine_job_executor_module._CP7_BLOCKERS
    assert checkpoint7["authority"] == engine_job_executor_module._CP7_AUTHORITY
    assert checkpoint7["side_effects"] == (
        engine_job_executor_module._CP7_SIDE_EFFECTS
    )
    checkpoint8 = result["checkpoint8_sensory_evidence_intake"]
    assert (
        "data/governance/"
        "lavande_ambre_profond_r6_cp8_sensory_evidence_intake_20261009.json"
        in engine_jobs_module._CAPABILITY_PATHS
    )
    assert "engine/experiments/checkpoint8_readiness.py" in (
        engine_jobs_module._CAPABILITY_PATHS
    )
    assert {
        "engine/formulation_intelligence/contracts.py",
        "engine/formulation_intelligence/hedonic_platform.py",
        "engine/sensory/panel_contract.py",
        "engine/hedonic_model.py",
        "engine/optimizer/scoring.py",
        "engine/formulation_intelligence/pleasantness.py",
        "engine/formulation_intelligence/pleasantness_table.py",
        "data/formulation_knowledge/pleasantness_crowd_v1.json",
        "data/governance/ma_2021_binary_mixture_baseline_benchmark_20260812.json",
        "docs/research/PERFUME_CHEM_C0_SENSORY_PANEL_CONTRACT_2026-08-09.md",
    }.issubset(set(engine_jobs_module._CAPABILITY_PATHS))
    assert checkpoint8["protocol_manifest_sha256"] == checkpoint8_hash
    assert checkpoint8["protocol_state"] == (
        "FROZEN_NONEXECUTING_SENSORY_EVIDENCE_INTAKE_CONTRACT"
    )
    assert checkpoint8["checkpoint8_state"] == (
        "SOFTWARE_COMPLETE_SENSORY_EVIDENCE_INTAKE_HOLD"
    )
    assert checkpoint8["sensory_evidence_state"] == (
        "HOLD_CP8_PHYSICAL_STUDY_OR_EXACT_SCOPE_EVIDENCE_INCOMPLETE"
    )
    assert checkpoint8["project_phase"] == (
        "SOFTWARE_CHECKPOINT_SEQUENCE_COMPLETE_EXTERNAL_VALIDATION_PENDING"
    )
    assert checkpoint8["hedonic_platform_contract"]["authority_ceiling"] == (
        "withheld"
    )
    assert checkpoint8["hedonic_platform_contract"]["view_count"] == 0
    assert checkpoint8["hedonic_platform_contract"][
        "ranked_winner_available"
    ] is False
    assert checkpoint8["panel_intake_contract"]["exit_decision"] == "hold"
    assert checkpoint8["panel_intake_contract"]["protocol_locked"] is False
    assert checkpoint8["panel_intake_contract"]["bound_binding_count"] == 0
    assert checkpoint8["endpoint_contract"]["pleasantness_state"] == (
        "NOT_ESTABLISHED"
    )
    assert checkpoint8["endpoint_contract"]["personal_liking_state"] == (
        "NOT_TESTED"
    )
    assert checkpoint8["legacy_heuristic_quarantine"]["empty_input_score"] == 50
    assert checkpoint8["legacy_heuristic_quarantine"]["ranking_status"] == (
        "WITHHELD"
    )
    assert checkpoint8["evidence_census"]["exact_condition_observation_count"] == 0
    assert checkpoint8["blockers"] == engine_job_executor_module._CP8_BLOCKERS
    assert checkpoint8["authority"] == engine_job_executor_module._CP8_AUTHORITY
    assert checkpoint8["side_effects"] == (
        engine_job_executor_module._CP8_SIDE_EFFECTS
    )

    terminal, result, validation, _diagnostics = execute_registered_engine_job(
        "SHORTLIST_EVALUATION",
        validate_engine_payload(
            "SHORTLIST_EVALUATION",
            {**base, "comparator_manifest_sha256": "1" * 64},
        ),
    )
    assert terminal == "WITHHELD"
    assert validation == "HOLD_COMPARATOR_MANIFEST_HASH_MISMATCH"
    assert result["ranked_candidates"] == []


def test_shortlist_executor_fails_closed_when_cp3_evidence_is_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    manifest_path = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "governance"
        / "lavande_ambre_profond_r5_design_comparator_20260923.json"
    )
    monkeypatch.setattr(
        engine_job_executor_module,
        "_R5_STOCK_CONFIRMATION",
        tmp_path / "missing-stock-confirmation.json",
    )
    payload = validate_engine_payload(
        "SHORTLIST_EVALUATION",
        {
            "comparator_manifest_sha256": stable_file_hash(manifest_path),
            "endpoint_id": "measured_intensity_comparison",
            "candidates": [
                {
                    "candidate_id": "candidate-1",
                    "lavender_share_decimal": "0.7",
                    "ambrox_share_decimal": "0.3",
                }
            ],
            "constant_total_basis": "UNRESOLVED",
        },
    )

    terminal, result, validation, _diagnostics = execute_registered_engine_job(
        "SHORTLIST_EVALUATION", payload
    )

    assert terminal == "WITHHELD"
    assert validation == "HOLD_CP3_READINESS_PROTOCOL_UNAVAILABLE"
    assert result["ranked_candidates"] == []
    assert result["formula_action"] == "NO_CHANGE"


def test_shortlist_executor_fails_closed_when_cp4_successor_is_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    manifest_path = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "governance"
        / "lavande_ambre_profond_r5_design_comparator_20260923.json"
    )
    monkeypatch.setattr(
        engine_job_executor_module,
        "_R6_AIMI_SUCCESSOR",
        tmp_path / "missing-aimi-successor.json",
    )
    payload = validate_engine_payload(
        "SHORTLIST_EVALUATION",
        {
            "comparator_manifest_sha256": stable_file_hash(manifest_path),
            "endpoint_id": "measured_intensity_comparison",
            "candidates": [
                {
                    "candidate_id": "candidate-1",
                    "lavender_share_decimal": "0.7",
                    "ambrox_share_decimal": "0.3",
                }
            ],
            "constant_total_basis": "UNRESOLVED",
        },
    )

    terminal, result, validation, _diagnostics = execute_registered_engine_job(
        "SHORTLIST_EVALUATION", payload
    )

    assert terminal == "WITHHELD"
    assert validation == "HOLD_CP4_AIMI_SUCCESSOR_UNAVAILABLE"
    assert result["ranked_candidates"] == []
    assert result["formula_action"] == "NO_CHANGE"


def test_shortlist_executor_fails_closed_when_cp5_input_freeze_is_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    manifest_path = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "governance"
        / "lavande_ambre_profond_r5_design_comparator_20260923.json"
    )
    monkeypatch.setattr(
        engine_job_executor_module,
        "_R6_CP5_INPUT_PROTOCOL",
        tmp_path / "missing-cp5-input-protocol.json",
    )
    payload = validate_engine_payload(
        "SHORTLIST_EVALUATION",
        {
            "comparator_manifest_sha256": stable_file_hash(manifest_path),
            "endpoint_id": "measured_intensity_comparison",
            "candidates": [
                {
                    "candidate_id": "candidate-1",
                    "lavender_share_decimal": "0.7",
                    "ambrox_share_decimal": "0.3",
                }
            ],
            "constant_total_basis": "UNRESOLVED",
        },
    )

    terminal, result, validation, _diagnostics = execute_registered_engine_job(
        "SHORTLIST_EVALUATION", payload
    )

    assert terminal == "WITHHELD"
    assert validation == "HOLD_CP5_INPUT_PROTOCOL_UNAVAILABLE"
    assert result["ranked_candidates"] == []
    assert result["formula_action"] == "NO_CHANGE"


def test_shortlist_executor_rejects_invalid_drifted_or_escalated_cp5_protocols(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, historical_shortlist_inventory: Path
) -> None:
    root = Path(__file__).resolve().parents[3]
    manifest_path = (
        root
        / "data"
        / "governance"
        / "lavande_ambre_profond_r5_design_comparator_20260923.json"
    )
    protocol_path = (
        root
        / "data"
        / "governance"
        / "lavande_ambre_profond_r6_cp5_execution_input_protocol_20260926.json"
    )
    payload = validate_engine_payload(
        "SHORTLIST_EVALUATION",
        {
            "comparator_manifest_sha256": stable_file_hash(manifest_path),
            "endpoint_id": "measured_intensity_comparison",
            "candidates": [
                {
                    "candidate_id": "candidate-1",
                    "lavender_share_decimal": "0.7",
                    "ambrox_share_decimal": "0.3",
                }
            ],
            "constant_total_basis": "UNRESOLVED",
        },
    )

    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("not-json", encoding="utf-8")
    monkeypatch.setattr(
        engine_job_executor_module,
        "_R6_CP5_INPUT_PROTOCOL",
        invalid_path,
    )
    terminal, result, validation, _diagnostics = execute_registered_engine_job(
        "SHORTLIST_EVALUATION", payload
    )
    assert terminal == "WITHHELD"
    assert validation == "HOLD_CP5_INPUT_PROTOCOL_INVALID"
    assert result["formula_action"] == "NO_CHANGE"

    drifted = json.loads(protocol_path.read_text(encoding="utf-8"))
    drifted["aimi_scope_contract"]["reference_linked_properties_allowed"] = True
    drifted_path = tmp_path / "drifted.json"
    drifted_path.write_text(json.dumps(drifted), encoding="utf-8")
    monkeypatch.setattr(
        engine_job_executor_module,
        "_R6_CP5_INPUT_PROTOCOL",
        drifted_path,
    )
    terminal, result, validation, _diagnostics = execute_registered_engine_job(
        "SHORTLIST_EVALUATION", payload
    )
    assert terminal == "WITHHELD"
    assert validation == "HOLD_CP5_INPUT_PROTOCOL_DRIFT"
    assert result["formula_action"] == "NO_CHANGE"

    escalated = json.loads(protocol_path.read_text(encoding="utf-8"))
    escalated["authority"]["compounding_authorized"] = True
    escalated_path = tmp_path / "escalated.json"
    escalated_path.write_text(json.dumps(escalated), encoding="utf-8")
    monkeypatch.setattr(
        engine_job_executor_module,
        "_R6_CP5_INPUT_PROTOCOL",
        escalated_path,
    )
    terminal, result, validation, _diagnostics = execute_registered_engine_job(
        "SHORTLIST_EVALUATION", payload
    )
    assert terminal == "WITHHELD"
    assert validation == "HOLD_CP5_INPUT_PROTOCOL_AUTHORITY_ESCALATION"
    assert result["formula_action"] == "NO_CHANGE"


def test_shortlist_executor_fails_closed_when_cp6_intake_is_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = Path(__file__).resolve().parents[3]
    manifest_path = (
        root
        / "data"
        / "governance"
        / "lavande_ambre_profond_r5_design_comparator_20260923.json"
    )
    monkeypatch.setattr(
        engine_job_executor_module,
        "_R6_CP6_LINEAGE_PROTOCOL",
        tmp_path / "missing-cp6-lineage-protocol.json",
    )
    payload = validate_engine_payload(
        "SHORTLIST_EVALUATION",
        {
            "comparator_manifest_sha256": stable_file_hash(manifest_path),
            "endpoint_id": "measured_intensity_comparison",
            "candidates": [
                {
                    "candidate_id": "candidate-1",
                    "lavender_share_decimal": "0.7",
                    "ambrox_share_decimal": "0.3",
                }
            ],
            "constant_total_basis": "UNRESOLVED",
        },
    )

    terminal, result, validation, _diagnostics = execute_registered_engine_job(
        "SHORTLIST_EVALUATION", payload
    )

    assert terminal == "WITHHELD"
    assert validation == "HOLD_CP6_LINEAGE_PROTOCOL_UNAVAILABLE"
    assert result["formula_action"] == "NO_CHANGE"


def test_shortlist_executor_rejects_invalid_drifted_or_escalated_cp6_protocols(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, historical_shortlist_inventory: Path
) -> None:
    root = Path(__file__).resolve().parents[3]
    manifest_path = (
        root
        / "data"
        / "governance"
        / "lavande_ambre_profond_r5_design_comparator_20260923.json"
    )
    protocol_path = (
        root
        / "data"
        / "governance"
        / "lavande_ambre_profond_r6_cp6_physical_lineage_intake_20260926.json"
    )
    payload = validate_engine_payload(
        "SHORTLIST_EVALUATION",
        {
            "comparator_manifest_sha256": stable_file_hash(manifest_path),
            "endpoint_id": "measured_intensity_comparison",
            "candidates": [
                {
                    "candidate_id": "candidate-1",
                    "lavender_share_decimal": "0.7",
                    "ambrox_share_decimal": "0.3",
                }
            ],
            "constant_total_basis": "UNRESOLVED",
        },
    )

    invalid_path = tmp_path / "invalid-cp6.json"
    invalid_path.write_text("not-json", encoding="utf-8")
    monkeypatch.setattr(
        engine_job_executor_module,
        "_R6_CP6_LINEAGE_PROTOCOL",
        invalid_path,
    )
    terminal, result, validation, _diagnostics = execute_registered_engine_job(
        "SHORTLIST_EVALUATION", payload
    )
    assert terminal == "WITHHELD"
    assert validation == "HOLD_CP6_LINEAGE_PROTOCOL_INVALID"
    assert result["formula_action"] == "NO_CHANGE"

    drifted = json.loads(protocol_path.read_text(encoding="utf-8"))
    drifted["candidate_identity_boundary"][
        "automatic_namespace_translation_allowed"
    ] = True
    drifted_path = tmp_path / "drifted-cp6.json"
    drifted_path.write_text(json.dumps(drifted), encoding="utf-8")
    monkeypatch.setattr(
        engine_job_executor_module,
        "_R6_CP6_LINEAGE_PROTOCOL",
        drifted_path,
    )
    terminal, result, validation, _diagnostics = execute_registered_engine_job(
        "SHORTLIST_EVALUATION", payload
    )
    assert terminal == "WITHHELD"
    assert validation == "HOLD_CP6_LINEAGE_PROTOCOL_DRIFT"
    assert result["formula_action"] == "NO_CHANGE"

    escalated = json.loads(protocol_path.read_text(encoding="utf-8"))
    escalated["authority"]["compounding_authorized"] = True
    escalated_path = tmp_path / "escalated-cp6.json"
    escalated_path.write_text(json.dumps(escalated), encoding="utf-8")
    monkeypatch.setattr(
        engine_job_executor_module,
        "_R6_CP6_LINEAGE_PROTOCOL",
        escalated_path,
    )
    terminal, result, validation, _diagnostics = execute_registered_engine_job(
        "SHORTLIST_EVALUATION", payload
    )
    assert terminal == "WITHHELD"
    assert validation == "HOLD_CP6_LINEAGE_PROTOCOL_AUTHORITY_ESCALATION"
    assert result["formula_action"] == "NO_CHANGE"


def test_shortlist_executor_fails_closed_when_cp7_intake_is_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, historical_shortlist_inventory: Path
) -> None:
    root = Path(__file__).resolve().parents[3]
    manifest_path = (
        root
        / "data"
        / "governance"
        / "lavande_ambre_profond_r5_design_comparator_20260923.json"
    )
    monkeypatch.setattr(
        engine_job_executor_module,
        "_R6_CP7_RESEARCH_PROTOCOL",
        tmp_path / "missing-cp7-research-protocol.json",
    )
    payload = validate_engine_payload(
        "SHORTLIST_EVALUATION",
        {
            "comparator_manifest_sha256": stable_file_hash(manifest_path),
            "endpoint_id": "measured_intensity_comparison",
            "candidates": [
                {
                    "candidate_id": "candidate-1",
                    "lavender_share_decimal": "0.7",
                    "ambrox_share_decimal": "0.3",
                }
            ],
            "constant_total_basis": "UNRESOLVED",
        },
    )

    terminal, result, validation, _diagnostics = execute_registered_engine_job(
        "SHORTLIST_EVALUATION", payload
    )

    assert terminal == "WITHHELD"
    assert validation == "HOLD_CP7_RESEARCH_PROTOCOL_UNAVAILABLE"
    assert result["ranked_candidates"] == []
    assert result["formula_action"] == "NO_CHANGE"


def test_shortlist_executor_rejects_invalid_drifted_or_escalated_cp7_protocols(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, historical_shortlist_inventory: Path
) -> None:
    root = Path(__file__).resolve().parents[3]
    manifest_path = (
        root
        / "data"
        / "governance"
        / "lavande_ambre_profond_r5_design_comparator_20260923.json"
    )
    protocol_path = (
        root
        / "data"
        / "governance"
        / "lavande_ambre_profond_r6_cp7_research_applicability_intake_20260926.json"
    )
    payload = validate_engine_payload(
        "SHORTLIST_EVALUATION",
        {
            "comparator_manifest_sha256": stable_file_hash(manifest_path),
            "endpoint_id": "measured_intensity_comparison",
            "candidates": [
                {
                    "candidate_id": "candidate-1",
                    "lavender_share_decimal": "0.7",
                    "ambrox_share_decimal": "0.3",
                }
            ],
            "constant_total_basis": "UNRESOLVED",
        },
    )

    invalid_path = tmp_path / "invalid-cp7.json"
    invalid_path.write_text("not-json", encoding="utf-8")
    monkeypatch.setattr(
        engine_job_executor_module,
        "_R6_CP7_RESEARCH_PROTOCOL",
        invalid_path,
    )
    terminal, result, validation, _diagnostics = execute_registered_engine_job(
        "SHORTLIST_EVALUATION", payload
    )
    assert terminal == "WITHHELD"
    assert validation == "HOLD_CP7_RESEARCH_PROTOCOL_INVALID"
    assert result["formula_action"] == "NO_CHANGE"

    drifted = json.loads(protocol_path.read_text(encoding="utf-8"))
    drifted["curve_input_contract"]["oav_allowed"] = True
    drifted_path = tmp_path / "drifted-cp7.json"
    drifted_path.write_text(json.dumps(drifted), encoding="utf-8")
    monkeypatch.setattr(
        engine_job_executor_module,
        "_R6_CP7_RESEARCH_PROTOCOL",
        drifted_path,
    )
    terminal, result, validation, _diagnostics = execute_registered_engine_job(
        "SHORTLIST_EVALUATION", payload
    )
    assert terminal == "WITHHELD"
    assert validation == "HOLD_CP7_RESEARCH_PROTOCOL_DRIFT"
    assert result["formula_action"] == "NO_CHANGE"

    escalated = json.loads(protocol_path.read_text(encoding="utf-8"))
    escalated["authority"]["compounding_authorized"] = True
    escalated_path = tmp_path / "escalated-cp7.json"
    escalated_path.write_text(json.dumps(escalated), encoding="utf-8")
    monkeypatch.setattr(
        engine_job_executor_module,
        "_R6_CP7_RESEARCH_PROTOCOL",
        escalated_path,
    )
    terminal, result, validation, _diagnostics = execute_registered_engine_job(
        "SHORTLIST_EVALUATION", payload
    )
    assert terminal == "WITHHELD"
    assert validation == "HOLD_CP7_RESEARCH_PROTOCOL_AUTHORITY_ESCALATION"
    assert result["formula_action"] == "NO_CHANGE"


def test_shortlist_executor_fails_closed_when_cp8_intake_is_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, historical_shortlist_inventory: Path
) -> None:
    root = Path(__file__).resolve().parents[3]
    manifest_path = (
        root
        / "data"
        / "governance"
        / "lavande_ambre_profond_r5_design_comparator_20260923.json"
    )
    monkeypatch.setattr(
        engine_job_executor_module,
        "_R6_CP8_SENSORY_PROTOCOL",
        tmp_path / "missing-cp8-sensory-protocol.json",
    )
    payload = validate_engine_payload(
        "SHORTLIST_EVALUATION",
        {
            "comparator_manifest_sha256": stable_file_hash(manifest_path),
            "endpoint_id": "measured_intensity_comparison",
            "candidates": [
                {
                    "candidate_id": "candidate-1",
                    "lavender_share_decimal": "0.7",
                    "ambrox_share_decimal": "0.3",
                }
            ],
            "constant_total_basis": "UNRESOLVED",
        },
    )

    terminal, result, validation, _diagnostics = execute_registered_engine_job(
        "SHORTLIST_EVALUATION", payload
    )

    assert terminal == "WITHHELD"
    assert validation == "HOLD_CP8_SENSORY_PROTOCOL_UNAVAILABLE"
    assert result["ranked_candidates"] == []
    assert result["formula_action"] == "NO_CHANGE"


def test_shortlist_executor_rejects_invalid_drifted_or_escalated_cp8_protocols(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, historical_shortlist_inventory: Path
) -> None:
    root = Path(__file__).resolve().parents[3]
    manifest_path = (
        root
        / "data"
        / "governance"
        / "lavande_ambre_profond_r5_design_comparator_20260923.json"
    )
    protocol_path = (
        root
        / "data"
        / "governance"
        / "lavande_ambre_profond_r6_cp8_sensory_evidence_intake_20261009.json"
    )
    payload = validate_engine_payload(
        "SHORTLIST_EVALUATION",
        {
            "comparator_manifest_sha256": stable_file_hash(manifest_path),
            "endpoint_id": "measured_intensity_comparison",
            "candidates": [
                {
                    "candidate_id": "candidate-1",
                    "lavender_share_decimal": "0.7",
                    "ambrox_share_decimal": "0.3",
                }
            ],
            "constant_total_basis": "UNRESOLVED",
        },
    )

    invalid_path = tmp_path / "invalid-cp8.json"
    invalid_path.write_text("not-json", encoding="utf-8")
    monkeypatch.setattr(
        engine_job_executor_module,
        "_R6_CP8_SENSORY_PROTOCOL",
        invalid_path,
    )
    terminal, result, validation, _diagnostics = execute_registered_engine_job(
        "SHORTLIST_EVALUATION", payload
    )
    assert terminal == "WITHHELD"
    assert validation == "HOLD_CP8_SENSORY_PROTOCOL_INVALID"
    assert result["formula_action"] == "NO_CHANGE"

    drifted = json.loads(protocol_path.read_text(encoding="utf-8"))
    drifted["legacy_heuristic_quarantine"]["may_select_or_rank_r6"] = True
    drifted_path = tmp_path / "drifted-cp8.json"
    drifted_path.write_text(json.dumps(drifted), encoding="utf-8")
    monkeypatch.setattr(
        engine_job_executor_module,
        "_R6_CP8_SENSORY_PROTOCOL",
        drifted_path,
    )
    terminal, result, validation, _diagnostics = execute_registered_engine_job(
        "SHORTLIST_EVALUATION", payload
    )
    assert terminal == "WITHHELD"
    assert validation == "HOLD_CP8_SENSORY_PROTOCOL_DRIFT"
    assert result["formula_action"] == "NO_CHANGE"

    evidence = json.loads(protocol_path.read_text(encoding="utf-8"))
    evidence["canonical_current_evidence"]["exact_condition_observations"] = [
        {"unreviewed": True}
    ]
    evidence_path = tmp_path / "evidence-cp8.json"
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    monkeypatch.setattr(
        engine_job_executor_module,
        "_R6_CP8_SENSORY_PROTOCOL",
        evidence_path,
    )
    terminal, result, validation, _diagnostics = execute_registered_engine_job(
        "SHORTLIST_EVALUATION", payload
    )
    assert terminal == "WITHHELD"
    assert validation == "HOLD_CP8_SENSORY_PROTOCOL_DRIFT"
    assert result["formula_action"] == "NO_CHANGE"

    superseded = json.loads(protocol_path.read_text(encoding="utf-8"))
    superseded["supersedes"]["sha256"] = "0" * 64
    superseded_path = tmp_path / "superseded-cp8.json"
    superseded_path.write_text(json.dumps(superseded), encoding="utf-8")
    monkeypatch.setattr(
        engine_job_executor_module,
        "_R6_CP8_SENSORY_PROTOCOL",
        superseded_path,
    )
    terminal, result, validation, _diagnostics = execute_registered_engine_job(
        "SHORTLIST_EVALUATION", payload
    )
    assert terminal == "WITHHELD"
    assert validation == "HOLD_CP8_SENSORY_PROTOCOL_DRIFT"
    assert result["formula_action"] == "NO_CHANGE"

    escalated = json.loads(protocol_path.read_text(encoding="utf-8"))
    escalated["authority"]["human_study_authorized"] = True
    escalated_path = tmp_path / "escalated-cp8.json"
    escalated_path.write_text(json.dumps(escalated), encoding="utf-8")
    monkeypatch.setattr(
        engine_job_executor_module,
        "_R6_CP8_SENSORY_PROTOCOL",
        escalated_path,
    )
    terminal, result, validation, _diagnostics = execute_registered_engine_job(
        "SHORTLIST_EVALUATION", payload
    )
    assert terminal == "WITHHELD"
    assert validation == "HOLD_CP8_SENSORY_PROTOCOL_AUTHORITY_ESCALATION"
    assert result["formula_action"] == "NO_CHANGE"


def test_worker_process_isolated_execution_and_hard_timeout() -> None:
    payload = validate_engine_payload("FORMULA_ANALYSIS", _formula_payload())
    terminal, result, validation, diagnostics = _execute_isolated(
        "FORMULA_ANALYSIS",
        payload,
        30,
    )
    assert terminal in {"SUCCEEDED", "WITHHELD"}
    assert result["formula_action"] == "NO_CHANGE"
    assert validation in {
        "ADVISORY_COMPLETE",
        "ADVISORY_FINDINGS",
        "WITHHOLD_UNKNOWN",
    }
    assert diagnostics["executor"] == "closed-registry-v1"

    with pytest.raises(EngineJobChildTimeoutError, match="ENGINE_JOB_TIMEOUT"):
        _execute_isolated("FORMULA_ANALYSIS", payload, 0)


@pytest.mark.asyncio
async def test_exact_idempotency_replay_coalescing_and_mismatch(db_session) -> None:
    service = LabService(db_session)
    first, reused = await service.submit_engine_job(
        job_type="FORMULA_ANALYSIS",
        payload=_formula_payload(),
        requester="fixture-requester",
        idempotency_key="same-key",
    )
    assert reused is False

    replay, reused = await service.submit_engine_job(
        job_type="FORMULA_ANALYSIS",
        payload=_formula_payload(),
        requester="fixture-requester",
        idempotency_key="same-key",
    )
    assert reused is True
    assert replay.id == first.id

    coalesced, reused = await service.submit_engine_job(
        job_type="FORMULA_ANALYSIS",
        payload=_formula_payload(),
        requester="fixture-requester",
        idempotency_key="different-key-same-command",
    )
    assert reused is True
    assert coalesced.id == first.id

    with pytest.raises(EngineJobConflictError) as raised:
        await service.submit_engine_job(
            job_type="FORMULA_ANALYSIS",
            payload=_formula_payload(amount="101"),
            requester="fixture-requester",
            idempotency_key="same-key",
        )
    assert raised.value.code == "IDEMPOTENCY_COMMAND_MISMATCH"


@pytest.mark.asyncio
async def test_worker_lifecycle_event_hash_chain_and_false_authority(db_session) -> None:
    service = LabService(db_session)
    job, _ = await service.submit_engine_job(
        job_type="FORMULA_ANALYSIS",
        payload=_formula_payload(),
        requester="fixture-requester",
        idempotency_key="lifecycle",
    )
    lease = await service.claim_next_engine_job(owner="worker-fixture", lease_seconds=30)
    assert lease is not None and lease.job.id == job.id
    await service.mark_engine_job_running(
        job_id=job.id, owner=lease.owner, token=lease.token
    )
    terminal, result, validation, diagnostics = execute_registered_engine_job(
        job.job_type, dict(job.normalized_payload_json)
    )
    await service.complete_engine_job(
        job_id=job.id,
        owner=lease.owner,
        token=lease.token,
        terminal_state=terminal,
        result=result,
        validation_state=validation,
        diagnostics=diagnostics,
    )

    snapshot = await service.engine_job_snapshot(job.id)
    assert snapshot["event_chain_verified"] is True
    assert snapshot["result_hash_verified"] is True
    assert snapshot["state"] in {"SUCCEEDED", "WITHHELD"}
    assert [event["state"] for event in snapshot["events"]] == [
        "QUEUED",
        "LEASED",
        "RUNNING",
        snapshot["state"],
    ]
    for parent, child in zip(snapshot["events"], snapshot["events"][1:]):
        assert child["parent_event_sha256"] == parent["event_sha256"]
    assert snapshot["result"] is not None
    for key in (
        "release_authority",
        "safety_authority",
        "compounding_authority",
        "evidence_admission_authorized",
    ):
        assert snapshot[key] is False
        assert snapshot["result"][key] is False
    assert await service.claim_next_engine_job(owner="second-worker") is None


@pytest.mark.asyncio
async def test_cancellation_wins_and_late_result_is_rejected(db_session) -> None:
    service = LabService(db_session)
    job, _ = await service.submit_engine_job(
        job_type="SHORTLIST_EVALUATION",
        payload={
            "comparator_manifest_sha256": "1" * 64,
            "endpoint_id": "measured_intensity_comparison",
            "candidates": [
                {
                    "candidate_id": "candidate-1",
                    "lavender_share_decimal": "0.7",
                    "ambrox_share_decimal": "0.3",
                }
            ],
            "constant_total_basis": "UNRESOLVED",
        },
        requester="fixture-requester",
        idempotency_key="cancel-race",
    )
    job_id = job.id
    lease = await service.claim_next_engine_job(owner="worker-fixture", lease_seconds=30)
    assert lease is not None
    await service.mark_engine_job_running(
        job_id=job_id, owner=lease.owner, token=lease.token
    )
    await service.cancel_engine_job(
        job_id=job_id,
        requester="fixture-requester",
        reason="fixture cancellation",
    )
    with pytest.raises(EngineJobConflictError) as raised:
        await service.complete_engine_job(
                job_id=job_id,
            owner=lease.owner,
            token=lease.token,
            terminal_state="WITHHELD",
            result={"status": "late"},
            validation_state="late",
        )
    assert raised.value.code == "ENGINE_JOB_LATE_RESULT_REJECTED"
    snapshot = await service.engine_job_snapshot(job_id)
    assert snapshot["state"] == "CANCELLED"
    assert snapshot["result"]["terminal_state"] == "CANCELLED"
    diagnostics = snapshot["result"]["diagnostics"]
    assert "reason" not in diagnostics
    assert len(diagnostics["request_reason_sha256"]) == 64


@pytest.mark.asyncio
async def test_expired_lease_fails_closed_once_without_retry(
    db_session, monkeypatch
) -> None:
    service = LabService(db_session)
    job, _ = await service.submit_engine_job(
        job_type="FORMULA_ANALYSIS",
        payload=_formula_payload(),
        requester="fixture-requester",
        idempotency_key="expire",
    )
    lease = await service.claim_next_engine_job(owner="worker-fixture", lease_seconds=30)
    assert lease is not None
    future = lease.expires_at + timedelta(seconds=1)
    monkeypatch.setattr(engine_jobs_module, "_utcnow", lambda: future)

    assert await service.fail_expired_engine_jobs() == 1
    snapshot = await service.engine_job_snapshot(job.id)
    assert snapshot["state"] == "FAILED"
    assert snapshot["result"]["validation_state"] == "FAILED_CLOSED_WORKER_LOST"
    assert snapshot["result"]["result"]["formula_action"] == "NO_CHANGE"
    assert await service.fail_expired_engine_jobs() == 0
    assert await service.claim_next_engine_job(owner="replacement-worker") is None


@pytest.mark.asyncio
async def test_invalid_payload_raises_stable_engine_job_error(db_session) -> None:
    with pytest.raises(EngineJobError) as raised:
        await LabService(db_session).submit_engine_job(
            job_type="FORMULA_ANALYSIS",
            payload={"module": "arbitrary"},
            requester="fixture-requester",
            idempotency_key="invalid",
        )
    assert raised.value.code == "INVALID_ENGINE_JOB_PAYLOAD"
