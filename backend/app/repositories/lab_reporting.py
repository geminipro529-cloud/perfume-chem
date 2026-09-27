"""Read-only repository for the B9 cross-domain science authority report."""

from __future__ import annotations

from typing import Any

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
from app.models.lab_claims import (
    LabClaimAuthoritySupportLink,
    LabClaimAuthorityVersion,
)
from app.models.lab_external_studies import (
    LabExternalCondition,
    LabExternalExperimentalUnit,
    LabExternalIdentityCrosswalk,
    LabExternalObservation,
    LabExternalStimulusComponent,
    LabExternalStimulusVersion,
    LabExternalStudyConflict,
    LabExternalStudyVersion,
)
from app.models.lab_properties import (
    LabPropertyConflictMember,
    LabPropertyConflictSet,
    LabPropertyObservation,
    LabSelectedAssertion,
    LabSelectedAssertionCandidate,
)
from app.models.lab_regulatory import (
    LabRegulatoryAuthorityFinding,
    LabRegulatorySnapshotVersion,
)
from app.models.lab_rules import (
    LabKnowledgeRule,
    LabRuleContradiction,
    LabRuleSupportEvidence,
)
from app.models.lab_sources import (
    LabEvidenceWorkflowEvent,
    LabSourceDocumentVersion,
    LabSourceExtractionRecord,
    LabSourceUseConstraintVersion,
)
from app.models.lab_thresholds import (
    LabOAVAssessment,
    LabThresholdObservationContext,
)

REPORT_MODEL_COLLECTIONS: dict[str, type[Any]] = {
    "source_documents": LabSourceDocumentVersion,
    "source_use_constraints": LabSourceUseConstraintVersion,
    "source_extractions": LabSourceExtractionRecord,
    "property_observations": LabPropertyObservation,
    "selected_assertions": LabSelectedAssertion,
    "property_conflict_sets": LabPropertyConflictSet,
    "contextual_thresholds": LabThresholdObservationContext,
    "oav_assessments": LabOAVAssessment,
    "knowledge_rules": LabKnowledgeRule,
    "rule_contradictions": LabRuleContradiction,
    "analytical_methods": LabAnalyticalMethodAuthority,
    "analytical_method_validation": LabMethodValidationRecord,
    "analytical_sequences": LabAnalyticalSequence,
    "analytical_runs": LabAnalyticalRunAuthority,
    "analytical_peaks": LabAnalyticalPeakAuthority,
    "gc_o_events": LabGCOEventAuthority,
    "analytical_claim_assessments": LabAnalyticalClaimAssessment,
    "regulatory_snapshots": LabRegulatorySnapshotVersion,
    "regulatory_findings": LabRegulatoryAuthorityFinding,
    "claim_authority_decisions": LabClaimAuthorityVersion,
    "claim_authority_support": LabClaimAuthoritySupportLink,
    "external_study_versions": LabExternalStudyVersion,
    "source_workflow_events": LabEvidenceWorkflowEvent,
    "property_conflict_members": LabPropertyConflictMember,
    "selected_assertion_candidates": LabSelectedAssertionCandidate,
    "rule_support_evidence": LabRuleSupportEvidence,
    "analytical_sequence_entries": LabAnalyticalSequenceEntry,
    "external_stimuli": LabExternalStimulusVersion,
    "external_stimulus_components": LabExternalStimulusComponent,
    "external_conditions": LabExternalCondition,
    "external_experimental_units": LabExternalExperimentalUnit,
    "external_observations": LabExternalObservation,
    "external_identity_crosswalks": LabExternalIdentityCrosswalk,
    "external_study_conflicts": LabExternalStudyConflict,
}


class ScienceReportRepository:
    """Query-only repository with no mutation surface."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def snapshot(self) -> dict[str, tuple[object, ...]]:
        """Read every B9 collection in deterministic order."""

        snapshot: dict[str, tuple[object, ...]] = {}
        for key, model in REPORT_MODEL_COLLECTIONS.items():
            result = await self._session.execute(
                select(model).order_by(model.created_at, model.id)
            )
            snapshot[key] = tuple(result.scalars().all())
        return snapshot


__all__ = ["REPORT_MODEL_COLLECTIONS", "ScienceReportRepository"]
