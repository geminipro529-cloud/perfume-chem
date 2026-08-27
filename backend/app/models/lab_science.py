"""Append-oriented analytical, regulatory, and claim-authority records."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.lab import LabRecord, UTCDateTime

ANALYTICAL_TECHNIQUES = ("GCMS", "HS_SPME_GCMS", "GC_O", "OTHER")
ANALYTICAL_METHOD_STATUSES = ("DRAFT", "VALIDATED", "RETIRED")
ANALYTICAL_RUN_STATUSES = (
    "ACQUIRED",
    "PROCESSED",
    "QC_ACCEPTED",
    "QC_REJECTED",
)
ANALYTICAL_IDENTITY_STATES = ("UNASSIGNED", "TENTATIVE", "CONFIRMED")
ANALYTICAL_QC_STATUSES = ("PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE")
REGULATORY_SUBJECT_TYPES = ("FORMULA_VERSION", "BUILD_PLAN_VERSION", "BOTTLE")
REGULATORY_STANDARD_STATES = ("CURRENT", "SUPERSEDED", "UNKNOWN")
ASSESSMENT_RESULT_STATES = ("PASS", "FAIL", "UNKNOWN", "CONFLICT")
CLAIM_SUBJECT_TYPES = (
    "ANALYTICAL_RUN",
    "REGULATORY_ASSESSMENT",
    "FORMULA_VERSION",
    "BUILD_PLAN_VERSION",
    "BOTTLE",
    "EXPERIMENT",
)
CLAIM_DECISIONS = (
    "ALLOW_EXACT",
    "ALLOW_SCOPED",
    "ADVISORY_ONLY",
    "WITHHOLD_UNKNOWN",
    "BLOCK",
)
CLAIM_REVIEW_STATES = ("NOT_REQUIRED", "PENDING", "APPROVED", "REJECTED")
CLAIM_EVIDENCE_ROLES = ("DIRECT", "SUPPORTING", "CONTRADICTING", "LIMITATION")


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


class LabAnalyticalMethodVersion(LabRecord):
    __tablename__ = "lab_analytical_method_versions"
    __table_args__ = (
        UniqueConstraint(
            "method_id",
            "version_number",
            name="uq_lab_analytical_method_version",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_analytical_method_content_sha256",
        ),
        CheckConstraint(
            "version_number >= 1",
            name="ck_lab_analytical_method_version_positive",
        ),
        CheckConstraint(
            f"technique IN ({_quoted(ANALYTICAL_TECHNIQUES)})",
            name="ck_lab_analytical_method_technique",
        ),
        CheckConstraint(
            f"status IN ({_quoted(ANALYTICAL_METHOD_STATUSES)})",
            name="ck_lab_analytical_method_status",
        ),
    )

    method_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    technique: Mapped[str] = mapped_column(String(40), nullable=False)
    intended_use: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    method_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    evidence_record_id: Mapped[str] = mapped_column(
        ForeignKey("lab_evidence_records.id", ondelete="RESTRICT"), nullable=False
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_analytical_method_versions.id", ondelete="RESTRICT")
    )
    parent_sha256: Mapped[str | None] = mapped_column(String(64))


class LabAnalyticalRun(LabRecord):
    __tablename__ = "lab_analytical_runs"
    __table_args__ = (
        UniqueConstraint("run_id", name="uq_lab_analytical_run_identity"),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_analytical_run_content_sha256",
        ),
        CheckConstraint(
            f"run_kind IN ({_quoted(ANALYTICAL_TECHNIQUES)})",
            name="ck_lab_analytical_run_kind",
        ),
        CheckConstraint(
            f"status IN ({_quoted(ANALYTICAL_RUN_STATUSES)})",
            name="ck_lab_analytical_run_status",
        ),
        CheckConstraint(
            "experiment_id IS NOT NULL OR sample_id IS NOT NULL "
            "OR bottle_id IS NOT NULL OR formula_version_id IS NOT NULL "
            "OR build_plan_version_id IS NOT NULL",
            name="ck_lab_analytical_run_subject",
        ),
    )

    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    method_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_analytical_method_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    run_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    instrument_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(
        UTCDateTime(timezone=True), nullable=False
    )
    parameters_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    deviations_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    processing_version: Mapped[str] = mapped_column(String(100), nullable=False)
    experiment_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_experiments.id", ondelete="RESTRICT")
    )
    sample_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_samples.id", ondelete="RESTRICT")
    )
    bottle_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_bottles.id", ondelete="RESTRICT")
    )
    formula_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_formula_versions.id", ondelete="RESTRICT")
    )
    build_plan_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_build_plan_versions.id", ondelete="RESTRICT")
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabAnalyticalPeak(LabRecord):
    __tablename__ = "lab_analytical_peaks"
    __table_args__ = (
        UniqueConstraint(
            "analytical_run_id",
            "peak_key",
            name="uq_lab_analytical_peak_identity",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_analytical_peak_content_sha256",
        ),
        UniqueConstraint(
            "id",
            "analytical_run_id",
            name="uq_lab_analytical_peak_id_run",
        ),
        CheckConstraint(
            "(retention_time_minutes IS NULL OR retention_time_minutes >= 0) "
            "AND (retention_index IS NULL OR retention_index >= 0) "
            "AND (area IS NULL OR area >= 0) "
            "AND (response_factor IS NULL OR response_factor >= 0) "
            "AND (quantity IS NULL OR quantity >= 0) "
            "AND (standard_uncertainty IS NULL OR standard_uncertainty >= 0)",
            name="ck_lab_analytical_peak_nonnegative",
        ),
        CheckConstraint(
            "match_score IS NULL OR (match_score >= 0 AND match_score <= 1)",
            name="ck_lab_analytical_peak_match_score",
        ),
        CheckConstraint(
            f"identity_state IN ({_quoted(ANALYTICAL_IDENTITY_STATES)})",
            name="ck_lab_analytical_peak_identity_state",
        ),
        CheckConstraint(
            "identity_state != 'CONFIRMED' OR material_id IS NOT NULL",
            name="ck_lab_analytical_peak_confirmed_material",
        ),
        CheckConstraint(
            "(quantity IS NULL AND quantity_unit IS NULL "
            "AND quantitation_basis IS NULL) "
            "OR (quantity IS NOT NULL AND quantity_unit IS NOT NULL "
            "AND quantitation_basis IS NOT NULL)",
            name="ck_lab_analytical_peak_quantity_basis",
        ),
    )

    analytical_run_id: Mapped[str] = mapped_column(
        ForeignKey("lab_analytical_runs.id", ondelete="RESTRICT"), nullable=False
    )
    peak_key: Mapped[str] = mapped_column(String(100), nullable=False)
    retention_time_minutes: Mapped[float | None] = mapped_column(Float)
    retention_index: Mapped[float | None] = mapped_column(Float)
    area: Mapped[float | None] = mapped_column(Float)
    response_factor: Mapped[float | None] = mapped_column(Float)
    qualifier_ions_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    tentative_identity: Mapped[str | None] = mapped_column(String(255))
    material_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_materials.id", ondelete="RESTRICT")
    )
    identity_state: Mapped[str] = mapped_column(String(40), nullable=False)
    match_score: Mapped[float | None] = mapped_column(Float)
    quantitation_basis: Mapped[str | None] = mapped_column(String(100))
    quantity: Mapped[float | None] = mapped_column(Float)
    quantity_unit: Mapped[str | None] = mapped_column(String(40))
    standard_uncertainty: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabAnalyticalQCRecord(LabRecord):
    __tablename__ = "lab_analytical_qc_records"
    __table_args__ = (
        UniqueConstraint(
            "analytical_run_id",
            "qc_key",
            name="uq_lab_analytical_qc_identity",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_analytical_qc_content_sha256",
        ),
        CheckConstraint(
            f"status IN ({_quoted(ANALYTICAL_QC_STATUSES)})",
            name="ck_lab_analytical_qc_status",
        ),
    )

    analytical_run_id: Mapped[str] = mapped_column(
        ForeignKey("lab_analytical_runs.id", ondelete="RESTRICT"), nullable=False
    )
    qc_key: Mapped[str] = mapped_column(String(100), nullable=False)
    qc_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    criteria_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    observed_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    evidence_record_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_evidence_records.id", ondelete="RESTRICT")
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabAnalyticalAttachment(LabRecord):
    __tablename__ = "lab_analytical_attachments"
    __table_args__ = (
        UniqueConstraint(
            "analytical_run_id",
            "attachment_kind",
            "content_sha256",
            name="uq_lab_analytical_attachment",
        ),
        CheckConstraint(
            "byte_length >= 0",
            name="ck_lab_analytical_attachment_length",
        ),
    )

    analytical_run_id: Mapped[str] = mapped_column(
        ForeignKey("lab_analytical_runs.id", ondelete="RESTRICT"), nullable=False
    )
    attachment_kind: Mapped[str] = mapped_column(String(100), nullable=False)
    media_type: Mapped[str] = mapped_column(String(255), nullable=False)
    byte_length: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_locator: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_record_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_evidence_records.id", ondelete="RESTRICT")
    )


class LabGCOEvent(LabRecord):
    __tablename__ = "lab_gco_events"
    __table_args__ = (
        UniqueConstraint(
            "analytical_run_id",
            "event_key",
            name="uq_lab_gco_event_identity",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_gco_event_content_sha256",
        ),
        ForeignKeyConstraint(
            ["analytical_peak_id", "analytical_run_id"],
            ["lab_analytical_peaks.id", "lab_analytical_peaks.analytical_run_id"],
            name="fk_lab_gco_peak_run",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "(retention_time_minutes IS NULL OR retention_time_minutes >= 0) "
            "AND (retention_index IS NULL OR retention_index >= 0)",
            name="ck_lab_gco_event_position",
        ),
        CheckConstraint(
            "intensity IS NULL OR (intensity >= 0 AND intensity <= 1)",
            name="ck_lab_gco_event_intensity",
        ),
    )

    analytical_run_id: Mapped[str] = mapped_column(
        ForeignKey("lab_analytical_runs.id", ondelete="RESTRICT"), nullable=False
    )
    analytical_peak_id: Mapped[str | None] = mapped_column(String(36))
    event_key: Mapped[str] = mapped_column(String(100), nullable=False)
    retention_time_minutes: Mapped[float | None] = mapped_column(Float)
    retention_index: Mapped[float | None] = mapped_column(Float)
    descriptor: Mapped[str] = mapped_column(Text, nullable=False)
    intensity: Mapped[float | None] = mapped_column(Float)
    assessor_pseudonym: Mapped[str] = mapped_column(String(255), nullable=False)
    repeatability_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    evidence_record_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_evidence_records.id", ondelete="RESTRICT")
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabRegulatoryAssessmentVersion(LabRecord):
    __tablename__ = "lab_regulatory_assessment_versions"
    __table_args__ = (
        UniqueConstraint(
            "assessment_id",
            "version_number",
            name="uq_lab_regulatory_assessment_version",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_regulatory_assessment_content_sha256",
        ),
        CheckConstraint(
            "version_number >= 1",
            name="ck_lab_regulatory_assessment_version_positive",
        ),
        CheckConstraint(
            f"subject_type IN ({_quoted(REGULATORY_SUBJECT_TYPES)})",
            name="ck_lab_regulatory_assessment_subject_type",
        ),
        CheckConstraint(
            f"standard_state IN ({_quoted(REGULATORY_STANDARD_STATES)})",
            name="ck_lab_regulatory_assessment_standard_state",
        ),
        CheckConstraint(
            f"result_state IN ({_quoted(ASSESSMENT_RESULT_STATES)})",
            name="ck_lab_regulatory_assessment_result_state",
        ),
        CheckConstraint(
            "finished_product_concentration IS NULL "
            "OR finished_product_concentration >= 0",
            name="ck_lab_regulatory_assessment_concentration",
        ),
    )

    assessment_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(40), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    parent_version_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "lab_regulatory_assessment_versions.id",
            ondelete="RESTRICT",
        )
    )
    standard_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    standard_amendment: Mapped[str | None] = mapped_column(String(100))
    standard_state: Mapped[str] = mapped_column(String(40), nullable=False)
    source_evidence_record_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_evidence_records.id", ondelete="RESTRICT")
    )
    jurisdiction: Mapped[str] = mapped_column(String(100), nullable=False)
    product_category: Mapped[str] = mapped_column(String(255), nullable=False)
    concentration_basis: Mapped[str] = mapped_column(String(100), nullable=False)
    finished_product_concentration: Mapped[float | None] = mapped_column(Float)
    effective_date: Mapped[date | None] = mapped_column(Date)
    evaluated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(timezone=True), nullable=False
    )
    result_state: Mapped[str] = mapped_column(String(40), nullable=False)
    assumptions_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    unresolved_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    permitted_wording: Mapped[str | None] = mapped_column(Text)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_sha256: Mapped[str | None] = mapped_column(String(64))


class LabRegulatoryFinding(LabRecord):
    __tablename__ = "lab_regulatory_findings"
    __table_args__ = (
        UniqueConstraint(
            "regulatory_assessment_version_id",
            "finding_key",
            name="uq_lab_regulatory_finding_identity",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_regulatory_finding_content_sha256",
        ),
        CheckConstraint(
            "(observed_fraction IS NULL OR observed_fraction >= 0) "
            "AND (maximum_fraction IS NULL OR maximum_fraction >= 0)",
            name="ck_lab_regulatory_finding_fractions",
        ),
        CheckConstraint(
            f"result_state IN ({_quoted(ASSESSMENT_RESULT_STATES)})",
            name="ck_lab_regulatory_finding_result_state",
        ),
        CheckConstraint(
            "result_state != 'PASS' OR "
            "(observed_fraction IS NOT NULL AND maximum_fraction IS NOT NULL "
            "AND concentration_basis IS NOT NULL)",
            name="ck_lab_regulatory_finding_pass_basis",
        ),
    )

    regulatory_assessment_version_id: Mapped[str] = mapped_column(
        ForeignKey(
            "lab_regulatory_assessment_versions.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    finding_key: Mapped[str] = mapped_column(String(100), nullable=False)
    restriction_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_restrictions.id", ondelete="RESTRICT")
    )
    material_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_materials.id", ondelete="RESTRICT")
    )
    substance_identity: Mapped[str] = mapped_column(String(255), nullable=False)
    observed_fraction: Mapped[float | None] = mapped_column(Float)
    maximum_fraction: Mapped[float | None] = mapped_column(Float)
    concentration_basis: Mapped[str | None] = mapped_column(String(100))
    result_state: Mapped[str] = mapped_column(String(40), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_record_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_evidence_records.id", ondelete="RESTRICT")
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabClaimAssessmentVersion(LabRecord):
    __tablename__ = "lab_claim_assessment_versions"
    __table_args__ = (
        UniqueConstraint(
            "claim_id",
            "version_number",
            name="uq_lab_claim_assessment_version",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_claim_assessment_content_sha256",
        ),
        CheckConstraint(
            "version_number >= 1",
            name="ck_lab_claim_assessment_version_positive",
        ),
        CheckConstraint(
            f"subject_type IN ({_quoted(CLAIM_SUBJECT_TYPES)})",
            name="ck_lab_claim_assessment_subject_type",
        ),
        CheckConstraint(
            f"decision IN ({_quoted(CLAIM_DECISIONS)})",
            name="ck_lab_claim_assessment_decision",
        ),
        CheckConstraint(
            f"human_review_state IN ({_quoted(CLAIM_REVIEW_STATES)})",
            name="ck_lab_claim_assessment_review_state",
        ),
    )

    claim_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    claim_type: Mapped[str] = mapped_column(String(100), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(40), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    parent_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_claim_assessment_versions.id", ondelete="RESTRICT")
    )
    policy_version: Mapped[str] = mapped_column(String(100), nullable=False)
    decision: Mapped[str] = mapped_column(String(40), nullable=False)
    authority_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    missing_evidence_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    conflicts_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    permitted_wording: Mapped[str | None] = mapped_column(Text)
    forbidden_wording: Mapped[str | None] = mapped_column(Text)
    human_review_state: Mapped[str] = mapped_column(String(40), nullable=False)
    reviewer_pseudonym: Mapped[str | None] = mapped_column(String(255))
    reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(timezone=True))
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_sha256: Mapped[str | None] = mapped_column(String(64))


class LabClaimAssessmentEvidenceLink(LabRecord):
    __tablename__ = "lab_claim_assessment_evidence_links"
    __table_args__ = (
        UniqueConstraint(
            "claim_assessment_version_id",
            "evidence_record_id",
            "role",
            name="uq_lab_claim_assessment_evidence_link",
        ),
        CheckConstraint(
            f"role IN ({_quoted(CLAIM_EVIDENCE_ROLES)})",
            name="ck_lab_claim_evidence_role",
        ),
    )

    claim_assessment_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_claim_assessment_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    evidence_record_id: Mapped[str] = mapped_column(
        ForeignKey("lab_evidence_records.id", ondelete="RESTRICT"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(40), nullable=False)


SCIENCE_AUTHORITY_TABLE_NAMES = {
    "lab_analytical_method_versions",
    "lab_analytical_runs",
    "lab_analytical_peaks",
    "lab_analytical_qc_records",
    "lab_analytical_attachments",
    "lab_gco_events",
    "lab_regulatory_assessment_versions",
    "lab_regulatory_findings",
    "lab_claim_assessment_versions",
    "lab_claim_assessment_evidence_links",
}


__all__ = [
    "ANALYTICAL_IDENTITY_STATES",
    "ANALYTICAL_METHOD_STATUSES",
    "ANALYTICAL_QC_STATUSES",
    "ANALYTICAL_RUN_STATUSES",
    "ANALYTICAL_TECHNIQUES",
    "ASSESSMENT_RESULT_STATES",
    "CLAIM_DECISIONS",
    "CLAIM_EVIDENCE_ROLES",
    "CLAIM_REVIEW_STATES",
    "CLAIM_SUBJECT_TYPES",
    "REGULATORY_STANDARD_STATES",
    "REGULATORY_SUBJECT_TYPES",
    "SCIENCE_AUTHORITY_TABLE_NAMES",
    "LabAnalyticalAttachment",
    "LabAnalyticalMethodVersion",
    "LabAnalyticalPeak",
    "LabAnalyticalQCRecord",
    "LabAnalyticalRun",
    "LabClaimAssessmentEvidenceLink",
    "LabClaimAssessmentVersion",
    "LabGCOEvent",
    "LabRegulatoryAssessmentVersion",
    "LabRegulatoryFinding",
]
