"""Read-only response contracts for B9 science authority reporting."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SCIENCE_EVIDENCE_CLASSES = (
    "MEASURED",
    "LITERATURE_DERIVED",
    "SUPPLIER_PROVIDED",
    "EMPIRICALLY_CALIBRATED",
    "MODEL_ESTIMATED",
    "HEURISTIC",
    "SPECULATIVE",
    "UNKNOWN",
)
SCIENCE_SECTION_KEYS = (
    "source_documents",
    "source_extractions",
    "property_observations",
    "selected_assertions",
    "property_conflict_sets",
    "contextual_thresholds",
    "oav_assessments",
    "knowledge_rules",
    "rule_contradictions",
    "analytical_methods",
    "analytical_method_validation",
    "analytical_sequences",
    "analytical_runs",
    "analytical_peaks",
    "gc_o_events",
    "analytical_claim_assessments",
    "regulatory_snapshots",
    "regulatory_findings",
    "claim_authority_decisions",
    "claim_authority_support",
)

EvidenceClass = Literal[
    "MEASURED",
    "LITERATURE_DERIVED",
    "SUPPLIER_PROVIDED",
    "EMPIRICALLY_CALIBRATED",
    "MODEL_ESTIMATED",
    "HEURISTIC",
    "SPECULATIVE",
    "UNKNOWN",
]
ScienceSectionKey = Literal[
    "source_documents",
    "source_extractions",
    "property_observations",
    "selected_assertions",
    "property_conflict_sets",
    "contextual_thresholds",
    "oav_assessments",
    "knowledge_rules",
    "rule_contradictions",
    "analytical_methods",
    "analytical_method_validation",
    "analytical_sequences",
    "analytical_runs",
    "analytical_peaks",
    "gc_o_events",
    "analytical_claim_assessments",
    "regulatory_snapshots",
    "regulatory_findings",
    "claim_authority_decisions",
    "claim_authority_support",
]


class ScienceView(str, Enum):
    """Permitted report views."""

    STRICT = "strict"
    EXPLORATORY = "exploratory"


class ScienceReportModel(BaseModel):
    """Closed response base."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ScienceRecord(ScienceReportModel):
    """One explicitly allowlisted authority record."""

    id: str = Field(min_length=1)
    created_at: str = Field(min_length=1)
    evidence_class: EvidenceClass
    strict_eligible: bool
    strict_reason_codes: tuple[str, ...]
    authority: dict[str, object]
    provenance: dict[str, object]
    facts: dict[str, object]


class ScienceSection(ScienceReportModel):
    """One ordered report section."""

    key: ScienceSectionKey
    label: str = Field(min_length=1)
    included: tuple[ScienceRecord, ...]
    withheld: tuple[ScienceRecord, ...]
    total_count: int = Field(ge=0)
    included_count: int = Field(ge=0)
    withheld_count: int = Field(ge=0)


class ScienceReportPolicy(ScienceReportModel):
    """Machine-readable presentation boundaries."""

    numeric_aggregation_forbidden: Literal[True] = True
    strict_unknowns_visible: Literal[True] = True
    explicit_evidence_labels_required: Literal[True] = True
    source_field_allowlists_required: Literal[True] = True
    release_authority: Literal[False] = False


class ScienceReportTotals(ScienceReportModel):
    """Count reconciliation without a score or percentage."""

    section_count: int = Field(ge=0)
    total_records: int = Field(ge=0)
    included_records: int = Field(ge=0)
    withheld_records: int = Field(ge=0)


class ScienceAuthorityReport(ScienceReportModel):
    """Canonical B9 read-only report."""

    schema_version: Literal["lab-science-authority-report-v1"]
    view: ScienceView
    authority_state: Literal["READ_ONLY_NON_PROMOTING"]
    evidence_classes: tuple[EvidenceClass, ...]
    policy: ScienceReportPolicy
    sections: tuple[ScienceSection, ...]
    totals: ScienceReportTotals
    report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


__all__ = [
    "SCIENCE_EVIDENCE_CLASSES",
    "SCIENCE_SECTION_KEYS",
    "EvidenceClass",
    "ScienceAuthorityReport",
    "ScienceRecord",
    "ScienceReportPolicy",
    "ScienceReportTotals",
    "ScienceSection",
    "ScienceSectionKey",
    "ScienceView",
]
