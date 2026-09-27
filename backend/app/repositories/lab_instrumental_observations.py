"""Persistence-only queries for instrumental observation intake."""

from __future__ import annotations

from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lab_instrumental_observations import LabInstrumentalObservation


class LabInstrumentalObservationRepositoryMixin:
    session: AsyncSession

    async def get_instrumental_observation(
        self, record_id: str
    ) -> LabInstrumentalObservation | None:
        return cast(
            LabInstrumentalObservation | None,
            await self.session.get(LabInstrumentalObservation, record_id),
        )

    async def instrumental_observation_for_idempotency(
        self, *, requester_scope: str, idempotency_key_sha256: str
    ) -> LabInstrumentalObservation | None:
        return cast(
            LabInstrumentalObservation | None,
            await self.session.scalar(
                select(LabInstrumentalObservation)
                .where(
                    LabInstrumentalObservation.requester_scope == requester_scope,
                    LabInstrumentalObservation.idempotency_key_sha256
                    == idempotency_key_sha256,
                )
                .limit(1)
            ),
        )

    async def instrumental_observation_for_identity(
        self, observation_id: str
    ) -> LabInstrumentalObservation | None:
        return cast(
            LabInstrumentalObservation | None,
            await self.session.scalar(
                select(LabInstrumentalObservation)
                .where(LabInstrumentalObservation.observation_id == observation_id)
                .limit(1)
            ),
        )


__all__ = ["LabInstrumentalObservationRepositoryMixin"]
