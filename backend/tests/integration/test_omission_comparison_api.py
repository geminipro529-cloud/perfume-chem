import sqlite3
from contextlib import closing

import pytest
from sqlalchemy import func, select

from alembic import command
from app.models.lab import LabBottle, LabExperiment
from app.services.engine_job_executor import execute_registered_engine_job
from app.services.lab_service import LabService
from tests.integration.test_formula_design_job_migration import (
    _config,
    _insert_populated_job_graph,
    _job_table_sql,
    _revision,
    _triggers,
)
from tests.unit.test_omission_comparison_jobs import payload


def test_omission_migration_preserves_populated_graph_and_round_trip(tmp_path):
    database = tmp_path / "omission.db"
    config = _config(database)
    command.upgrade(config, "20260929_0024")
    _insert_populated_job_graph(database)
    command.upgrade(config, "20261007_0025")
    assert "OMISSION_COMPARISON_PLAN" in _job_table_sql(database)
    assert _revision(database) == "20261007_0025"
    assert "trg_lab_engine_jobs_update_append_only" in _triggers(database)
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        for table in ("lab_engine_jobs", "lab_engine_job_events", "lab_engine_job_results"):
            assert connection.execute(f"SELECT count(*) FROM {table}").fetchone() == (1,)
    command.downgrade(config, "20260929_0024")
    assert "OMISSION_COMPARISON_PLAN" not in _job_table_sql(database)
    command.upgrade(config, "20261007_0025")
    assert "OMISSION_COMPARISON_PLAN" in _job_table_sql(database)


async def test_omission_plan_is_durable_idempotent_and_does_not_create_physical_records(client, db_session):
    before = [await db_session.scalar(select(func.count()).select_from(model)) for model in (LabBottle, LabExperiment)]
    request = dict(schema_version="lab-engine-job-request-v2", job_type="OMISSION_COMPARISON_PLAN",
                   requester="test", idempotency_key="one-plan", payload=payload())
    submitted = await client.post("/api/v1/lab/v2/engine-jobs", json=request)
    assert submitted.status_code == 202
    replay = await client.post("/api/v1/lab/v2/engine-jobs", json=request)
    assert replay.json()["id"] == submitted.json()["id"]
    service = LabService(db_session)
    lease = await service.claim_next_engine_job(owner="omission-test", lease_seconds=60)
    assert lease is not None
    await service.mark_engine_job_running(job_id=lease.job.id, owner=lease.owner, token=lease.token)
    terminal, result, validation, diagnostics = execute_registered_engine_job(
        lease.job.job_type, dict(lease.job.normalized_payload_json), contract_version=lease.job.contract_version,
    )
    await service.complete_engine_job(job_id=lease.job.id, owner=lease.owner, token=lease.token,
                                     terminal_state=terminal, result=result, validation_state=validation, diagnostics=diagnostics)
    response = await client.get(f"/api/v1/lab/v2/engine-jobs/{lease.job.id}")
    completed = response.json()
    assert completed["state"] == "SUCCEEDED"
    assert completed["event_chain_verified"] and completed["result_hash_verified"]
    assert completed["result"]["result"]["result"]["sensory_validation"] == "NOT_TESTED"
    assert before == [await db_session.scalar(select(func.count()).select_from(model)) for model in (LabBottle, LabExperiment)]
    request["payload"]["goal"] = "Changed goal"
    conflict = await client.post("/api/v1/lab/v2/engine-jobs", json=request)
    assert conflict.status_code == 409


async def test_omission_ui_is_optional_and_has_no_automatic_execution(client):
    page = (await client.get("/app")).text
    js = (await client.get("/static/lab.js")).text
    assert 'id="omission-plan-form"' in page
    assert "Optional: compare a control" in page
    assert "cannot remove anything from your existing bottle" in page
    assert 'job_type: "OMISSION_COMPARISON_PLAN"' in js
    assert "not yet an executable blind session" in js


def test_downgrade_refuses_existing_omission_job_before_changing_graph(tmp_path):
    database = tmp_path / "populated-omission.db"
    config = _config(database)
    command.upgrade(config, "20261007_0025")
    _insert_populated_job_graph(database, job_type="OMISSION_COMPARISON_PLAN")
    original_sql, original_triggers = _job_table_sql(database), _triggers(database)
    with pytest.raises(RuntimeError, match="OMISSION_JOBS_EXIST_DOWNGRADE_WITHHELD"):
        command.downgrade(config, "20260929_0024")
    assert _revision(database) == "20261007_0025"
    assert _job_table_sql(database) == original_sql
    assert _triggers(database) == original_triggers
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        for table in ("lab_engine_jobs", "lab_engine_job_events", "lab_engine_job_results"):
            assert connection.execute(f"SELECT count(*) FROM {table}").fetchone() == (1,)


async def test_active_v5_design_reaches_ui_through_durable_job(client, db_session):
    before = (await client.get("/api/v1/lab/dashboard")).json()["counts"]
    request = dict(
        schema_version="lab-engine-job-request-v2", job_type="FORMULA_DESIGN",
        requester="test", idempotency_key="v5-durable-design",
        payload=dict(message="mineral woody", formula_name="V5 queue verification",
                     liquid_concentrate_ul_decimal="6000", max_materials=12,
                     design_mode="DEEP_COMPOSE", variant_count=3),
    )
    submitted = await client.post("/api/v1/lab/v2/engine-jobs", json=request)
    assert submitted.status_code == 202
    replay = await client.post("/api/v1/lab/v2/engine-jobs", json=request)
    assert replay.json()["id"] == submitted.json()["id"]
    service = LabService(db_session)
    lease = await service.claim_next_engine_job(owner="v5-test", lease_seconds=120)
    assert lease is not None and lease.job.id == submitted.json()["id"]
    await service.mark_engine_job_running(job_id=lease.job.id, owner=lease.owner, token=lease.token)
    terminal, result, validation, diagnostics = execute_registered_engine_job(
        lease.job.job_type, dict(lease.job.normalized_payload_json), contract_version=lease.job.contract_version,
    )
    await service.complete_engine_job(job_id=lease.job.id, owner=lease.owner, token=lease.token,
                                     terminal_state=terminal, result=result, validation_state=validation, diagnostics=diagnostics)
    completed = (await client.get(f"/api/v1/lab/v2/engine-jobs/{lease.job.id}")).json()
    assert completed["state"] == "SUCCEEDED"
    assert completed["event_chain_verified"] and completed["result_hash_verified"]
    envelope = completed["result"]["result"]
    design = envelope["result"]["formula_design"]
    variants = design["design_variants"]
    assert variants[0]["architecture"]["kind"] == "UNCHANGED_CONTROL"
    assert any(row["architecture"].get("subtype_id") == "WOOD_MINERAL" for row in variants[1:])
    assert not any(envelope["authority"][key] for key in (
        "release_authority", "safety_authority", "compounding_authority", "evidence_admission_authorized"))
    assert design["inventory_modified"] is False and design["formula_modified"] is False
    assert (await client.get("/api/v1/lab/dashboard")).json()["counts"] == before
