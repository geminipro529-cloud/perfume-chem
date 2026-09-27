from __future__ import annotations

from app.services.engine_job_executor import execute_registered_engine_job
from app.services.lab_service import LabService


def _request() -> dict:
    return {
        "schema_version": "lab-engine-job-request-v2",
        "job_type": "RELEASE_SIMULATION",
        "idempotency_key": "release-api-v2",
        "requester": "v2-api-fixture",
        "payload": {
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
        },
    }


def _goal_request() -> dict:
    return {
        "schema_version": "lab-engine-job-request-v2",
        "job_type": "FORMULA_ANALYSIS",
        "idempotency_key": "goal-analysis-api-v2",
        "requester": "personal-research-api-fixture",
        "payload": {
            "formula_id": "lavender-amber-api",
            "formula_name": "Lavender Amber API Study",
            "workflow_mode": "PERSONAL_RESEARCH",
            "rows": [
                {
                    "row_id": "lavender-1",
                    "material": "Lavender EO Bontoux",
                    "amount_decimal": "700",
                    "amount_unit": "uL",
                    "concentration_fraction_decimal": "1",
                    "concentration_basis": "NEAT",
                    "operation": "DIRECT_ADD",
                },
                {
                    "row_id": "lavender-2",
                    "material": "Lavender EO Aroma More",
                    "amount_decimal": "300",
                    "amount_unit": "uL",
                    "concentration_fraction_decimal": "1",
                    "concentration_basis": "NEAT",
                    "operation": "DIRECT_ADD",
                },
                {
                    "row_id": "ambrox",
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
            "mode": "between_mix",
        },
    }


async def test_v2_job_enters_durable_queue_and_worker_result_chain(client, db_session) -> None:
    response = await client.post("/api/v1/lab/v2/engine-jobs", json=_request())
    assert response.status_code == 202
    queued = response.json()
    assert queued["schema_version"] == "lab-engine-job-response-v2"
    assert queued["state"] == "QUEUED"
    assert queued["contract_version"] == "perfume-chem-engine-job-contract-v2"

    service = LabService(db_session)
    lease = await service.claim_next_engine_job(owner="test-worker", lease_seconds=60)
    assert lease is not None
    await service.mark_engine_job_running(
        job_id=lease.job.id,
        owner=lease.owner,
        token=lease.token,
    )
    terminal, result, validation, diagnostics = execute_registered_engine_job(
        lease.job.job_type,
        dict(lease.job.normalized_payload_json),
        contract_version=lease.job.contract_version,
    )
    await service.complete_engine_job(
        job_id=lease.job.id,
        owner=lease.owner,
        token=lease.token,
        terminal_state=terminal,
        result=result,
        validation_state=validation,
        diagnostics=diagnostics,
    )

    completed = await client.get(f"/api/v1/lab/v2/engine-jobs/{lease.job.id}")
    assert completed.status_code == 200
    body = completed.json()
    assert body["schema_version"] == "lab-engine-job-response-v2"
    assert body["state"] == "SUCCEEDED"
    assert body["event_chain_verified"] is True
    assert body["result_hash_verified"] is True
    assert body["result"]["result"]["schema_version"] == "lab-engine-result-envelope-v2"
    assert body["result"]["result"]["authority"]["compounding_authority"] is False


async def test_v2_api_rejects_new_type_under_v1_schema(client) -> None:
    request = _request()
    request["schema_version"] = "lab-engine-job-request-v1"
    request["idempotency_key"] = "wrong-schema"
    response = await client.post("/api/v1/lab/v2/engine-jobs", json=request)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_ENGINE_JOB_PAYLOAD"


async def test_v2_goal_analysis_runs_through_durable_api_and_worker(client, db_session) -> None:
    response = await client.post("/api/v1/lab/v2/engine-jobs", json=_goal_request())
    assert response.status_code == 202
    queued = response.json()
    assert queued["state"] == "QUEUED"

    service = LabService(db_session)
    lease = await service.claim_next_engine_job(owner="goal-test-worker", lease_seconds=60)
    assert lease is not None
    await service.mark_engine_job_running(
        job_id=lease.job.id,
        owner=lease.owner,
        token=lease.token,
    )
    terminal, result, validation, diagnostics = execute_registered_engine_job(
        lease.job.job_type,
        dict(lease.job.normalized_payload_json),
        contract_version=lease.job.contract_version,
    )
    await service.complete_engine_job(
        job_id=lease.job.id,
        owner=lease.owner,
        token=lease.token,
        terminal_state=terminal,
        result=result,
        validation_state=validation,
        diagnostics=diagnostics,
    )

    completed = await client.get(f"/api/v1/lab/v2/engine-jobs/{lease.job.id}")
    assert completed.status_code == 200
    body = completed.json()
    assert body["state"] == "SUCCEEDED"
    envelope = body["result"]["result"]
    assert envelope["result"]["goal_analysis"]["status"] == "GOAL_DIRECTED_HYPOTHESES_READY"
    assert envelope["selection"]["status"] == "UNORDERED_CONTROLLED_HYPOTHESES"
    assert envelope["authority"]["compounding_authority"] is False
