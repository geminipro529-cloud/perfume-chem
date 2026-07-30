"""Deterministic reads for append-only B1 source authority records."""

from __future__ import annotations

from sqlalchemy import select

from app.models.lab_sources import (
    LabEvidenceWorkflowEvent,
    LabSourceDocumentVersion,
    LabSourceExtractionRecord,
)


class LabSourceRepositoryMixin:
    """B1 source reads; transaction ownership remains in ``LabService``."""

    async def get_source_document_version(
        self,
        version_id: str,
    ) -> LabSourceDocumentVersion | None:
        return await self.session.get(LabSourceDocumentVersion, version_id)

    async def latest_source_document_version(
        self,
        source_id: str,
    ) -> LabSourceDocumentVersion | None:
        result = await self.session.execute(
            select(LabSourceDocumentVersion)
            .where(LabSourceDocumentVersion.source_id == source_id)
            .order_by(
                LabSourceDocumentVersion.version_number.desc(),
                LabSourceDocumentVersion.id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def source_record_by_hash(
        self,
        record_sha256: str,
    ) -> LabSourceDocumentVersion | None:
        result = await self.session.execute(
            select(LabSourceDocumentVersion)
            .where(LabSourceDocumentVersion.record_sha256 == record_sha256)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_source_extraction(
        self,
        extraction_id: str,
    ) -> LabSourceExtractionRecord | None:
        return await self.session.get(LabSourceExtractionRecord, extraction_id)

    async def extraction_record_by_hash(
        self,
        record_sha256: str,
    ) -> LabSourceExtractionRecord | None:
        result = await self.session.execute(
            select(LabSourceExtractionRecord)
            .where(LabSourceExtractionRecord.record_sha256 == record_sha256)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def source_extractions(
        self,
        source_version_id: str,
    ) -> list[LabSourceExtractionRecord]:
        result = await self.session.execute(
            select(LabSourceExtractionRecord)
            .where(
                LabSourceExtractionRecord.source_version_id
                == source_version_id
            )
            .order_by(
                LabSourceExtractionRecord.created_at,
                LabSourceExtractionRecord.id,
            )
        )
        return list(result.scalars())

    async def observation_extractions(
        self,
        observation_id: str,
    ) -> list[LabSourceExtractionRecord]:
        result = await self.session.execute(
            select(LabSourceExtractionRecord)
            .where(
                LabSourceExtractionRecord.output_observation_id
                == observation_id
            )
            .order_by(
                LabSourceExtractionRecord.created_at,
                LabSourceExtractionRecord.id,
            )
        )
        return list(result.scalars())

    async def workflow_events(
        self,
        subject_type: str,
        subject_id: str,
    ) -> list[LabEvidenceWorkflowEvent]:
        result = await self.session.execute(
            select(LabEvidenceWorkflowEvent)
            .where(
                LabEvidenceWorkflowEvent.subject_type == subject_type,
                LabEvidenceWorkflowEvent.subject_id == subject_id,
            )
            .order_by(
                LabEvidenceWorkflowEvent.sequence_number,
                LabEvidenceWorkflowEvent.id,
            )
        )
        return list(result.scalars())


__all__ = ["LabSourceRepositoryMixin"]
