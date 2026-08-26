"""Explicit-ID reads for append-only B5 analytical authority."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lab_analytical import (
    LabAnalyticalClaimAssessment,
    LabAnalyticalMethodAuthority,
    LabAnalyticalPeakAuthority,
    LabAnalyticalRunAuthority,
    LabAnalyticalSequence,
    LabAnalyticalSequenceEntry,
    LabGCOEventAuthority,
    LabMethodValidationRecord,
)
from app.models.lab_science import (
    LabAnalyticalAttachment,
    LabGCOEvent,
)


class LabAnalyticalAuthorityRepositoryMixin:
    """Read B5 authority without ambient latest-version selection."""

    session: AsyncSession

    async def get_analytical_method_authority(
        self,
        record_id: str,
    ) -> LabAnalyticalMethodAuthority | None:
        return await self.session.get(LabAnalyticalMethodAuthority, record_id)

    async def analytical_method_authority_for_version(
        self,
        method_version_id: str,
    ) -> LabAnalyticalMethodAuthority | None:
        result = await self.session.execute(
            select(LabAnalyticalMethodAuthority).where(
                LabAnalyticalMethodAuthority.method_version_id
                == method_version_id
            )
        )
        return result.scalar_one_or_none()

    async def method_validation_records(
        self,
        method_authority_id: str,
    ) -> list[LabMethodValidationRecord]:
        result = await self.session.execute(
            select(LabMethodValidationRecord)
            .where(
                LabMethodValidationRecord.method_authority_id
                == method_authority_id
            )
            .order_by(
                LabMethodValidationRecord.intended_claim,
                LabMethodValidationRecord.scope_sha256,
                LabMethodValidationRecord.id,
            )
        )
        return list(result.scalars())

    async def get_method_validation_record(
        self,
        record_id: str,
    ) -> LabMethodValidationRecord | None:
        return await self.session.get(LabMethodValidationRecord, record_id)

    async def get_analytical_sequence(
        self,
        sequence_id: str,
    ) -> LabAnalyticalSequence | None:
        return await self.session.get(LabAnalyticalSequence, sequence_id)

    async def analytical_sequence_entries(
        self,
        sequence_id: str,
    ) -> list[LabAnalyticalSequenceEntry]:
        result = await self.session.execute(
            select(LabAnalyticalSequenceEntry)
            .where(LabAnalyticalSequenceEntry.sequence_id == sequence_id)
            .order_by(
                LabAnalyticalSequenceEntry.injection_order,
                LabAnalyticalSequenceEntry.id,
            )
        )
        return list(result.scalars())

    async def get_analytical_sequence_entry(
        self,
        entry_id: str,
    ) -> LabAnalyticalSequenceEntry | None:
        return await self.session.get(LabAnalyticalSequenceEntry, entry_id)

    async def get_analytical_attachment(
        self,
        attachment_id: str,
    ) -> LabAnalyticalAttachment | None:
        return await self.session.get(LabAnalyticalAttachment, attachment_id)

    async def get_analytical_run_authority(
        self,
        record_id: str,
    ) -> LabAnalyticalRunAuthority | None:
        return await self.session.get(LabAnalyticalRunAuthority, record_id)

    async def analytical_run_authority_for_run(
        self,
        run_id: str,
    ) -> LabAnalyticalRunAuthority | None:
        result = await self.session.execute(
            select(LabAnalyticalRunAuthority).where(
                LabAnalyticalRunAuthority.analytical_run_id == run_id
            )
        )
        return result.scalar_one_or_none()

    async def get_analytical_peak_authority(
        self,
        record_id: str,
    ) -> LabAnalyticalPeakAuthority | None:
        return await self.session.get(LabAnalyticalPeakAuthority, record_id)

    async def analytical_peak_authority_for_peak(
        self,
        peak_id: str,
    ) -> LabAnalyticalPeakAuthority | None:
        result = await self.session.execute(
            select(LabAnalyticalPeakAuthority).where(
                LabAnalyticalPeakAuthority.analytical_peak_id == peak_id
            )
        )
        return result.scalar_one_or_none()

    async def get_analytical_claim_assessment(
        self,
        record_id: str,
    ) -> LabAnalyticalClaimAssessment | None:
        return await self.session.get(LabAnalyticalClaimAssessment, record_id)

    async def get_gco_event(
        self,
        event_id: str,
    ) -> LabGCOEvent | None:
        return await self.session.get(LabGCOEvent, event_id)

    async def get_gco_event_authority(
        self,
        record_id: str,
    ) -> LabGCOEventAuthority | None:
        return await self.session.get(LabGCOEventAuthority, record_id)

    async def gco_event_authority_for_event(
        self,
        event_id: str,
    ) -> LabGCOEventAuthority | None:
        result = await self.session.execute(
            select(LabGCOEventAuthority).where(
                LabGCOEventAuthority.gco_event_id == event_id
            )
        )
        return result.scalar_one_or_none()
