from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.lab_engine_jobs import LabEngineWorker

STATUS_URL = "/api/v1/lab/v2/engine-workers/status"


def _worker(worker_id: str, *, seen_seconds_ago: float) -> LabEngineWorker:
    now = datetime.now(timezone.utc)
    return LabEngineWorker(
        id=worker_id,
        pid=4242,
        host="lab-host",
        started_at=now - timedelta(minutes=10),
        last_seen_at=now - timedelta(seconds=seen_seconds_ago),
    )


async def test_engine_worker_status_reports_no_workers(client) -> None:
    response = await client.get(STATUS_URL)
    assert response.status_code == 200
    body = response.json()
    assert body["live"] == 0
    assert body["workers"] == []
    assert body["max_age_seconds"] == 45
    assert datetime.fromisoformat(body["checked_at"]).tzinfo is not None


async def test_engine_worker_status_reports_one_fresh_worker(client, db_session) -> None:
    db_session.add(_worker("lab-host:4242:abcdef01", seen_seconds_ago=5))
    await db_session.commit()

    response = await client.get(STATUS_URL)
    assert response.status_code == 200
    body = response.json()
    assert body["live"] == 1
    assert len(body["workers"]) == 1
    worker = body["workers"][0]
    assert set(worker) == {"id", "host", "pid", "started_at", "last_seen_at"}
    assert worker["id"] == "lab-host:4242:abcdef01"
    assert worker["host"] == "lab-host"
    assert worker["pid"] == 4242


async def test_engine_worker_status_ignores_a_stale_worker(client, db_session) -> None:
    db_session.add(_worker("lab-host:4242:deadbeef", seen_seconds_ago=120))
    await db_session.commit()

    response = await client.get(STATUS_URL)
    assert response.status_code == 200
    body = response.json()
    assert body["live"] == 0
    assert body["workers"] == []
