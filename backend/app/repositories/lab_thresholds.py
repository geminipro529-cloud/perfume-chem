"""Explicit-ID persistence reads for B3 threshold and OAV authority."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models.lab_thresholds import (
    LabLegacyThresholdRecord,
    LabOAVAssessment,
    LabThresholdObservationContext,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class LabThresholdRepositoryMixin:
    if TYPE_CHECKING:
        session: AsyncSession

    async def get_threshold_context(
        self,
        context_id: str,
    ) -> LabThresholdObservationContext | None:
        return await self.session.get(
            LabThresholdObservationContext,
            context_id,
        )

    async def threshold_context_for_observation(
        self,
        observation_id: str,
    ) -> LabThresholdObservationContext | None:
        result = await self.session.execute(
            select(LabThresholdObservationContext).where(
                LabThresholdObservationContext.observation_id == observation_id
            )
        )
        return result.scalar_one_or_none()

    async def threshold_context_by_hash(
        self,
        content_sha256: str,
    ) -> LabThresholdObservationContext | None:
        result = await self.session.execute(
            select(LabThresholdObservationContext).where(
                LabThresholdObservationContext.content_sha256 == content_sha256
            )
        )
        return result.scalar_one_or_none()

    async def get_oav_assessment(
        self,
        assessment_id: str,
    ) -> LabOAVAssessment | None:
        return await self.session.get(LabOAVAssessment, assessment_id)

    async def oav_assessment_by_hash(
        self,
        content_sha256: str,
    ) -> LabOAVAssessment | None:
        result = await self.session.execute(
            select(LabOAVAssessment).where(LabOAVAssessment.content_sha256 == content_sha256)
        )
        return result.scalar_one_or_none()

    async def get_legacy_threshold_record(
        self,
        record_id: str,
    ) -> LabLegacyThresholdRecord | None:
        return await self.session.get(LabLegacyThresholdRecord, record_id)

    async def legacy_threshold_by_hash(
        self,
        content_sha256: str,
    ) -> LabLegacyThresholdRecord | None:
        result = await self.session.execute(
            select(LabLegacyThresholdRecord).where(
                LabLegacyThresholdRecord.content_sha256 == content_sha256
            )
        )
        return result.scalar_one_or_none()


__all__ = ["LabThresholdRepositoryMixin"]
