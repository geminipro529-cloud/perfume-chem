"""Deterministic reads for append-only B1 source authority records."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models.lab_sources import (
    LabEvidenceWorkflowEvent,
    LabSourceDerivationLink,
    LabSourceDocumentVersion,
    LabSourceExtractionRecord,
    LabSourceUseConstraintVersion,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class LabSourceRepositoryMixin:
    """B1 source reads; transaction ownership remains in ``LabService``."""

    if TYPE_CHECKING:
        session: AsyncSession

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

    async def get_source_use_constraint_version(
        self,
        version_id: str,
    ) -> LabSourceUseConstraintVersion | None:
        return await self.session.get(LabSourceUseConstraintVersion, version_id)

    async def latest_source_use_constraint_version(
        self,
        constraint_id: str,
    ) -> LabSourceUseConstraintVersion | None:
        result = await self.session.execute(
            select(LabSourceUseConstraintVersion)
            .where(LabSourceUseConstraintVersion.constraint_id == constraint_id)
            .order_by(
                LabSourceUseConstraintVersion.version_number.desc(),
                LabSourceUseConstraintVersion.id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def source_use_constraint_record_by_hash(
        self,
        record_sha256: str,
    ) -> LabSourceUseConstraintVersion | None:
        result = await self.session.execute(
            select(LabSourceUseConstraintVersion)
            .where(LabSourceUseConstraintVersion.record_sha256 == record_sha256)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def source_use_constraints(
        self,
        subject_source_version_id: str,
    ) -> list[LabSourceUseConstraintVersion]:
        result = await self.session.execute(
            select(LabSourceUseConstraintVersion)
            .where(
                LabSourceUseConstraintVersion.subject_source_version_id
                == subject_source_version_id
            )
            .order_by(
                LabSourceUseConstraintVersion.constraint_id,
                LabSourceUseConstraintVersion.version_number.desc(),
                LabSourceUseConstraintVersion.id,
            )
        )
        return list(result.scalars())

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

    async def get_source_derivation(
        self,
        child_source_version_id: str,
        parent_source_version_id: str,
        relation: str,
    ) -> LabSourceDerivationLink | None:
        result = await self.session.execute(
            select(LabSourceDerivationLink)
            .where(
                LabSourceDerivationLink.child_source_version_id
                == child_source_version_id,
                LabSourceDerivationLink.parent_source_version_id
                == parent_source_version_id,
                LabSourceDerivationLink.relation == relation,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def derivation_record_by_hash(
        self,
        record_sha256: str,
    ) -> LabSourceDerivationLink | None:
        result = await self.session.execute(
            select(LabSourceDerivationLink)
            .where(LabSourceDerivationLink.record_sha256 == record_sha256)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def parent_derivation_links(
        self,
        child_source_version_id: str,
    ) -> list[LabSourceDerivationLink]:
        result = await self.session.execute(
            select(LabSourceDerivationLink)
            .where(
                LabSourceDerivationLink.child_source_version_id
                == child_source_version_id
            )
            .order_by(
                LabSourceDerivationLink.relation,
                LabSourceDerivationLink.parent_source_version_id,
                LabSourceDerivationLink.id,
            )
        )
        return list(result.scalars())

    async def child_derivation_links(
        self,
        parent_source_version_id: str,
    ) -> list[LabSourceDerivationLink]:
        result = await self.session.execute(
            select(LabSourceDerivationLink)
            .where(
                LabSourceDerivationLink.parent_source_version_id
                == parent_source_version_id
            )
            .order_by(
                LabSourceDerivationLink.relation,
                LabSourceDerivationLink.child_source_version_id,
                LabSourceDerivationLink.id,
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
