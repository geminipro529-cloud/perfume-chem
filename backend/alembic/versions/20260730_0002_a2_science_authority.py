"""Add immutable A2 analytical, regulatory, and claim authority records."""

import sqlalchemy as sa

from alembic import op

revision = "20260730_0002"
down_revision = "20260730_0001"
branch_labels = None
depends_on = None

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
SCIENCE_AUTHORITY_TABLES = (
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
)


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _record_columns() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def _create_append_only_triggers(table_name: str) -> None:
    for operation in ("UPDATE", "DELETE"):
        trigger_name = f"trg_{table_name}_{operation.lower()}_append_only"
        op.execute(
            f"""
            CREATE TRIGGER {trigger_name}
            BEFORE {operation} ON {table_name}
            BEGIN
                SELECT RAISE(ABORT, 'append-only: {table_name}');
            END
            """
        )


def _drop_append_only_triggers(table_name: str) -> None:
    for operation in ("UPDATE", "DELETE"):
        trigger_name = f"trg_{table_name}_{operation.lower()}_append_only"
        op.execute(f"DROP TRIGGER {trigger_name}")


def upgrade() -> None:
    op.create_table(
        "lab_analytical_method_versions",
        *_record_columns(),
        sa.Column("method_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.String(length=80), nullable=False),
        sa.Column("technique", sa.String(length=40), nullable=False),
        sa.Column("intended_use", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column(
            "method_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("evidence_record_id", sa.String(length=36), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("parent_version_id", sa.String(length=36), nullable=True),
        sa.Column("parent_sha256", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "version_number >= 1",
            name="ck_lab_analytical_method_version_positive",
        ),
        sa.CheckConstraint(
            f"technique IN ({_quoted(ANALYTICAL_TECHNIQUES)})",
            name="ck_lab_analytical_method_technique",
        ),
        sa.CheckConstraint(
            f"status IN ({_quoted(ANALYTICAL_METHOD_STATUSES)})",
            name="ck_lab_analytical_method_status",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_record_id"],
            ["lab_evidence_records.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parent_version_id"],
            ["lab_analytical_method_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "method_id",
            "version_number",
            name="uq_lab_analytical_method_version",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_analytical_method_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_analytical_method_versions_method_id",
        "lab_analytical_method_versions",
        ["method_id"],
        unique=False,
    )

    op.create_table(
        "lab_analytical_runs",
        *_record_columns(),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("method_version_id", sa.String(length=36), nullable=False),
        sa.Column("run_kind", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("instrument_identifier", sa.String(length=255), nullable=False),
        sa.Column(
            "acquired_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "parameters_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "deviations_json",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("processing_version", sa.String(length=100), nullable=False),
        sa.Column("experiment_id", sa.String(length=36), nullable=True),
        sa.Column("sample_id", sa.String(length=36), nullable=True),
        sa.Column("bottle_id", sa.String(length=36), nullable=True),
        sa.Column("formula_version_id", sa.String(length=36), nullable=True),
        sa.Column("build_plan_version_id", sa.String(length=36), nullable=True),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            f"run_kind IN ({_quoted(ANALYTICAL_TECHNIQUES)})",
            name="ck_lab_analytical_run_kind",
        ),
        sa.CheckConstraint(
            f"status IN ({_quoted(ANALYTICAL_RUN_STATUSES)})",
            name="ck_lab_analytical_run_status",
        ),
        sa.CheckConstraint(
            "experiment_id IS NOT NULL OR sample_id IS NOT NULL "
            "OR bottle_id IS NOT NULL OR formula_version_id IS NOT NULL "
            "OR build_plan_version_id IS NOT NULL",
            name="ck_lab_analytical_run_subject",
        ),
        sa.ForeignKeyConstraint(
            ["method_version_id"],
            ["lab_analytical_method_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["experiment_id"],
            ["lab_experiments.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["sample_id"],
            ["lab_samples.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["bottle_id"],
            ["lab_bottles.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["formula_version_id"],
            ["lab_formula_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["build_plan_version_id"],
            ["lab_build_plan_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", name="uq_lab_analytical_run_identity"),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_analytical_run_content_sha256",
        ),
    )

    op.create_table(
        "lab_analytical_peaks",
        *_record_columns(),
        sa.Column("analytical_run_id", sa.String(length=36), nullable=False),
        sa.Column("peak_key", sa.String(length=100), nullable=False),
        sa.Column("retention_time_minutes", sa.Float(), nullable=True),
        sa.Column("retention_index", sa.Float(), nullable=True),
        sa.Column("area", sa.Float(), nullable=True),
        sa.Column("response_factor", sa.Float(), nullable=True),
        sa.Column(
            "qualifier_ions_json",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("tentative_identity", sa.String(length=255), nullable=True),
        sa.Column("material_id", sa.String(length=36), nullable=True),
        sa.Column("identity_state", sa.String(length=40), nullable=False),
        sa.Column("match_score", sa.Float(), nullable=True),
        sa.Column("quantitation_basis", sa.String(length=100), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=True),
        sa.Column("quantity_unit", sa.String(length=40), nullable=True),
        sa.Column("standard_uncertainty", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "(retention_time_minutes IS NULL OR retention_time_minutes >= 0) "
            "AND (retention_index IS NULL OR retention_index >= 0) "
            "AND (area IS NULL OR area >= 0) "
            "AND (response_factor IS NULL OR response_factor >= 0) "
            "AND (quantity IS NULL OR quantity >= 0) "
            "AND (standard_uncertainty IS NULL OR standard_uncertainty >= 0)",
            name="ck_lab_analytical_peak_nonnegative",
        ),
        sa.CheckConstraint(
            "match_score IS NULL OR (match_score >= 0 AND match_score <= 1)",
            name="ck_lab_analytical_peak_match_score",
        ),
        sa.CheckConstraint(
            f"identity_state IN ({_quoted(ANALYTICAL_IDENTITY_STATES)})",
            name="ck_lab_analytical_peak_identity_state",
        ),
        sa.CheckConstraint(
            "identity_state != 'CONFIRMED' OR material_id IS NOT NULL",
            name="ck_lab_analytical_peak_confirmed_material",
        ),
        sa.CheckConstraint(
            "(quantity IS NULL AND quantity_unit IS NULL "
            "AND quantitation_basis IS NULL) "
            "OR (quantity IS NOT NULL AND quantity_unit IS NOT NULL "
            "AND quantitation_basis IS NOT NULL)",
            name="ck_lab_analytical_peak_quantity_basis",
        ),
        sa.ForeignKeyConstraint(
            ["analytical_run_id"],
            ["lab_analytical_runs.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["material_id"],
            ["lab_materials.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analytical_run_id",
            "peak_key",
            name="uq_lab_analytical_peak_identity",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_analytical_peak_content_sha256",
        ),
        sa.UniqueConstraint(
            "id",
            "analytical_run_id",
            name="uq_lab_analytical_peak_id_run",
        ),
    )

    op.create_table(
        "lab_analytical_qc_records",
        *_record_columns(),
        sa.Column("analytical_run_id", sa.String(length=36), nullable=False),
        sa.Column("qc_key", sa.String(length=100), nullable=False),
        sa.Column("qc_type", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column(
            "criteria_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "observed_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("evidence_record_id", sa.String(length=36), nullable=True),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            f"status IN ({_quoted(ANALYTICAL_QC_STATUSES)})",
            name="ck_lab_analytical_qc_status",
        ),
        sa.ForeignKeyConstraint(
            ["analytical_run_id"],
            ["lab_analytical_runs.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_record_id"],
            ["lab_evidence_records.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analytical_run_id",
            "qc_key",
            name="uq_lab_analytical_qc_identity",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_analytical_qc_content_sha256",
        ),
    )

    op.create_table(
        "lab_analytical_attachments",
        *_record_columns(),
        sa.Column("analytical_run_id", sa.String(length=36), nullable=False),
        sa.Column("attachment_kind", sa.String(length=100), nullable=False),
        sa.Column("media_type", sa.String(length=255), nullable=False),
        sa.Column("byte_length", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_locator", sa.Text(), nullable=False),
        sa.Column("evidence_record_id", sa.String(length=36), nullable=True),
        sa.CheckConstraint(
            "byte_length >= 0",
            name="ck_lab_analytical_attachment_length",
        ),
        sa.ForeignKeyConstraint(
            ["analytical_run_id"],
            ["lab_analytical_runs.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_record_id"],
            ["lab_evidence_records.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analytical_run_id",
            "attachment_kind",
            "content_sha256",
            name="uq_lab_analytical_attachment",
        ),
    )

    op.create_table(
        "lab_gco_events",
        *_record_columns(),
        sa.Column("analytical_run_id", sa.String(length=36), nullable=False),
        sa.Column("analytical_peak_id", sa.String(length=36), nullable=True),
        sa.Column("event_key", sa.String(length=100), nullable=False),
        sa.Column("retention_time_minutes", sa.Float(), nullable=True),
        sa.Column("retention_index", sa.Float(), nullable=True),
        sa.Column("descriptor", sa.Text(), nullable=False),
        sa.Column("intensity", sa.Float(), nullable=True),
        sa.Column("assessor_pseudonym", sa.String(length=255), nullable=False),
        sa.Column(
            "repeatability_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("evidence_record_id", sa.String(length=36), nullable=True),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "(retention_time_minutes IS NULL OR retention_time_minutes >= 0) "
            "AND (retention_index IS NULL OR retention_index >= 0)",
            name="ck_lab_gco_event_position",
        ),
        sa.CheckConstraint(
            "intensity IS NULL OR (intensity >= 0 AND intensity <= 1)",
            name="ck_lab_gco_event_intensity",
        ),
        sa.ForeignKeyConstraint(
            ["analytical_run_id"],
            ["lab_analytical_runs.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["analytical_peak_id", "analytical_run_id"],
            ["lab_analytical_peaks.id", "lab_analytical_peaks.analytical_run_id"],
            name="fk_lab_gco_peak_run",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_record_id"],
            ["lab_evidence_records.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analytical_run_id",
            "event_key",
            name="uq_lab_gco_event_identity",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_gco_event_content_sha256",
        ),
    )

    op.create_table(
        "lab_regulatory_assessment_versions",
        *_record_columns(),
        sa.Column("assessment_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.String(length=80), nullable=False),
        sa.Column("subject_type", sa.String(length=40), nullable=False),
        sa.Column("subject_id", sa.String(length=36), nullable=False),
        sa.Column("parent_version_id", sa.String(length=36), nullable=True),
        sa.Column("standard_identifier", sa.String(length=255), nullable=False),
        sa.Column("standard_amendment", sa.String(length=100), nullable=True),
        sa.Column("standard_state", sa.String(length=40), nullable=False),
        sa.Column(
            "source_evidence_record_id",
            sa.String(length=36),
            nullable=True,
        ),
        sa.Column("jurisdiction", sa.String(length=100), nullable=False),
        sa.Column("product_category", sa.String(length=255), nullable=False),
        sa.Column("concentration_basis", sa.String(length=100), nullable=False),
        sa.Column("finished_product_concentration", sa.Float(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("result_state", sa.String(length=40), nullable=False),
        sa.Column(
            "assumptions_json",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column(
            "unresolved_json",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("permitted_wording", sa.Text(), nullable=True),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("parent_sha256", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "version_number >= 1",
            name="ck_lab_regulatory_assessment_version_positive",
        ),
        sa.CheckConstraint(
            f"subject_type IN ({_quoted(REGULATORY_SUBJECT_TYPES)})",
            name="ck_lab_regulatory_assessment_subject_type",
        ),
        sa.CheckConstraint(
            f"standard_state IN ({_quoted(REGULATORY_STANDARD_STATES)})",
            name="ck_lab_regulatory_assessment_standard_state",
        ),
        sa.CheckConstraint(
            f"result_state IN ({_quoted(ASSESSMENT_RESULT_STATES)})",
            name="ck_lab_regulatory_assessment_result_state",
        ),
        sa.CheckConstraint(
            "finished_product_concentration IS NULL "
            "OR finished_product_concentration >= 0",
            name="ck_lab_regulatory_assessment_concentration",
        ),
        sa.ForeignKeyConstraint(
            ["parent_version_id"],
            ["lab_regulatory_assessment_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_evidence_record_id"],
            ["lab_evidence_records.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assessment_id",
            "version_number",
            name="uq_lab_regulatory_assessment_version",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_regulatory_assessment_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_regulatory_assessment_versions_assessment_id",
        "lab_regulatory_assessment_versions",
        ["assessment_id"],
        unique=False,
    )
    op.create_index(
        "ix_lab_regulatory_assessment_versions_subject_id",
        "lab_regulatory_assessment_versions",
        ["subject_id"],
        unique=False,
    )

    op.create_table(
        "lab_regulatory_findings",
        *_record_columns(),
        sa.Column(
            "regulatory_assessment_version_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column("finding_key", sa.String(length=100), nullable=False),
        sa.Column("restriction_id", sa.String(length=36), nullable=True),
        sa.Column("material_id", sa.String(length=36), nullable=True),
        sa.Column("substance_identity", sa.String(length=255), nullable=False),
        sa.Column("observed_fraction", sa.Float(), nullable=True),
        sa.Column("maximum_fraction", sa.Float(), nullable=True),
        sa.Column("concentration_basis", sa.String(length=100), nullable=True),
        sa.Column("result_state", sa.String(length=40), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("evidence_record_id", sa.String(length=36), nullable=True),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "(observed_fraction IS NULL OR observed_fraction >= 0) "
            "AND (maximum_fraction IS NULL OR maximum_fraction >= 0)",
            name="ck_lab_regulatory_finding_fractions",
        ),
        sa.CheckConstraint(
            f"result_state IN ({_quoted(ASSESSMENT_RESULT_STATES)})",
            name="ck_lab_regulatory_finding_result_state",
        ),
        sa.CheckConstraint(
            "result_state != 'PASS' OR "
            "(observed_fraction IS NOT NULL AND maximum_fraction IS NOT NULL "
            "AND concentration_basis IS NOT NULL)",
            name="ck_lab_regulatory_finding_pass_basis",
        ),
        sa.ForeignKeyConstraint(
            ["regulatory_assessment_version_id"],
            ["lab_regulatory_assessment_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["restriction_id"],
            ["lab_restrictions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["material_id"],
            ["lab_materials.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_record_id"],
            ["lab_evidence_records.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "regulatory_assessment_version_id",
            "finding_key",
            name="uq_lab_regulatory_finding_identity",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_regulatory_finding_content_sha256",
        ),
    )

    op.create_table(
        "lab_claim_assessment_versions",
        *_record_columns(),
        sa.Column("claim_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.String(length=80), nullable=False),
        sa.Column("claim_type", sa.String(length=100), nullable=False),
        sa.Column("subject_type", sa.String(length=40), nullable=False),
        sa.Column("subject_id", sa.String(length=36), nullable=False),
        sa.Column("parent_version_id", sa.String(length=36), nullable=True),
        sa.Column("policy_version", sa.String(length=100), nullable=False),
        sa.Column("decision", sa.String(length=40), nullable=False),
        sa.Column(
            "authority_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "missing_evidence_json",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column(
            "conflicts_json",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("permitted_wording", sa.Text(), nullable=True),
        sa.Column("forbidden_wording", sa.Text(), nullable=True),
        sa.Column("human_review_state", sa.String(length=40), nullable=False),
        sa.Column("reviewer_pseudonym", sa.String(length=255), nullable=True),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("parent_sha256", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "version_number >= 1",
            name="ck_lab_claim_assessment_version_positive",
        ),
        sa.CheckConstraint(
            f"subject_type IN ({_quoted(CLAIM_SUBJECT_TYPES)})",
            name="ck_lab_claim_assessment_subject_type",
        ),
        sa.CheckConstraint(
            f"decision IN ({_quoted(CLAIM_DECISIONS)})",
            name="ck_lab_claim_assessment_decision",
        ),
        sa.CheckConstraint(
            f"human_review_state IN ({_quoted(CLAIM_REVIEW_STATES)})",
            name="ck_lab_claim_assessment_review_state",
        ),
        sa.ForeignKeyConstraint(
            ["parent_version_id"],
            ["lab_claim_assessment_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "claim_id",
            "version_number",
            name="uq_lab_claim_assessment_version",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_claim_assessment_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_claim_assessment_versions_claim_id",
        "lab_claim_assessment_versions",
        ["claim_id"],
        unique=False,
    )
    op.create_index(
        "ix_lab_claim_assessment_versions_subject_id",
        "lab_claim_assessment_versions",
        ["subject_id"],
        unique=False,
    )

    op.create_table(
        "lab_claim_assessment_evidence_links",
        *_record_columns(),
        sa.Column(
            "claim_assessment_version_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column("evidence_record_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.CheckConstraint(
            f"role IN ({_quoted(CLAIM_EVIDENCE_ROLES)})",
            name="ck_lab_claim_evidence_role",
        ),
        sa.ForeignKeyConstraint(
            ["claim_assessment_version_id"],
            ["lab_claim_assessment_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_record_id"],
            ["lab_evidence_records.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "claim_assessment_version_id",
            "evidence_record_id",
            "role",
            name="uq_lab_claim_assessment_evidence_link",
        ),
    )

    for table_name in SCIENCE_AUTHORITY_TABLES:
        _create_append_only_triggers(table_name)


def downgrade() -> None:
    for table_name in reversed(SCIENCE_AUTHORITY_TABLES):
        _drop_append_only_triggers(table_name)

    op.drop_table("lab_claim_assessment_evidence_links")
    op.drop_index(
        "ix_lab_claim_assessment_versions_subject_id",
        table_name="lab_claim_assessment_versions",
    )
    op.drop_index(
        "ix_lab_claim_assessment_versions_claim_id",
        table_name="lab_claim_assessment_versions",
    )
    op.drop_table("lab_claim_assessment_versions")
    op.drop_table("lab_regulatory_findings")
    op.drop_index(
        "ix_lab_regulatory_assessment_versions_subject_id",
        table_name="lab_regulatory_assessment_versions",
    )
    op.drop_index(
        "ix_lab_regulatory_assessment_versions_assessment_id",
        table_name="lab_regulatory_assessment_versions",
    )
    op.drop_table("lab_regulatory_assessment_versions")
    op.drop_table("lab_gco_events")
    op.drop_table("lab_analytical_attachments")
    op.drop_table("lab_analytical_qc_records")
    op.drop_table("lab_analytical_peaks")
    op.drop_table("lab_analytical_runs")
    op.drop_index(
        "ix_lab_analytical_method_versions_method_id",
        table_name="lab_analytical_method_versions",
    )
    op.drop_table("lab_analytical_method_versions")
