"""Append-only B5 analytical method, run, QC, and claim authority."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.lab import LabRecord, UTCDateTime

ANALYTICAL_METHOD_AUTHORITY_STATUSES = (
    "EXPLORATORY",
    "VERIFIED",
    "VALIDATED_FOR_SCOPE",
    "RETIRED",
)
METHOD_VALIDATION_RESULTS = ("PASS", "FAIL", "INCOMPLETE")
ANALYTICAL_SEQUENCE_STATUSES = ("PLANNED", "ACQUIRED", "CANCELLED")
ANALYTICAL_SEQUENCE_ENTRY_ROLES = (
    "SAMPLE",
    "SOLVENT_BLANK",
    "METHOD_BLANK",
    "CALIBRATION_STANDARD",
    "INTERNAL_STANDARD",
    "SPIKE",
    "DUPLICATE",
    "REPLICATE",
    "QC_SAMPLE",
    "RI_STANDARD",
    "CONTROL",
)
ANALYTICAL_PRIMARY_SUBJECT_TYPES = (
    "SAMPLE",
    "STOCK_LOT",
    "NATURAL_LOT",
    "FORMULA_VERSION",
    "BUILD_PLAN_VERSION",
    "BOTTLE_STREAM",
)
ANALYTICAL_RUN_DISPOSITIONS = (
    "PENDING",
    "ACCEPTED",
    "QUALIFIED",
    "REJECTED",
)
ANALYTICAL_IDENTITY_AUTHORITY_STATES = (
    "CONFIRMED_AUTHENTIC_STANDARD",
    "STRONGLY_SUPPORTED_RI_PLUS_SPECTRUM",
    "PROBABLE",
    "TENTATIVE_LIBRARY_MATCH",
    "UNRESOLVED",
    "REJECTED",
)
ANALYTICAL_STANDARD_MATCH_STATES = ("NOT_RUN", "MATCHED", "FAILED")
ANALYTICAL_QUANTITATION_STATES = (
    "NONE",
    "AREA_PERCENT_ONLY",
    "CALIBRATED_CONCENTRATION",
)
GCO_TRAINING_STATES = ("QUALIFIED", "IN_TRAINING", "UNKNOWN")
GCO_WINDOW_BASES = ("RETENTION_TIME", "RETENTION_INDEX")
ANALYTICAL_CLAIM_TYPES = ("IDENTITY", "QUANTITY")
ANALYTICAL_CLAIM_DECISIONS = (
    "SUPPORTED_FOR_SCOPE",
    "ADVISORY_ONLY",
    "WITHHELD",
)


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


class LabAnalyticalMethodAuthority(LabRecord):
    __tablename__ = "lab_analytical_method_authorities"
    __table_args__ = (
        UniqueConstraint(
            "method_version_id",
            name="uq_lab_analytical_method_authority_version",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_analytical_method_authority_content_sha256",
        ),
        CheckConstraint(
            f"status IN ({_quoted(ANALYTICAL_METHOD_AUTHORITY_STATUSES)})",
            name="ck_lab_analytical_method_authority_status",
        ),
        CheckConstraint(
            "length(source_artifact_sha256) = 64",
            name="ck_lab_analytical_method_authority_source_sha256",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_analytical_method_authority_content_sha256",
        ),
        Index(
            "ix_lab_analytical_method_authorities_status",
            "status",
        ),
    )

    method_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_analytical_method_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    analyte_scope_json: Mapped[list] = mapped_column(
        JSON,
        default=list,
        server_default=text("'[]'"),
        nullable=False,
    )
    instrument_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    detector_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    software_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    separation_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    acquisition_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    sample_preparation_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    hs_spme_json: Mapped[dict | None] = mapped_column(JSON)
    standards_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    calibration_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    response_factors_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    identity_criteria_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    integration_policy_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    qc_plan_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    raw_data_policy_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    source_document_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_source_document_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_locator_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    source_artifact_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabMethodValidationRecord(LabRecord):
    __tablename__ = "lab_method_validation_records"
    __table_args__ = (
        UniqueConstraint(
            "method_authority_id",
            "intended_claim",
            "scope_sha256",
            name="uq_lab_method_validation_scope",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_method_validation_content_sha256",
        ),
        CheckConstraint(
            f"result IN ({_quoted(METHOD_VALIDATION_RESULTS)})",
            name="ck_lab_method_validation_result",
        ),
        CheckConstraint(
            "length(scope_sha256) = 64",
            name="ck_lab_method_validation_scope_sha256",
        ),
        CheckConstraint(
            "length(source_artifact_sha256) = 64",
            name="ck_lab_method_validation_source_sha256",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_method_validation_content_sha256",
        ),
        CheckConstraint(
            "length(trim(reviewer_pseudonym)) > 0 "
            "AND reviewed_at IS NOT NULL",
            name="ck_lab_method_validation_review",
        ),
        Index(
            "ix_lab_method_validation_records_method_authority_id",
            "method_authority_id",
        ),
    )

    method_authority_id: Mapped[str] = mapped_column(
        ForeignKey(
            "lab_analytical_method_authorities.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    intended_claim: Mapped[str] = mapped_column(Text, nullable=False)
    matrix_scope_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    scope_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    characteristics_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    acceptance_criteria_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    result: Mapped[str] = mapped_column(String(40), nullable=False)
    limitations_json: Mapped[list] = mapped_column(
        JSON,
        default=list,
        server_default=text("'[]'"),
        nullable=False,
    )
    measurement_uncertainty_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    reviewer_pseudonym: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    reviewed_at: Mapped[datetime] = mapped_column(
        UTCDateTime(timezone=True), nullable=False
    )
    source_document_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_source_document_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_locator_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    source_artifact_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabAnalyticalSequence(LabRecord):
    __tablename__ = "lab_analytical_sequences"
    __table_args__ = (
        UniqueConstraint(
            "sequence_key",
            name="uq_lab_analytical_sequence_key",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_analytical_sequence_content_sha256",
        ),
        CheckConstraint(
            f"status IN ({_quoted(ANALYTICAL_SEQUENCE_STATUSES)})",
            name="ck_lab_analytical_sequence_status",
        ),
        CheckConstraint(
            "entry_count >= 1",
            name="ck_lab_analytical_sequence_entry_count",
        ),
        CheckConstraint(
            "length(content_sha256) = 64 AND length(entries_sha256) = 64",
            name="ck_lab_analytical_sequence_content_sha256",
        ),
        CheckConstraint(
            "status != 'ACQUIRED' OR acquired_at IS NOT NULL",
            name="ck_lab_analytical_sequence_acquired_at",
        ),
        Index(
            "ix_lab_analytical_sequences_method_authority_id",
            "method_authority_id",
        ),
    )

    sequence_key: Mapped[str] = mapped_column(String(255), nullable=False)
    method_authority_id: Mapped[str] = mapped_column(
        ForeignKey(
            "lab_analytical_method_authorities.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    instrument_identifier: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    entry_count: Mapped[int] = mapped_column(Integer, nullable=False)
    entries_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    acquired_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(timezone=True)
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabAnalyticalSequenceEntry(LabRecord):
    __tablename__ = "lab_analytical_sequence_entries"
    __table_args__ = (
        UniqueConstraint(
            "sequence_id",
            "injection_order",
            name="uq_lab_analytical_sequence_entry_order",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_analytical_sequence_entry_content_sha256",
        ),
        UniqueConstraint(
            "id",
            "sequence_id",
            name="uq_lab_analytical_sequence_entry_id_sequence",
        ),
        CheckConstraint(
            f"role IN ({_quoted(ANALYTICAL_SEQUENCE_ENTRY_ROLES)})",
            name="ck_lab_analytical_sequence_entry_role",
        ),
        CheckConstraint(
            "injection_order >= 1",
            name="ck_lab_analytical_sequence_entry_order",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_analytical_sequence_entry_content_sha256",
        ),
        Index(
            "ix_lab_analytical_sequence_entries_sequence_id",
            "sequence_id",
        ),
    )

    sequence_id: Mapped[str] = mapped_column(
        ForeignKey("lab_analytical_sequences.id", ondelete="RESTRICT"),
        nullable=False,
    )
    injection_order: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    reference: Mapped[str] = mapped_column(Text, nullable=False)
    level_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabAnalyticalRunAuthority(LabRecord):
    __tablename__ = "lab_analytical_run_authorities"
    __table_args__ = (
        UniqueConstraint(
            "analytical_run_id",
            name="uq_lab_analytical_run_authority_run",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_analytical_run_authority_content_sha256",
        ),
        ForeignKeyConstraint(
            ["sequence_entry_id", "sequence_id"],
            [
                "lab_analytical_sequence_entries.id",
                "lab_analytical_sequence_entries.sequence_id",
            ],
            name="fk_lab_analytical_run_authority_sequence_entry",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            f"subject_type IN ({_quoted(ANALYTICAL_PRIMARY_SUBJECT_TYPES)})",
            name="ck_lab_analytical_run_authority_subject_type",
        ),
        CheckConstraint(
            "(subject_type = 'BOTTLE_STREAM' "
            "AND subject_stream_sequence IS NOT NULL "
            "AND subject_stream_sequence >= 1) OR "
            "(subject_type != 'BOTTLE_STREAM' "
            "AND subject_stream_sequence IS NULL)",
            name="ck_lab_analytical_run_authority_subject_shape",
        ),
        CheckConstraint(
            f"disposition IN ({_quoted(ANALYTICAL_RUN_DISPOSITIONS)})",
            name="ck_lab_analytical_run_authority_disposition",
        ),
        CheckConstraint(
            "raw_vendor_attachment_id != open_export_attachment_id",
            name="ck_lab_analytical_run_authority_raw_distinct",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_analytical_run_authority_content_sha256",
        ),
        Index(
            "ix_lab_analytical_run_authorities_sequence_id",
            "sequence_id",
        ),
        Index(
            "ix_lab_analytical_run_authorities_subject",
            "subject_type",
            "subject_id",
        ),
    )

    analytical_run_id: Mapped[str] = mapped_column(
        ForeignKey("lab_analytical_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    method_authority_id: Mapped[str] = mapped_column(
        ForeignKey(
            "lab_analytical_method_authorities.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    sequence_id: Mapped[str] = mapped_column(String(36), nullable=False)
    sequence_entry_id: Mapped[str] = mapped_column(String(36), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(40), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(36), nullable=False)
    subject_stream_sequence: Mapped[int | None] = mapped_column(Integer)
    matrix_scope_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    applicability_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    instrument_state_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    processing_details_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    deviation_assessment_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    reviewer_pseudonym: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    reviewed_at: Mapped[datetime] = mapped_column(
        UTCDateTime(timezone=True), nullable=False
    )
    disposition: Mapped[str] = mapped_column(String(40), nullable=False)
    raw_vendor_attachment_id: Mapped[str] = mapped_column(
        ForeignKey("lab_analytical_attachments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    open_export_attachment_id: Mapped[str] = mapped_column(
        ForeignKey("lab_analytical_attachments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabAnalyticalPeakAuthority(LabRecord):
    __tablename__ = "lab_analytical_peak_authorities"
    __table_args__ = (
        UniqueConstraint(
            "analytical_peak_id",
            name="uq_lab_analytical_peak_authority_peak",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_analytical_peak_authority_content_sha256",
        ),
        CheckConstraint(
            "identity_state IN "
            f"({_quoted(ANALYTICAL_IDENTITY_AUTHORITY_STATES)})",
            name="ck_lab_analytical_peak_authority_identity_state",
        ),
        CheckConstraint(
            "authentic_standard_state IN "
            f"({_quoted(ANALYTICAL_STANDARD_MATCH_STATES)}) "
            "AND co_injection_state IN "
            f"({_quoted(ANALYTICAL_STANDARD_MATCH_STATES)})",
            name="ck_lab_analytical_peak_authority_standard_states",
        ),
        CheckConstraint(
            "quantitation_state IN "
            f"({_quoted(ANALYTICAL_QUANTITATION_STATES)})",
            name="ck_lab_analytical_peak_authority_quantitation_state",
        ),
        CheckConstraint(
            "identity_state != 'CONFIRMED_AUTHENTIC_STANDARD' "
            "OR authentic_standard_state = 'MATCHED' "
            "OR co_injection_state = 'MATCHED'",
            name="ck_lab_analytical_peak_authority_confirmed_standard",
        ),
        CheckConstraint(
            "identity_state IN ('UNRESOLVED', 'REJECTED') "
            "OR identity_label IS NOT NULL",
            name="ck_lab_analytical_peak_authority_identity_label",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_analytical_peak_authority_content_sha256",
        ),
        Index(
            "ix_lab_analytical_peak_authorities_identity_state",
            "identity_state",
        ),
    )

    analytical_peak_id: Mapped[str] = mapped_column(
        ForeignKey("lab_analytical_peaks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    analytical_run_authority_id: Mapped[str] = mapped_column(
        ForeignKey(
            "lab_analytical_run_authorities.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    identity_state: Mapped[str] = mapped_column(String(60), nullable=False)
    identity_label: Mapped[str | None] = mapped_column(Text)
    stationary_phase: Mapped[str] = mapped_column(Text, nullable=False)
    spectrum_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    deconvolution_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    library_candidates_json: Mapped[list] = mapped_column(
        JSON,
        default=list,
        server_default=text("'[]'"),
        nullable=False,
    )
    exact_mass_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    authentic_standard_state: Mapped[str] = mapped_column(
        String(40), nullable=False
    )
    co_injection_state: Mapped[str] = mapped_column(
        String(40), nullable=False
    )
    quantifier_ions_json: Mapped[list] = mapped_column(
        JSON,
        default=list,
        server_default=text("'[]'"),
        nullable=False,
    )
    coelution_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    manual_review_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    identity_decision_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    quantitation_state: Mapped[str] = mapped_column(
        String(40), nullable=False
    )
    quantitation_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    applicability_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    reviewer_pseudonym: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    reviewed_at: Mapped[datetime] = mapped_column(
        UTCDateTime(timezone=True), nullable=False
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabGCOEventAuthority(LabRecord):
    __tablename__ = "lab_gco_event_authorities"
    __table_args__ = (
        UniqueConstraint(
            "gco_event_id",
            name="uq_lab_gco_event_authority_event",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_gco_event_authority_content_sha256",
        ),
        CheckConstraint(
            f"assessor_training_state IN ({_quoted(GCO_TRAINING_STATES)})",
            name="ck_lab_gco_event_authority_training_state",
        ),
        CheckConstraint(
            f"window_basis IN ({_quoted(GCO_WINDOW_BASES)})",
            name="ck_lab_gco_event_authority_window_basis",
        ),
        CheckConstraint(
            "window_start >= 0 AND window_end >= window_start",
            name="ck_lab_gco_event_authority_window",
        ),
        CheckConstraint(
            "replicate_index >= 1 AND replicate_count >= replicate_index",
            name="ck_lab_gco_event_authority_replicates",
        ),
        CheckConstraint(
            "detection_frequency >= 0 AND detection_frequency <= 1",
            name="ck_lab_gco_event_authority_frequency",
        ),
        CheckConstraint(
            "exact_identity_claim = false",
            name="ck_lab_gco_event_authority_no_exact_identity",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_gco_event_authority_content_sha256",
        ),
        Index(
            "ix_lab_gco_event_authorities_training_state",
            "assessor_training_state",
        ),
    )

    gco_event_id: Mapped[str] = mapped_column(
        ForeignKey("lab_gco_events.id", ondelete="RESTRICT"),
        nullable=False,
    )
    analytical_run_authority_id: Mapped[str] = mapped_column(
        ForeignKey(
            "lab_analytical_run_authorities.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    assessor_training_state: Mapped[str] = mapped_column(
        String(40), nullable=False
    )
    window_basis: Mapped[str] = mapped_column(String(40), nullable=False)
    window_start: Mapped[float] = mapped_column(Float, nullable=False)
    window_end: Mapped[float] = mapped_column(Float, nullable=False)
    detection_method: Mapped[str] = mapped_column(Text, nullable=False)
    replicate_index: Mapped[int] = mapped_column(Integer, nullable=False)
    replicate_count: Mapped[int] = mapped_column(Integer, nullable=False)
    detection_frequency: Mapped[float] = mapped_column(Float, nullable=False)
    repeatability_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    aligned_peak_ids_json: Mapped[list] = mapped_column(
        JSON,
        default=list,
        server_default=text("'[]'"),
        nullable=False,
    )
    unknown_event: Mapped[bool] = mapped_column(Boolean, nullable=False)
    exact_identity_claim: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabAnalyticalClaimAssessment(LabRecord):
    __tablename__ = "lab_analytical_claim_assessments"
    __table_args__ = (
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_analytical_claim_assessment_content_sha256",
        ),
        CheckConstraint(
            f"claim_type IN ({_quoted(ANALYTICAL_CLAIM_TYPES)})",
            name="ck_lab_analytical_claim_assessment_type",
        ),
        CheckConstraint(
            f"decision IN ({_quoted(ANALYTICAL_CLAIM_DECISIONS)})",
            name="ck_lab_analytical_claim_assessment_decision",
        ),
        CheckConstraint(
            "(decision = 'WITHHELD' AND result_json IS NULL) OR "
            "(decision != 'WITHHELD' AND result_json IS NOT NULL)",
            name="ck_lab_analytical_claim_assessment_withheld_result",
        ),
        CheckConstraint(
            "length(trim(reviewer_pseudonym)) > 0 "
            "AND reviewed_at IS NOT NULL",
            name="ck_lab_analytical_claim_assessment_review",
        ),
        CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_analytical_claim_assessment_content_sha256",
        ),
        Index(
            "ix_lab_analytical_claim_assessments_run_decision",
            "analytical_run_id",
            "decision",
        ),
    )

    analytical_run_id: Mapped[str] = mapped_column(
        ForeignKey("lab_analytical_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    run_authority_id: Mapped[str] = mapped_column(
        ForeignKey(
            "lab_analytical_run_authorities.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    peak_authority_id: Mapped[str] = mapped_column(
        ForeignKey(
            "lab_analytical_peak_authorities.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    claim_type: Mapped[str] = mapped_column(String(40), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(100), nullable=False)
    decision: Mapped[str] = mapped_column(String(40), nullable=False)
    scope_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    missing_requirements_json: Mapped[list] = mapped_column(
        JSON,
        default=list,
        server_default=text("'[]'"),
        nullable=False,
    )
    qualifications_json: Mapped[list] = mapped_column(
        JSON,
        default=list,
        server_default=text("'[]'"),
        nullable=False,
    )
    details_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    upstream_hashes_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    result_json: Mapped[dict | None] = mapped_column(
        JSON(none_as_null=True)
    )
    reviewer_pseudonym: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    reviewed_at: Mapped[datetime] = mapped_column(
        UTCDateTime(timezone=True), nullable=False
    )
    evidence_record_id: Mapped[str] = mapped_column(
        ForeignKey("lab_evidence_records.id", ondelete="RESTRICT"),
        nullable=False,
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


ANALYTICAL_AUTHORITY_TABLE_NAMES = {
    "lab_analytical_method_authorities",
    "lab_method_validation_records",
    "lab_analytical_sequences",
    "lab_analytical_sequence_entries",
    "lab_analytical_run_authorities",
    "lab_analytical_peak_authorities",
    "lab_gco_event_authorities",
    "lab_analytical_claim_assessments",
}


__all__ = [
    "ANALYTICAL_AUTHORITY_TABLE_NAMES",
    "ANALYTICAL_CLAIM_DECISIONS",
    "ANALYTICAL_CLAIM_TYPES",
    "ANALYTICAL_IDENTITY_AUTHORITY_STATES",
    "ANALYTICAL_METHOD_AUTHORITY_STATUSES",
    "ANALYTICAL_PRIMARY_SUBJECT_TYPES",
    "ANALYTICAL_QUANTITATION_STATES",
    "ANALYTICAL_RUN_DISPOSITIONS",
    "ANALYTICAL_SEQUENCE_ENTRY_ROLES",
    "ANALYTICAL_SEQUENCE_STATUSES",
    "ANALYTICAL_STANDARD_MATCH_STATES",
    "GCO_TRAINING_STATES",
    "GCO_WINDOW_BASES",
    "METHOD_VALIDATION_RESULTS",
    "LabAnalyticalClaimAssessment",
    "LabAnalyticalMethodAuthority",
    "LabAnalyticalPeakAuthority",
    "LabAnalyticalRunAuthority",
    "LabAnalyticalSequence",
    "LabAnalyticalSequenceEntry",
    "LabGCOEventAuthority",
    "LabMethodValidationRecord",
]
