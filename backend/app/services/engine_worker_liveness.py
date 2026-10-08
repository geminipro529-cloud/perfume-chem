"""Engine worker liveness rows: written by the worker, read by the API."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lab_engine_jobs import LabEngineWorker


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def record_engine_worker_seen(
    session: AsyncSession,
    *,
    worker_id: str,
    pid: int,
    host: str,
    started_at: datetime,
) -> None:
    """Insert or refresh this worker's row with ``last_seen_at = now``."""

    await session.merge(
        LabEngineWorker(
            id=worker_id,
            pid=pid,
            host=host,
            started_at=started_at,
            last_seen_at=_utcnow(),
        )
    )
    await session.commit()


async def remove_engine_worker(session: AsyncSession, *, worker_id: str) -> None:
    """Delete this worker's row on a clean exit."""

    await session.execute(delete(LabEngineWorker).where(LabEngineWorker.id == worker_id))
    await session.commit()


async def get_live_engine_workers(
    session: AsyncSession, max_age_seconds: float = 45
) -> list[LabEngineWorker]:
    """Return workers seen within ``max_age_seconds``, most recent first."""

    cutoff = _utcnow() - timedelta(seconds=max_age_seconds)
    rows = await session.scalars(
        select(LabEngineWorker)
        .where(LabEngineWorker.last_seen_at >= cutoff)
        .order_by(LabEngineWorker.last_seen_at.desc())
    )
    return list(rows)


__all__ = [
    "get_live_engine_workers",
    "record_engine_worker_seen",
    "remove_engine_worker",
]
