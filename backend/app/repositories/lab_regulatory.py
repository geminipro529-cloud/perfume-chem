"""Explicit-ID reads for append-only B6 regulatory authority."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lab_regulatory import (
    LabRegulatoryAuthorityFinding,
    LabRegulatoryCompositionEntry,
    LabRegulatoryCompositionProfile,
    LabRegulatoryRuleVersion,
    LabRegulatorySnapshotVersion,
    LabRegulatorySourceVersion,
    LabSupplierDocumentBinding,
)


class LabRegulatoryAuthorityRepositoryMixin:
    """Read B6 authority without unscoped ambient selection."""

    session: AsyncSession

    async def get_regulatory_source_version(
        self,
        record_id: str,
    ) -> LabRegulatorySourceVersion | None:
        return await self.session.get(LabRegulatorySourceVersion, record_id)

    async def latest_regulatory_source_version(
        self,
        authority_id: str,
    ) -> LabRegulatorySourceVersion | None:
        result = await self.session.execute(
            select(LabRegulatorySourceVersion)
            .where(LabRegulatorySourceVersion.authority_id == authority_id)
            .order_by(
                LabRegulatorySourceVersion.revision_number.desc(),
                LabRegulatorySourceVersion.id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def superseding_regulatory_source(
        self,
        source_version_id: str,
    ) -> LabRegulatorySourceVersion | None:
        result = await self.session.execute(
            select(LabRegulatorySourceVersion)
            .where(
                LabRegulatorySourceVersion.supersedes_source_version_id
                == source_version_id
            )
            .order_by(
                LabRegulatorySourceVersion.checked_at,
                LabRegulatorySourceVersion.revision_number,
                LabRegulatorySourceVersion.id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_regulatory_rule_version(
        self,
        record_id: str,
    ) -> LabRegulatoryRuleVersion | None:
        return await self.session.get(LabRegulatoryRuleVersion, record_id)

    async def latest_regulatory_rule_version(
        self,
        rule_id: str,
    ) -> LabRegulatoryRuleVersion | None:
        result = await self.session.execute(
            select(LabRegulatoryRuleVersion)
            .where(LabRegulatoryRuleVersion.rule_id == rule_id)
            .order_by(
                LabRegulatoryRuleVersion.revision_number.desc(),
                LabRegulatoryRuleVersion.id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_supplier_document_binding(
        self,
        record_id: str,
    ) -> LabSupplierDocumentBinding | None:
        return await self.session.get(LabSupplierDocumentBinding, record_id)

    async def get_regulatory_composition_profile(
        self,
        record_id: str,
    ) -> LabRegulatoryCompositionProfile | None:
        return await self.session.get(LabRegulatoryCompositionProfile, record_id)

    async def latest_regulatory_composition_profile(
        self,
        profile_id: str,
    ) -> LabRegulatoryCompositionProfile | None:
        result = await self.session.execute(
            select(LabRegulatoryCompositionProfile)
            .where(LabRegulatoryCompositionProfile.profile_id == profile_id)
            .order_by(
                LabRegulatoryCompositionProfile.version_number.desc(),
                LabRegulatoryCompositionProfile.id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def regulatory_composition_entries(
        self,
        profile_version_id: str,
    ) -> list[LabRegulatoryCompositionEntry]:
        result = await self.session.execute(
            select(LabRegulatoryCompositionEntry)
            .where(
                LabRegulatoryCompositionEntry.composition_profile_id
                == profile_version_id
            )
            .order_by(
                LabRegulatoryCompositionEntry.position,
                LabRegulatoryCompositionEntry.id,
            )
        )
        return list(result.scalars())

    async def get_regulatory_snapshot_version(
        self,
        record_id: str,
    ) -> LabRegulatorySnapshotVersion | None:
        return await self.session.get(LabRegulatorySnapshotVersion, record_id)

    async def latest_regulatory_snapshot_version(
        self,
        snapshot_id: str,
    ) -> LabRegulatorySnapshotVersion | None:
        result = await self.session.execute(
            select(LabRegulatorySnapshotVersion)
            .where(LabRegulatorySnapshotVersion.snapshot_id == snapshot_id)
            .order_by(
                LabRegulatorySnapshotVersion.version_number.desc(),
                LabRegulatorySnapshotVersion.id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def regulatory_authority_findings(
        self,
        snapshot_version_id: str,
    ) -> list[LabRegulatoryAuthorityFinding]:
        result = await self.session.execute(
            select(LabRegulatoryAuthorityFinding)
            .where(
                LabRegulatoryAuthorityFinding.snapshot_version_id
                == snapshot_version_id
            )
            .order_by(
                LabRegulatoryAuthorityFinding.enforced.desc(),
                LabRegulatoryAuthorityFinding.rule_version_id,
                LabRegulatoryAuthorityFinding.id,
            )
        )
        return list(result.scalars())

    async def passed_snapshot_for_legacy_assessment(
        self,
        assessment_version_id: str,
    ) -> LabRegulatorySnapshotVersion | None:
        result = await self.session.execute(
            select(LabRegulatorySnapshotVersion)
            .where(
                LabRegulatorySnapshotVersion.legacy_assessment_version_id
                == assessment_version_id,
                LabRegulatorySnapshotVersion.result_state
                == "PASS_FOR_DECLARED_SCOPE",
            )
            .order_by(
                LabRegulatorySnapshotVersion.evaluated_at.desc(),
                LabRegulatorySnapshotVersion.id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()
