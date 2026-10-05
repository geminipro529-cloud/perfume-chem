"""Persistence-only queries for immutable commercial-reference links."""

from __future__ import annotations

from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lab_commercial_references import LabCommercialReferenceSample


class LabCommercialReferenceRepositoryMixin:
    session: AsyncSession

    async def get_commercial_reference_sample(
        self, record_id: str
    ) -> LabCommercialReferenceSample | None:
        return cast(
            LabCommercialReferenceSample | None,
            await self.session.get(LabCommercialReferenceSample, record_id),
        )

    async def commercial_reference_for_sample(
        self, sample_id: str
    ) -> LabCommercialReferenceSample | None:
        return cast(
            LabCommercialReferenceSample | None,
            await self.session.scalar(
                select(LabCommercialReferenceSample)
                .where(LabCommercialReferenceSample.sample_id == sample_id)
                .limit(1)
            ),
        )

    async def commercial_reference_for_idempotency(
        self, *, requester_scope: str, idempotency_key_sha256: str
    ) -> LabCommercialReferenceSample | None:
        return cast(
            LabCommercialReferenceSample | None,
            await self.session.scalar(
                select(LabCommercialReferenceSample)
                .where(
                    LabCommercialReferenceSample.requester_scope == requester_scope,
                    LabCommercialReferenceSample.idempotency_key_sha256
                    == idempotency_key_sha256,
                )
                .limit(1)
            ),
        )


__all__ = ["LabCommercialReferenceRepositoryMixin"]
