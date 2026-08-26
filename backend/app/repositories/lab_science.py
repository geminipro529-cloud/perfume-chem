"""Deterministic reads for immutable A2 science-authority records."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lab_science import (
    LabAnalyticalMethodVersion,
    LabAnalyticalPeak,
    LabAnalyticalQCRecord,
    LabAnalyticalRun,
    LabClaimAssessmentEvidenceLink,
    LabClaimAssessmentVersion,
    LabRegulatoryAssessmentVersion,
)


class LabScienceRepositoryMixin:
    """Science-authority reads; transaction ownership remains in LabService."""

    session: AsyncSession

    async def get_analytical_method_version(
        self,
        version_id: str,
    ) -> LabAnalyticalMethodVersion | None:
        return await self.session.get(LabAnalyticalMethodVersion, version_id)

    async def latest_analytical_method_version(
        self,
        method_id: str,
    ) -> LabAnalyticalMethodVersion | None:
        result = await self.session.execute(
            select(LabAnalyticalMethodVersion)
            .where(LabAnalyticalMethodVersion.method_id == method_id)
            .order_by(
                LabAnalyticalMethodVersion.version_number.desc(),
                LabAnalyticalMethodVersion.id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_analytical_run(
        self,
        run_id: str,
    ) -> LabAnalyticalRun | None:
        return await self.session.get(LabAnalyticalRun, run_id)

    async def get_analytical_peak(
        self,
        peak_id: str,
    ) -> LabAnalyticalPeak | None:
        return await self.session.get(LabAnalyticalPeak, peak_id)

    async def analytical_qc_records(
        self,
        run_id: str,
    ) -> list[LabAnalyticalQCRecord]:
        result = await self.session.execute(
            select(LabAnalyticalQCRecord)
            .where(LabAnalyticalQCRecord.analytical_run_id == run_id)
            .order_by(LabAnalyticalQCRecord.qc_key, LabAnalyticalQCRecord.id)
        )
        return list(result.scalars())

    async def get_regulatory_assessment_version(
        self,
        version_id: str,
    ) -> LabRegulatoryAssessmentVersion | None:
        return await self.session.get(LabRegulatoryAssessmentVersion, version_id)

    async def latest_regulatory_assessment_version(
        self,
        assessment_id: str,
    ) -> LabRegulatoryAssessmentVersion | None:
        result = await self.session.execute(
            select(LabRegulatoryAssessmentVersion)
            .where(
                LabRegulatoryAssessmentVersion.assessment_id == assessment_id
            )
            .order_by(
                LabRegulatoryAssessmentVersion.version_number.desc(),
                LabRegulatoryAssessmentVersion.id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_claim_assessment_version(
        self,
        version_id: str,
    ) -> LabClaimAssessmentVersion | None:
        return await self.session.get(LabClaimAssessmentVersion, version_id)

    async def latest_claim_assessment_version(
        self,
        claim_id: str,
    ) -> LabClaimAssessmentVersion | None:
        result = await self.session.execute(
            select(LabClaimAssessmentVersion)
            .where(LabClaimAssessmentVersion.claim_id == claim_id)
            .order_by(
                LabClaimAssessmentVersion.version_number.desc(),
                LabClaimAssessmentVersion.id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def claim_assessment_evidence_links(
        self,
        assessment_version_id: str,
    ) -> list[LabClaimAssessmentEvidenceLink]:
        result = await self.session.execute(
            select(LabClaimAssessmentEvidenceLink)
            .where(
                LabClaimAssessmentEvidenceLink.claim_assessment_version_id
                == assessment_version_id
            )
            .order_by(
                LabClaimAssessmentEvidenceLink.role,
                LabClaimAssessmentEvidenceLink.evidence_record_id,
                LabClaimAssessmentEvidenceLink.id,
            )
        )
        return list(result.scalars())
