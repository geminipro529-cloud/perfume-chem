import pytest
from sqlalchemy import func, select

from app.models.lab import LabBottle, LabExperiment
from app.services.engine_job_executor import execute_registered_engine_job
from app.services.lab_service import LabService
from tests.unit.test_one_change_comparison_jobs import addition, dose, payload


async def _run(client, db_session, change, key):
    request = dict(schema_version="lab-engine-job-request-v2", job_type="OMISSION_COMPARISON_PLAN",
                   requester="test", idempotency_key=key, payload=payload(change))
    submitted = await client.post("/api/v1/lab/v2/engine-jobs", json=request)
    assert submitted.status_code == 202, submitted.text
    service = LabService(db_session)
    lease = await service.claim_next_engine_job(owner="one-change-test", lease_seconds=60)
    assert lease is not None and lease.job.id == submitted.json()["id"]
    await service.mark_engine_job_running(job_id=lease.job.id, owner=lease.owner, token=lease.token)
    terminal, result, validation, diagnostics = execute_registered_engine_job(
        lease.job.job_type, dict(lease.job.normalized_payload_json), contract_version=lease.job.contract_version,
    )
    await service.complete_engine_job(job_id=lease.job.id, owner=lease.owner, token=lease.token,
                                     terminal_state=terminal, result=result, validation_state=validation,
                                     diagnostics=diagnostics)
    completed = (await client.get(f"/api/v1/lab/v2/engine-jobs/{lease.job.id}")).json()
    assert completed["state"] == "SUCCEEDED"
    assert completed["event_chain_verified"] and completed["result_hash_verified"]
    return completed["result"]["result"]["result"]


@pytest.mark.parametrize("change,method,split", [
    (addition(), "SPLIT_VIAL", (20, 180)),
    (addition(amount="50"), "BLOTTER_PREVIEW", None),
    (dose("UP"), "SPLIT_VIAL", (20, 180)),
    (dose("DOWN"), "FRESH_VIALS", None),
])
async def test_one_change_plan_through_durable_job_creates_no_physical_records(client, db_session, change, method, split):
    before = [await db_session.scalar(select(func.count()).select_from(m)) for m in (LabBottle, LabExperiment)]
    result = await _run(client, db_session, change, f"one-change-{change['kind']}-{method}")
    assert result["schema_version"] == "one-change-comparison-handoff-v1"
    assert result["how_to_try"]["method"] == method
    if split:
        vial = result["how_to_try"]["split_vial"]
        assert (vial["split_ul"], vial["main_bottle_ul"]) == split
    assert result["triangle_test"]["min_correct"] == 5
    assert result["bottle_modified"] is False and result["physical_execution_authorized"] is False
    after = [await db_session.scalar(select(func.count()).select_from(m)) for m in (LabBottle, LabExperiment)]
    assert before == after


@pytest.mark.parametrize("change,message", [
    ([addition(), dose("UP")], "Choose exactly one change per plan"),
    (dose("DOWN", step="500"), "use an omission plan"),
])
async def test_zero_or_several_changes_are_a_readable_400(client, change, message):
    request = dict(schema_version="lab-engine-job-request-v2", job_type="OMISSION_COMPARISON_PLAN",
                   requester="test", idempotency_key="bad-change", payload=payload(change))
    response = await client.post("/api/v1/lab/v2/engine-jobs", json=request)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_ENGINE_JOB_PAYLOAD"
    assert message in response.json()["error"]["message"]
