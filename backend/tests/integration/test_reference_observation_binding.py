"""Reference jobs bind exact persisted observations before queue admission."""

from __future__ import annotations

import pytest
from engine.calibration.hashing import stable_json_hash
from engine.research.commercial_references import build_commercial_reference_panel
from sqlalchemy import select

from app.models.lab import LabObservation
from app.models.lab_engine_jobs import LabEngineJob


async def _observation_id(client) -> str:
    bottle = await client.post(
        "/api/v1/lab/bottles",
        json={"label": "Blind target sample", "initial_mass_g": 0.0},
    )
    assert bottle.status_code == 201, bottle.text
    experiment = await client.post(
        "/api/v1/lab/experiments",
        json={"name": "Quick blind reference", "protocol": {"mode": "QUICK_REFERENCE"}},
    )
    assert experiment.status_code == 201, experiment.text
    sample = await client.post(
        f"/api/v1/lab/experiments/{experiment.json()['id']}/samples",
        json={"bottle_id": bottle.json()["id"], "blind_code": "482"},
    )
    assert sample.status_code == 201, sample.text
    application = await client.post(
        "/api/v1/lab/applications",
        json={
            "sample_id": sample.json()["id"],
            "applied_at": "2026-09-28T12:00:00+07:00",
            "dose": {"sprays": "1"},
            "context": {"substrate": "blotter"},
        },
    )
    assert application.status_code == 201, application.text
    observation = await client.post(
        f"/api/v1/lab/applications/{application.json()['id']}/observations",
        json={
            "elapsed_seconds": 300,
            "observations": {
                "preferred": "target",
                "reason": "clearer lavender",
                "scope": "exploratory personal",
            },
        },
    )
    assert observation.status_code == 201, observation.text
    return str(observation.json()["id"])


def _job_request(observation_ids: list[str], *, key: str) -> dict:
    panel = build_commercial_reference_panel(
        ("lavender", "amber"), as_of_date="2026-09-28"
    )
    return {
        "schema_version": "lab-engine-job-request-v2",
        "job_type": "REFERENCE_PANEL_EVALUATION",
        "requester": "personal-reference-binding-test",
        "idempotency_key": key,
        "payload": {
            "target_snapshot_id": "target-bottle-state-1",
            "target_snapshot_sha256": "1" * 64,
            "request_interpretation_sha256": "2" * 64,
            "reference_panel_id": panel["panel"]["panel_id"],
            "reference_panel_sha256": panel["panel_sha256"],
            "comparison_evidence": "QUICK_BLIND",
            "observation_record_ids": observation_ids,
            "seed": 17,
            "as_of_date": "2026-09-28",
        },
    }


@pytest.mark.asyncio
async def test_reference_job_binds_exact_observation_hash_before_persistence(
    client,
    db_session,
) -> None:
    observation_id = await _observation_id(client)
    submitted = await client.post(
        "/api/v1/lab/v2/engine-jobs",
        json=_job_request([observation_id], key="reference-observation-1"),
    )
    assert submitted.status_code == 202, submitted.text

    job = await db_session.scalar(
        select(LabEngineJob).where(LabEngineJob.id == submitted.json()["id"])
    )
    assert job is not None
    observation = await db_session.get(LabObservation, observation_id)
    assert observation is not None
    expected_hash = stable_json_hash(
        {
            "id": observation.id,
            "application_id": observation.application_id,
            "elapsed_seconds": observation.elapsed_seconds,
            "observations": dict(observation.observations_json),
            "created_at": observation.created_at.isoformat(),
        }
    )
    context = job.source_request_json["server_bound_context"]
    assert context["schema_version"] == "reference-observation-bindings-v1"
    assert context["observation_records"] == [
        {
            "record_id": observation_id,
            "record_sha256": expected_hash,
        }
    ]


@pytest.mark.asyncio
async def test_reference_job_rejects_unknown_observation_before_persistence(
    client,
    db_session,
) -> None:
    rejected = await client.post(
        "/api/v1/lab/v2/engine-jobs",
        json=_job_request(["00000000-0000-0000-0000-000000000000"], key="missing-observation"),
    )
    assert rejected.status_code == 400, rejected.text
    assert rejected.json()["error"]["code"] == "OBSERVATION_RECORD_NOT_FOUND"
    assert await db_session.scalar(select(LabEngineJob)) is None
