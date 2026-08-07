"""Build B5 append-only analytical method, run, QC, and claim authority.

Revision ID: 20260731_0009
Revises: 20260731_0008
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260731_0009"
down_revision: str | None = "20260731_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

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
B5_TABLES = (
    "lab_analytical_method_authorities",
    "lab_method_validation_records",
    "lab_analytical_sequences",
    "lab_analytical_sequence_entries",
    "lab_analytical_run_authorities",
    "lab_analytical_peak_authorities",
    "lab_gco_event_authorities",
    "lab_analytical_claim_assessments",
)


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _record_columns() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def _json_object(name: str) -> sa.Column:
    return sa.Column(
        name,
        sa.JSON(),
        server_default=sa.text("'{}'"),
        nullable=False,
    )


def _json_array(name: str) -> sa.Column:
    return sa.Column(
        name,
        sa.JSON(),
        server_default=sa.text("'[]'"),
        nullable=False,
    )


def _create_append_only_triggers(table_name: str) -> None:
    if op.get_bind().dialect.name != "sqlite":
        return
    op.execute(
        f"""
        CREATE TRIGGER trg_{table_name}_no_update
        BEFORE UPDATE ON {table_name}
        BEGIN
            SELECT RAISE(ABORT, 'append-only table');
        END
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER trg_{table_name}_no_delete
        BEFORE DELETE ON {table_name}
        BEGIN
            SELECT RAISE(ABORT, 'append-only table');
        END
        """
    )


def _drop_append_only_triggers(table_name: str) -> None:
    if op.get_bind().dialect.name != "sqlite":
        return
    op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_no_delete")
    op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_no_update")


def upgrade() -> None:
    op.create_table(
        "lab_analytical_method_authorities",
        *_record_columns(),
        sa.Column("method_version_id", sa.String(length=36), nullable=False),
        sa.Column("schema_version", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        _json_array("analyte_scope_json"),
        _json_object("instrument_json"),
        _json_object("detector_json"),
        _json_object("software_json"),
        _json_object("separation_json"),
        _json_object("acquisition_json"),
        _json_object("sample_preparation_json"),
        sa.Column("hs_spme_json", sa.JSON()),
        _json_object("standards_json"),
        _json_object("calibration_json"),
        _json_object("response_factors_json"),
        _json_object("identity_criteria_json"),
        _json_object("integration_policy_json"),
        _json_object("qc_plan_json"),
        _json_object("raw_data_policy_json"),
        sa.Column(
            "source_document_version_id",
            sa.String(length=36),
            nullable=False,
        ),
        _json_object("source_locator_json"),
        sa.Column(
            "source_artifact_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "status IN "
            f"({_quoted(ANALYTICAL_METHOD_AUTHORITY_STATUSES)})",
            name="ck_lab_analytical_method_authority_status",
        ),
        sa.CheckConstraint(
            "length(source_artifact_sha256) = 64",
            name="ck_lab_analytical_method_authority_source_sha256",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_analytical_method_authority_content_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["method_version_id"],
            ["lab_analytical_method_versions.id"],
            ondelete="RESTRICT",
            name="fk_lab_analytical_method_authority_method_version",
        ),
        sa.ForeignKeyConstraint(
            ["source_document_version_id"],
            ["lab_source_document_versions.id"],
            ondelete="RESTRICT",
            name="fk_lab_analytical_method_authority_source_version",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "method_version_id",
            name="uq_lab_analytical_method_authority_version",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_analytical_method_authority_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_analytical_method_authorities_status",
        "lab_analytical_method_authorities",
        ["status"],
        unique=False,
    )

    op.create_table(
        "lab_method_validation_records",
        *_record_columns(),
        sa.Column(
            "method_authority_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column("intended_claim", sa.Text(), nullable=False),
        _json_object("matrix_scope_json"),
        sa.Column("scope_sha256", sa.String(length=64), nullable=False),
        _json_object("characteristics_json"),
        _json_object("acceptance_criteria_json"),
        sa.Column("result", sa.String(length=40), nullable=False),
        _json_array("limitations_json"),
        _json_object("measurement_uncertainty_json"),
        sa.Column(
            "reviewer_pseudonym",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "source_document_version_id",
            sa.String(length=36),
            nullable=False,
        ),
        _json_object("source_locator_json"),
        sa.Column(
            "source_artifact_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            f"result IN ({_quoted(METHOD_VALIDATION_RESULTS)})",
            name="ck_lab_method_validation_result",
        ),
        sa.CheckConstraint(
            "length(scope_sha256) = 64",
            name="ck_lab_method_validation_scope_sha256",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_method_validation_content_sha256",
        ),
        sa.CheckConstraint(
            "length(trim(reviewer_pseudonym)) > 0 "
            "AND reviewed_at IS NOT NULL",
            name="ck_lab_method_validation_review",
        ),
        sa.ForeignKeyConstraint(
            ["method_authority_id"],
            ["lab_analytical_method_authorities.id"],
            ondelete="RESTRICT",
            name="fk_lab_method_validation_method_authority",
        ),
        sa.ForeignKeyConstraint(
            ["source_document_version_id"],
            ["lab_source_document_versions.id"],
            ondelete="RESTRICT",
            name="fk_lab_method_validation_source_version",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "method_authority_id",
            "intended_claim",
            "scope_sha256",
            name="uq_lab_method_validation_scope",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_method_validation_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_method_validation_records_method_authority_id",
        "lab_method_validation_records",
        ["method_authority_id"],
        unique=False,
    )

    op.create_table(
        "lab_analytical_sequences",
        *_record_columns(),
        sa.Column("sequence_key", sa.String(length=255), nullable=False),
        sa.Column(
            "method_authority_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "instrument_identifier",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("entry_count", sa.Integer(), nullable=False),
        sa.Column("entries_sha256", sa.String(length=64), nullable=False),
        sa.Column("acquired_at", sa.DateTime(timezone=True)),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            f"status IN ({_quoted(ANALYTICAL_SEQUENCE_STATUSES)})",
            name="ck_lab_analytical_sequence_status",
        ),
        sa.CheckConstraint(
            "entry_count >= 1",
            name="ck_lab_analytical_sequence_entry_count",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64 AND length(entries_sha256) = 64",
            name="ck_lab_analytical_sequence_content_sha256",
        ),
        sa.CheckConstraint(
            "status != 'ACQUIRED' OR acquired_at IS NOT NULL",
            name="ck_lab_analytical_sequence_acquired_at",
        ),
        sa.ForeignKeyConstraint(
            ["method_authority_id"],
            ["lab_analytical_method_authorities.id"],
            ondelete="RESTRICT",
            name="fk_lab_analytical_sequence_method_authority",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "sequence_key",
            name="uq_lab_analytical_sequence_key",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_analytical_sequence_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_analytical_sequences_method_authority_id",
        "lab_analytical_sequences",
        ["method_authority_id"],
        unique=False,
    )

    op.create_table(
        "lab_analytical_sequence_entries",
        *_record_columns(),
        sa.Column("sequence_id", sa.String(length=36), nullable=False),
        sa.Column("injection_order", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column("reference", sa.Text(), nullable=False),
        _json_object("level_json"),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            f"role IN ({_quoted(ANALYTICAL_SEQUENCE_ENTRY_ROLES)})",
            name="ck_lab_analytical_sequence_entry_role",
        ),
        sa.CheckConstraint(
            "injection_order >= 1",
            name="ck_lab_analytical_sequence_entry_order",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_analytical_sequence_entry_content_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["sequence_id"],
            ["lab_analytical_sequences.id"],
            ondelete="RESTRICT",
            name="fk_lab_analytical_sequence_entry_sequence",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "sequence_id",
            "injection_order",
            name="uq_lab_analytical_sequence_entry_order",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_analytical_sequence_entry_content_sha256",
        ),
        sa.UniqueConstraint(
            "id",
            "sequence_id",
            name="uq_lab_analytical_sequence_entry_id_sequence",
        ),
    )
    op.create_index(
        "ix_lab_analytical_sequence_entries_sequence_id",
        "lab_analytical_sequence_entries",
        ["sequence_id"],
        unique=False,
    )

    op.create_table(
        "lab_analytical_run_authorities",
        *_record_columns(),
        sa.Column("analytical_run_id", sa.String(length=36), nullable=False),
        sa.Column(
            "method_authority_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column("sequence_id", sa.String(length=36), nullable=False),
        sa.Column("sequence_entry_id", sa.String(length=36), nullable=False),
        sa.Column("subject_type", sa.String(length=40), nullable=False),
        sa.Column("subject_id", sa.String(length=36), nullable=False),
        sa.Column("subject_stream_sequence", sa.Integer()),
        _json_object("matrix_scope_json"),
        _json_object("applicability_json"),
        _json_object("instrument_state_json"),
        _json_object("processing_details_json"),
        _json_object("deviation_assessment_json"),
        sa.Column(
            "reviewer_pseudonym",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("disposition", sa.String(length=40), nullable=False),
        sa.Column(
            "raw_vendor_attachment_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "open_export_attachment_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "subject_type IN "
            f"({_quoted(ANALYTICAL_PRIMARY_SUBJECT_TYPES)})",
            name="ck_lab_analytical_run_authority_subject_type",
        ),
        sa.CheckConstraint(
            "(subject_type = 'BOTTLE_STREAM' "
            "AND subject_stream_sequence IS NOT NULL "
            "AND subject_stream_sequence >= 1) OR "
            "(subject_type != 'BOTTLE_STREAM' "
            "AND subject_stream_sequence IS NULL)",
            name="ck_lab_analytical_run_authority_subject_shape",
        ),
        sa.CheckConstraint(
            f"disposition IN ({_quoted(ANALYTICAL_RUN_DISPOSITIONS)})",
            name="ck_lab_analytical_run_authority_disposition",
        ),
        sa.CheckConstraint(
            "raw_vendor_attachment_id != open_export_attachment_id",
            name="ck_lab_analytical_run_authority_raw_distinct",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_analytical_run_authority_content_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["analytical_run_id"],
            ["lab_analytical_runs.id"],
            ondelete="RESTRICT",
            name="fk_lab_analytical_run_authority_run",
        ),
        sa.ForeignKeyConstraint(
            ["method_authority_id"],
            ["lab_analytical_method_authorities.id"],
            ondelete="RESTRICT",
            name="fk_lab_analytical_run_authority_method",
        ),
        sa.ForeignKeyConstraint(
            ["sequence_entry_id", "sequence_id"],
            [
                "lab_analytical_sequence_entries.id",
                "lab_analytical_sequence_entries.sequence_id",
            ],
            ondelete="RESTRICT",
            name="fk_lab_analytical_run_authority_sequence_entry",
        ),
        sa.ForeignKeyConstraint(
            ["raw_vendor_attachment_id"],
            ["lab_analytical_attachments.id"],
            ondelete="RESTRICT",
            name="fk_lab_analytical_run_authority_vendor_attachment",
        ),
        sa.ForeignKeyConstraint(
            ["open_export_attachment_id"],
            ["lab_analytical_attachments.id"],
            ondelete="RESTRICT",
            name="fk_lab_analytical_run_authority_open_attachment",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analytical_run_id",
            name="uq_lab_analytical_run_authority_run",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_analytical_run_authority_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_analytical_run_authorities_sequence_id",
        "lab_analytical_run_authorities",
        ["sequence_id"],
        unique=False,
    )
    op.create_index(
        "ix_lab_analytical_run_authorities_subject",
        "lab_analytical_run_authorities",
        ["subject_type", "subject_id"],
        unique=False,
    )

    op.create_table(
        "lab_analytical_peak_authorities",
        *_record_columns(),
        sa.Column("analytical_peak_id", sa.String(length=36), nullable=False),
        sa.Column(
            "analytical_run_authority_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column("identity_state", sa.String(length=60), nullable=False),
        sa.Column("identity_label", sa.Text()),
        sa.Column("stationary_phase", sa.Text(), nullable=False),
        _json_object("spectrum_json"),
        _json_object("deconvolution_json"),
        _json_array("library_candidates_json"),
        _json_object("exact_mass_json"),
        sa.Column(
            "authentic_standard_state",
            sa.String(length=40),
            nullable=False,
        ),
        sa.Column(
            "co_injection_state",
            sa.String(length=40),
            nullable=False,
        ),
        _json_array("quantifier_ions_json"),
        _json_object("coelution_json"),
        _json_object("manual_review_json"),
        _json_object("identity_decision_json"),
        sa.Column(
            "quantitation_state",
            sa.String(length=40),
            nullable=False,
        ),
        _json_object("quantitation_json"),
        _json_object("applicability_json"),
        sa.Column(
            "reviewer_pseudonym",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "identity_state IN "
            f"({_quoted(ANALYTICAL_IDENTITY_AUTHORITY_STATES)})",
            name="ck_lab_analytical_peak_authority_identity_state",
        ),
        sa.CheckConstraint(
            "authentic_standard_state IN "
            f"({_quoted(ANALYTICAL_STANDARD_MATCH_STATES)}) "
            "AND co_injection_state IN "
            f"({_quoted(ANALYTICAL_STANDARD_MATCH_STATES)})",
            name="ck_lab_analytical_peak_authority_standard_states",
        ),
        sa.CheckConstraint(
            "quantitation_state IN "
            f"({_quoted(ANALYTICAL_QUANTITATION_STATES)})",
            name="ck_lab_analytical_peak_authority_quantitation_state",
        ),
        sa.CheckConstraint(
            "identity_state != 'CONFIRMED_AUTHENTIC_STANDARD' "
            "OR authentic_standard_state = 'MATCHED' "
            "OR co_injection_state = 'MATCHED'",
            name="ck_lab_analytical_peak_authority_confirmed_standard",
        ),
        sa.CheckConstraint(
            "identity_state IN ('UNRESOLVED', 'REJECTED') "
            "OR identity_label IS NOT NULL",
            name="ck_lab_analytical_peak_authority_identity_label",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_analytical_peak_authority_content_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["analytical_peak_id"],
            ["lab_analytical_peaks.id"],
            ondelete="RESTRICT",
            name="fk_lab_analytical_peak_authority_peak",
        ),
        sa.ForeignKeyConstraint(
            ["analytical_run_authority_id"],
            ["lab_analytical_run_authorities.id"],
            ondelete="RESTRICT",
            name="fk_lab_analytical_peak_authority_run_authority",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analytical_peak_id",
            name="uq_lab_analytical_peak_authority_peak",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_analytical_peak_authority_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_analytical_peak_authorities_identity_state",
        "lab_analytical_peak_authorities",
        ["identity_state"],
        unique=False,
    )

    op.create_table(
        "lab_gco_event_authorities",
        *_record_columns(),
        sa.Column("gco_event_id", sa.String(length=36), nullable=False),
        sa.Column(
            "analytical_run_authority_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "assessor_training_state",
            sa.String(length=40),
            nullable=False,
        ),
        sa.Column("window_basis", sa.String(length=40), nullable=False),
        sa.Column("window_start", sa.Float(), nullable=False),
        sa.Column("window_end", sa.Float(), nullable=False),
        sa.Column("detection_method", sa.Text(), nullable=False),
        sa.Column("replicate_index", sa.Integer(), nullable=False),
        sa.Column("replicate_count", sa.Integer(), nullable=False),
        sa.Column("detection_frequency", sa.Float(), nullable=False),
        _json_object("repeatability_json"),
        _json_array("aligned_peak_ids_json"),
        sa.Column("unknown_event", sa.Boolean(), nullable=False),
        sa.Column(
            "exact_identity_claim",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "assessor_training_state IN "
            f"({_quoted(GCO_TRAINING_STATES)})",
            name="ck_lab_gco_event_authority_training_state",
        ),
        sa.CheckConstraint(
            f"window_basis IN ({_quoted(GCO_WINDOW_BASES)})",
            name="ck_lab_gco_event_authority_window_basis",
        ),
        sa.CheckConstraint(
            "window_start >= 0 AND window_end >= window_start",
            name="ck_lab_gco_event_authority_window",
        ),
        sa.CheckConstraint(
            "replicate_index >= 1 AND replicate_count >= replicate_index",
            name="ck_lab_gco_event_authority_replicates",
        ),
        sa.CheckConstraint(
            "detection_frequency >= 0 AND detection_frequency <= 1",
            name="ck_lab_gco_event_authority_frequency",
        ),
        sa.CheckConstraint(
            "exact_identity_claim = false",
            name="ck_lab_gco_event_authority_no_exact_identity",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_gco_event_authority_content_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["gco_event_id"],
            ["lab_gco_events.id"],
            ondelete="RESTRICT",
            name="fk_lab_gco_event_authority_event",
        ),
        sa.ForeignKeyConstraint(
            ["analytical_run_authority_id"],
            ["lab_analytical_run_authorities.id"],
            ondelete="RESTRICT",
            name="fk_lab_gco_event_authority_run_authority",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "gco_event_id",
            name="uq_lab_gco_event_authority_event",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_gco_event_authority_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_gco_event_authorities_training_state",
        "lab_gco_event_authorities",
        ["assessor_training_state"],
        unique=False,
    )

    op.create_table(
        "lab_analytical_claim_assessments",
        *_record_columns(),
        sa.Column("analytical_run_id", sa.String(length=36), nullable=False),
        sa.Column("run_authority_id", sa.String(length=36), nullable=False),
        sa.Column("peak_authority_id", sa.String(length=36), nullable=False),
        sa.Column("claim_type", sa.String(length=40), nullable=False),
        sa.Column("policy_version", sa.String(length=100), nullable=False),
        sa.Column("decision", sa.String(length=40), nullable=False),
        _json_object("scope_json"),
        _json_array("missing_requirements_json"),
        _json_array("qualifications_json"),
        _json_object("details_json"),
        _json_object("upstream_hashes_json"),
        sa.Column("result_json", sa.JSON(none_as_null=True)),
        sa.Column(
            "reviewer_pseudonym",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("evidence_record_id", sa.String(length=36), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            f"claim_type IN ({_quoted(ANALYTICAL_CLAIM_TYPES)})",
            name="ck_lab_analytical_claim_assessment_type",
        ),
        sa.CheckConstraint(
            f"decision IN ({_quoted(ANALYTICAL_CLAIM_DECISIONS)})",
            name="ck_lab_analytical_claim_assessment_decision",
        ),
        sa.CheckConstraint(
            "(decision = 'WITHHELD' AND result_json IS NULL) OR "
            "(decision != 'WITHHELD' AND result_json IS NOT NULL)",
            name="ck_lab_analytical_claim_assessment_withheld_result",
        ),
        sa.CheckConstraint(
            "length(trim(reviewer_pseudonym)) > 0 "
            "AND reviewed_at IS NOT NULL",
            name="ck_lab_analytical_claim_assessment_review",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_analytical_claim_assessment_content_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["analytical_run_id"],
            ["lab_analytical_runs.id"],
            ondelete="RESTRICT",
            name="fk_lab_analytical_claim_assessment_run",
        ),
        sa.ForeignKeyConstraint(
            ["run_authority_id"],
            ["lab_analytical_run_authorities.id"],
            ondelete="RESTRICT",
            name="fk_lab_analytical_claim_assessment_run_authority",
        ),
        sa.ForeignKeyConstraint(
            ["peak_authority_id"],
            ["lab_analytical_peak_authorities.id"],
            ondelete="RESTRICT",
            name="fk_lab_analytical_claim_assessment_peak_authority",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_record_id"],
            ["lab_evidence_records.id"],
            ondelete="RESTRICT",
            name="fk_lab_analytical_claim_assessment_evidence",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_analytical_claim_assessment_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_analytical_claim_assessments_run_decision",
        "lab_analytical_claim_assessments",
        ["analytical_run_id", "decision"],
        unique=False,
    )

    for table_name in B5_TABLES:
        _create_append_only_triggers(table_name)


def downgrade() -> None:
    for table_name in reversed(B5_TABLES):
        _drop_append_only_triggers(table_name)

    op.drop_index(
        "ix_lab_analytical_claim_assessments_run_decision",
        table_name="lab_analytical_claim_assessments",
    )
    op.drop_table("lab_analytical_claim_assessments")

    op.drop_index(
        "ix_lab_gco_event_authorities_training_state",
        table_name="lab_gco_event_authorities",
    )
    op.drop_table("lab_gco_event_authorities")

    op.drop_index(
        "ix_lab_analytical_peak_authorities_identity_state",
        table_name="lab_analytical_peak_authorities",
    )
    op.drop_table("lab_analytical_peak_authorities")

    op.drop_index(
        "ix_lab_analytical_run_authorities_subject",
        table_name="lab_analytical_run_authorities",
    )
    op.drop_index(
        "ix_lab_analytical_run_authorities_sequence_id",
        table_name="lab_analytical_run_authorities",
    )
    op.drop_table("lab_analytical_run_authorities")

    op.drop_index(
        "ix_lab_analytical_sequence_entries_sequence_id",
        table_name="lab_analytical_sequence_entries",
    )
    op.drop_table("lab_analytical_sequence_entries")

    op.drop_index(
        "ix_lab_analytical_sequences_method_authority_id",
        table_name="lab_analytical_sequences",
    )
    op.drop_table("lab_analytical_sequences")

    op.drop_index(
        "ix_lab_method_validation_records_method_authority_id",
        table_name="lab_method_validation_records",
    )
    op.drop_table("lab_method_validation_records")

    op.drop_index(
        "ix_lab_analytical_method_authorities_status",
        table_name="lab_analytical_method_authorities",
    )
    op.drop_table("lab_analytical_method_authorities")
