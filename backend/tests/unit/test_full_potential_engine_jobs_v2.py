from __future__ import annotations

from copy import deepcopy

import pytest
from engine.research.commercial_references import build_commercial_reference_panel

from app.services.engine_job_executor import execute_registered_engine_job
from app.services.engine_job_registry import ENGINE_JOB_CONTRACT_VERSION_V2
from app.services.engine_jobs import (
    EngineJobError,
    _file_manifest,
    build_engine_job_identity,
)


def test_engine_implementation_manifest_is_portable_across_text_line_endings(
    tmp_path,
) -> None:
    source = tmp_path / "portable_source.py"
    source.write_bytes(b"first = 1\nsecond = 2\n")
    lf_manifest = _file_manifest((source,))

    source.write_bytes(b"first = 1\r\nsecond = 2\r\n")
    crlf_manifest = _file_manifest((source,))

    assert lf_manifest == crlf_manifest
    assert lf_manifest["schema"] == "engine-implementation-manifest-v2"
    assert (
        lf_manifest["artifact_hash_semantics"]
        == "sha256-binary-exact-or-utf8-lf-normalized-v1"
    )


def _release_payload() -> dict:
    return {
        "formula_sha256": "1" * 64,
        "components": [
            {
                "material_id": "example",
                "initial_mass_g_decimal": "0.01",
                "identity_state": "EXACT",
                "molecular_weight_g_mol": 100.0,
                "vapor_pressure_pa": 1.0,
                "activity_coefficient": 1.2,
                "substrate_retained_fraction_decimal": "0",
                "precipitated_fraction_decimal": "0",
                "reacted_fraction_decimal": "0",
                "desorption_rate_s_decimal": "0",
                "permeation_rate_s_decimal": "0",
                "reaction_rate_s_decimal": "0",
            }
        ],
        "scenario": {
            "scenario_id": "glass-v1",
            "matrix_id": "ethanol-water-80-20",
            "substrate": "GLASS",
            "deposit_mass_g_decimal": "0.01",
            "surface_area_m2_decimal": "0.0001",
            "temperature_k": 298.15,
            "relative_humidity_decimal": "0.5",
            "airflow_m_s_decimal": "0.1",
            "delivery_volume_m3_decimal": "0.001",
            "sampling_geometry": "sealed-cell",
            "timepoints_seconds": [0.0, 10.0],
        },
        "parameters": {
            "capability_id": "finite-release-v1",
            "equilibrium_model": "NONIDEAL_PARAMETERIZED",
            "matrix_ids": ["ethanol-water-80-20"],
            "supported_substrates": ["GLASS"],
            "mass_transfer_coefficient_m_s_decimal": "0.0001",
            "air_exchange_rate_s_decimal": "0.1",
            "delivered_capture_fraction_decimal": "0.25",
            "maximum_step_seconds_decimal": "0.25",
            "calibration_state": "UNCALIBRATED",
        },
    }


def _candidate(index: int) -> dict:
    x = index / 12.0
    loss = (x - 0.4) ** 2
    return {
        "candidate_id": f"c-{index}",
        "formula_sha256": f"{index % 16:x}" * 64,
        "variables": {"lavender": x, "ambrox": 1.0 - x},
        "endpoint_value": loss,
        "prediction_interval": [loss - 0.2, loss + 0.2],
        "coverage_decimal": "1",
        "applicability_state": "APPLICABLE",
        "feature_lineage": ["delivered gas intensity trajectory"],
        "model_signs": {"strongest": -1, "partial": -1},
    }


def _optimizer_payload() -> dict:
    return {
        "search_id": "search-v2",
        "endpoint_id": "measured-intensity-loss",
        "baseline_id": "c-0",
        "candidates": [_candidate(index) for index in range(13)],
        "budget_per_arm": 4,
        "seeds": [17, 29],
        "minimize": True,
    }


def _goal_analysis_payload() -> dict:
    return {
        "formula_id": "lavender-amber-r6",
        "formula_name": "Lavande Ambre Profond R6",
        "workflow_mode": "PERSONAL_RESEARCH",
        "rows": [
            {
                "row_id": "lavender-bontoux",
                "material": "Lavender EO Bontoux",
                "amount_decimal": "700",
                "amount_unit": "uL",
                "concentration_fraction_decimal": "1",
                "concentration_basis": "NEAT",
                "operation": "DIRECT_ADD",
            },
            {
                "row_id": "lavender-aroma-more",
                "material": "Lavender EO Aroma More",
                "amount_decimal": "300",
                "amount_unit": "uL",
                "concentration_fraction_decimal": "1",
                "concentration_basis": "NEAT",
                "operation": "DIRECT_ADD",
            },
            {
                "row_id": "ambrox-crystal",
                "material": "Ambrox Super Crystals",
                "amount_decimal": "300",
                "amount_unit": "mg",
                "concentration_fraction_decimal": "1",
                "concentration_basis": "NEAT",
                "operation": "MASS_ADD",
            },
        ],
        "goals": ["Make the lavender clearer while preserving the dry amber"],
        "must_preserve": ["dry amber"],
        "must_avoid": ["sweeter"],
        "mode": "between_mix",
        "max_hypotheses": 3,
    }


def _formula_design_payload() -> dict:
    return {
        "message": (
            "A cold metallic pear perfume with violet powder, transparent air, "
            "and dry cedar; no vanilla."
        ),
        "formula_name": "Chrome Orchard",
        "liquid_concentrate_ul_decimal": "6000",
        "max_materials": 30,
        "must_preserve": ["cold mineral identity"],
        "must_avoid": ["vanilla"],
        "previous_stock_ids": [],
        "conversation_context": [],
        "execution_strategy": "NEW_FORMULA",
        "appeal_mode": "IDENTITY_FIRST",
        "comparison_evidence": "DOCUMENT_ONLY",
        "active_bottle_id": None,
        "design_mode": "DEEP_COMPOSE",
        "variant_count": 3,
    }


def test_v2_formula_design_is_durable_closed_and_advisory() -> None:
    identity = build_engine_job_identity(
        job_type="FORMULA_DESIGN",
        payload=_formula_design_payload(),
        requester="formula-studio-test",
        idempotency_key="formula-design-1",
        request_schema_version="lab-engine-job-request-v2",
    )

    terminal, result, validation, diagnostics = execute_registered_engine_job(
        "FORMULA_DESIGN",
        identity["normalized_payload"],
        contract_version=identity["contract_version"],
    )

    assert terminal == "SUCCEEDED"
    assert validation in {"ADVISORY_COMPLETE", "ADVISORY_FINDINGS"}
    design = result["result"]["formula_design"]
    assert design["composition_plan"]["method"] == (
        "SEMANTIC_TARGET_PLUS_GLOBAL_CONSTRAINT_SOLVER_V1"
    )
    assert len(design["design_variants"]) == 3
    assert result["selection"]["ranked_candidates"] == []
    assert result["selection"]["formula_action"] == "PROPOSAL_ONLY"
    assert result["release_authority"] is False
    assert result["safety_authority"] is False
    assert result["compounding_authority"] is False
    assert diagnostics == {"executor": "closed-registry-v2"}


def test_formula_design_requires_v2_and_rejects_caller_execution_fields() -> None:
    with pytest.raises(EngineJobError) as legacy_error:
        build_engine_job_identity(
            job_type="FORMULA_DESIGN",
            payload=_formula_design_payload(),
            requester="formula-studio-test",
            idempotency_key="formula-design-legacy",
        )
    assert legacy_error.value.code == "INVALID_ENGINE_JOB_PAYLOAD"

    invalid = deepcopy(_formula_design_payload())
    invalid["python_module"] = "arbitrary.module"
    with pytest.raises(EngineJobError) as invalid_error:
        build_engine_job_identity(
            job_type="FORMULA_DESIGN",
            payload=invalid,
            requester="formula-studio-test",
            idempotency_key="formula-design-invalid",
            request_schema_version="lab-engine-job-request-v2",
        )
    assert invalid_error.value.code == "INVALID_ENGINE_JOB_PAYLOAD"


def test_v2_release_simulation_is_closed_fingerprinted_and_executable() -> None:
    identity = build_engine_job_identity(
        job_type="RELEASE_SIMULATION",
        payload=_release_payload(),
        requester="test-v2",
        idempotency_key="release-1",
        request_schema_version="lab-engine-job-request-v2",
    )
    assert identity["contract_version"] == ENGINE_JOB_CONTRACT_VERSION_V2
    assert identity["source_request"]["schema_version"] == "lab-engine-job-request-v2"

    terminal, result, validation, diagnostics = execute_registered_engine_job(
        "RELEASE_SIMULATION",
        identity["normalized_payload"],
        contract_version=identity["contract_version"],
    )
    assert terminal == "SUCCEEDED"
    assert validation == "ADVISORY_FINDINGS"
    assert result["schema_version"] == "lab-engine-result-envelope-v2"
    assert result["result"]["release_trajectory"]["frames"]
    assert result["release_authority"] is False
    assert diagnostics == {"executor": "closed-registry-v2"}


def test_v2_formula_analysis_executes_goal_directed_science_with_mixed_units() -> None:
    identity = build_engine_job_identity(
        job_type="FORMULA_ANALYSIS",
        payload=_goal_analysis_payload(),
        requester="personal-research-test",
        idempotency_key="goal-analysis-1",
        request_schema_version="lab-engine-job-request-v2",
    )

    terminal, result, validation, diagnostics = execute_registered_engine_job(
        "FORMULA_ANALYSIS",
        identity["normalized_payload"],
        contract_version=identity["contract_version"],
    )

    assert terminal == "SUCCEEDED"
    assert validation == "ADVISORY_FINDINGS"
    assert result["schema_version"] == "lab-engine-result-envelope-v2"
    assert result["validation"]["findings"] == [
        {
            "code": "QUANTITATIVE_FORMULA_VALIDATION_WITHHELD",
            "state": "HOLD_CONSTANT_TOTAL_BASIS_UNRESOLVED",
        },
        {"code": "MEASURED_OUTCOME_NOT_SUPPLIED"},
    ]
    analysis = result["result"]["goal_analysis"]
    direct = next(
        hypothesis
        for hypothesis in analysis["modification_hypotheses"]
        if hypothesis["evidence_class"] == "EXPLICIT_GOAL_PLUS_FORMULA_FACT"
    )
    assert direct["target_row_ids"] == ["lavender-bontoux", "lavender-aroma-more"]
    assert direct["trial"]["internal_ratio_policy"] == "PRESERVE_CURRENT_BLOCK_RATIO"
    assert result["selection"]["status"] == "UNORDERED_CONTROLLED_HYPOTHESES"
    assert result["authority"]["compounding_authority"] is False
    assert result["authority"]["release_authority"] is False
    assert diagnostics == {"executor": "closed-registry-v2"}


def test_v2_formula_goal_and_forbidden_authority_fields_are_fingerprint_bound() -> None:
    first = build_engine_job_identity(
        job_type="FORMULA_ANALYSIS",
        payload=_goal_analysis_payload(),
        requester="personal-research-test",
        idempotency_key="goal-analysis-a",
        request_schema_version="lab-engine-job-request-v2",
    )
    changed_payload = deepcopy(_goal_analysis_payload())
    changed_payload["goals"] = ["Use less Ambrox while preserving lavender"]
    changed = build_engine_job_identity(
        job_type="FORMULA_ANALYSIS",
        payload=changed_payload,
        requester="personal-research-test",
        idempotency_key="goal-analysis-b",
        request_schema_version="lab-engine-job-request-v2",
    )
    assert first["job_fingerprint_sha256"] != changed["job_fingerprint_sha256"]

    invalid = deepcopy(_goal_analysis_payload())
    invalid["release_authority"] = True
    with pytest.raises(EngineJobError) as error:
        build_engine_job_identity(
            job_type="FORMULA_ANALYSIS",
            payload=invalid,
            requester="personal-research-test",
            idempotency_key="goal-analysis-invalid",
            request_schema_version="lab-engine-job-request-v2",
        )
    assert error.value.code == "INVALID_ENGINE_JOB_PAYLOAD"


def test_new_job_types_require_v2_and_seed_drift_changes_fingerprint() -> None:
    with pytest.raises(EngineJobError) as error:
        build_engine_job_identity(
            job_type="RELEASE_SIMULATION",
            payload=_release_payload(),
            requester="test",
            idempotency_key="legacy",
        )
    assert error.value.code == "INVALID_ENGINE_JOB_PAYLOAD"

    first = build_engine_job_identity(
        job_type="OPTIMIZER_SEARCH",
        payload=_optimizer_payload(),
        requester="test",
        idempotency_key="optimizer-1",
        request_schema_version="lab-engine-job-request-v2",
    )
    changed_payload = deepcopy(_optimizer_payload())
    changed_payload["seeds"] = [17, 43]
    changed = build_engine_job_identity(
        job_type="OPTIMIZER_SEARCH",
        payload=changed_payload,
        requester="test",
        idempotency_key="optimizer-2",
        request_schema_version="lab-engine-job-request-v2",
    )
    assert first["job_fingerprint_sha256"] != changed["job_fingerprint_sha256"]


def test_v2_optimizer_executes_three_equal_budget_arms_not_placeholder() -> None:
    identity = build_engine_job_identity(
        job_type="OPTIMIZER_SEARCH",
        payload=_optimizer_payload(),
        requester="test",
        idempotency_key="optimizer-run",
        request_schema_version="lab-engine-job-request-v2",
    )
    terminal, result, validation, _diagnostics = execute_registered_engine_job(
        "OPTIMIZER_SEARCH",
        identity["normalized_payload"],
        contract_version=identity["contract_version"],
    )
    benchmark = result["result"]["benchmark"]
    assert terminal in {"SUCCEEDED", "WITHHELD"}
    assert validation in {"ADVISORY_COMPLETE", "WITHHOLD_UNKNOWN"}
    assert benchmark["benchmark_equal_budget"] is True
    assert benchmark["algorithm_versions"]["conservative_gp"].startswith("rbf-gp")
    assert len(benchmark["runs"]) == 2
    assert result["selection"]["status"] != "NOT_REQUESTED"


def test_v2_preference_analysis_preserves_ties() -> None:
    comparisons = []
    for session in (1, 2, 3):
        for index, (left, right, preferred) in enumerate(
            (("A", "B", "A"), ("A", "C", None), ("B", "C", "C"), ("A", "B", None)),
            start=1,
        ):
            comparisons.append(
                {
                    "left_item": left,
                    "right_item": right,
                    "preferred_item": preferred,
                    "comparison_id": f"session-{session}:{index}",
                    "assessor_id": "one-user",
                    "protocol_id": "blind-paired-liking-v1",
                    "criterion_id": "personal-liking",
                    "time_seconds": 1800.0,
                    "first_presented_item": left,
                }
            )
    payload = {
        "analysis_id": "personal-v1",
        "criterion_id": "personal-liking",
        "comparisons": comparisons,
        "minimum_comparisons": 10,
        "minimum_sessions": 3,
        "regularization": 0.1,
        "bootstrap_replicates": 0,
        "bootstrap_seed": 17,
    }
    identity = build_engine_job_identity(
        job_type="PREFERENCE_ANALYSIS",
        payload=payload,
        requester="test",
        idempotency_key="preference-run",
        request_schema_version="lab-engine-job-request-v2",
    )
    terminal, result, validation, _diagnostics = execute_registered_engine_job(
        "PREFERENCE_ANALYSIS",
        identity["normalized_payload"],
        contract_version=identity["contract_version"],
    )
    fitted = result["result"]["personal_preference"]
    assert terminal == "SUCCEEDED"
    assert validation == "ADVISORY_FINDINGS"
    assert fitted["tie_rate"] == pytest.approx(0.5)
    assert fitted["population_claim_authorized"] is False


def test_v2_batch_gate_binds_exact_corpus_hash_and_executes_each_formula() -> None:
    formula = {
        "formula_id": "f-1",
        "formula_name": "Bound formula",
        "rows": [
            {
                "row_id": "r-1",
                "material": "Linalool",
                "amount_decimal": "100",
                "amount_unit": "uL",
                "concentration_fraction_decimal": "1",
                "concentration_basis": "NEAT",
                "operation": "DIRECT_ADD",
            }
        ],
        "final_volume_ml_decimal": "30",
        "expected_concentrate_ul_decimal": "100",
        "brief": "generic",
    }
    payload = {
        "corpus_id": "one-formula",
        "formulas": [formula],
        "worker_count": 1,
    }
    identity = build_engine_job_identity(
        job_type="BATCH_GATE",
        payload=payload,
        requester="test",
        idempotency_key="batch-run",
        request_schema_version="lab-engine-job-request-v2",
    )
    terminal, result, _validation, _diagnostics = execute_registered_engine_job(
        "BATCH_GATE",
        identity["normalized_payload"],
        contract_version=identity["contract_version"],
    )
    assert terminal == "SUCCEEDED"
    rows = result["result"]["formula_results"]
    assert len(rows) == 1
    assert rows[0]["formula_id"] == "f-1"
    assert rows[0]["result_sha256"]


def test_v2_batch_gate_rejects_caller_corpus_hash_mismatch_before_execution() -> None:
    formula = {
        "formula_id": "f-1",
        "formula_name": "Bound formula",
        "rows": [{
            "row_id": "r-1", "material": "Linalool", "amount_decimal": "100",
            "amount_unit": "uL", "concentration_fraction_decimal": "1",
            "concentration_basis": "NEAT", "operation": "DIRECT_ADD"
        }],
        "expected_concentrate_ul_decimal": "100",
        "brief": "generic",
    }
    with pytest.raises(EngineJobError) as error:
        build_engine_job_identity(
            job_type="BATCH_GATE",
            payload={
                "corpus_id": "bad",
                "frozen_corpus_sha256": "0" * 64,
                "formulas": [formula],
                "worker_count": 1,
            },
            requester="test",
            idempotency_key="bad-batch",
            request_schema_version="lab-engine-job-request-v2",
        )
    assert error.value.code == "INVALID_ENGINE_JOB_PAYLOAD"
    assert "FROZEN_CORPUS_HASH_MISMATCH" in str(error.value)


def test_reference_panel_job_is_fingerprinted_and_documentary_only() -> None:
    panel = build_commercial_reference_panel(
        ("lavender", "amber"), as_of_date="2026-09-28"
    )
    payload = {
        "target_snapshot_id": "r6",
        "target_snapshot_sha256": "1" * 64,
        "request_interpretation_sha256": "2" * 64,
        "reference_panel_id": panel["panel"]["panel_id"],
        "reference_panel_sha256": panel["panel_sha256"],
        "comparison_evidence": "DOCUMENT_ONLY",
        "observation_record_ids": [],
        "seed": 17,
        "as_of_date": "2026-09-28",
    }
    identity = build_engine_job_identity(
        job_type="REFERENCE_PANEL_EVALUATION",
        payload=payload,
        requester="personal-reference-test",
        idempotency_key="reference-panel-1",
        request_schema_version="lab-engine-job-request-v2",
    )
    terminal, result, validation, diagnostics = execute_registered_engine_job(
        "REFERENCE_PANEL_EVALUATION",
        identity["normalized_payload"],
        contract_version=identity["contract_version"],
    )
    assert terminal == "SUCCEEDED"
    assert validation == "ADVISORY_COMPLETE"
    assert result["selection"]["status"] == "DOCUMENTARY_ARCHITECTURE_CLUES_ONLY"
    assert result["result"]["personal_liking"]["state"] == "NOT_ESTABLISHED"
    assert result["authority"]["compounding_authority"] is False
    assert diagnostics == {"executor": "closed-registry-v2"}

    changed_payload = deepcopy(payload)
    changed_payload["seed"] = 29
    changed = build_engine_job_identity(
        job_type="REFERENCE_PANEL_EVALUATION",
        payload=changed_payload,
        requester="personal-reference-test",
        idempotency_key="reference-panel-2",
        request_schema_version="lab-engine-job-request-v2",
    )
    assert identity["job_fingerprint_sha256"] != changed["job_fingerprint_sha256"]

    first_bound = build_engine_job_identity(
        job_type="REFERENCE_PANEL_EVALUATION",
        payload=payload,
        requester="personal-reference-test",
        idempotency_key="reference-panel-bound-1",
        request_schema_version="lab-engine-job-request-v2",
        server_bound_context={
            "schema_version": "reference-observation-bindings-v1",
            "observation_records": [
                {"record_id": "obs-1", "record_sha256": "3" * 64}
            ],
        },
    )
    second_bound = build_engine_job_identity(
        job_type="REFERENCE_PANEL_EVALUATION",
        payload=payload,
        requester="personal-reference-test",
        idempotency_key="reference-panel-bound-2",
        request_schema_version="lab-engine-job-request-v2",
        server_bound_context={
            "schema_version": "reference-observation-bindings-v1",
            "observation_records": [
                {"record_id": "obs-1", "record_sha256": "4" * 64}
            ],
        },
    )
    assert first_bound["job_fingerprint_sha256"] != (
        second_bound["job_fingerprint_sha256"]
    )
    assert first_bound["source_request"]["server_bound_context"][
        "observation_records"
    ][0]["record_sha256"] == "3" * 64
