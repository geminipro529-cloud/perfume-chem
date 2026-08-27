"""Build B3 contextual thresholds, OAV assessments, and legacy quarantine.

Revision ID: 20260730_0007
Revises: 20260730_0006
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260730_0007"
down_revision: str | None = "20260730_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

THRESHOLD_ENDPOINTS = (
    "DETECTION",
    "RECOGNITION",
    "DIFFERENCE",
    "REJECTION",
    "OTHER",
)
THRESHOLD_ROUTES = ("ORTHONASAL", "RETRONASAL", "OTHER")
THRESHOLD_MATRIX_STATES = ("SPECIFIED", "UNSPECIFIED")
THRESHOLD_TRAINING_STATES = (
    "TRAINED",
    "UNTRAINED",
    "MIXED",
    "NOT_REPORTED",
)
THRESHOLD_CONCENTRATION_BASES = (
    "MOLE_FRACTION",
    "MASS_FRACTION",
    "VOLUME_FRACTION",
    "MASS_CONCENTRATION",
    "AMOUNT_CONCENTRATION",
    "OTHER_DECLARED",
)
OAV_ASSESSMENT_STATUSES = ("COMPUTED", "WITHHELD")
LEGACY_THRESHOLD_AUTHORITY = "LEGACY_CONTEXT_INCOMPLETE"
B3_TABLES = (
    "lab_threshold_observation_contexts",
    "lab_oav_assessments",
    "lab_legacy_threshold_records",
)


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _record_columns() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
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
        "lab_threshold_observation_contexts",
        *_record_columns(),
        sa.Column(
            "observation_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "schema_version",
            sa.String(length=80),
            nullable=False,
        ),
        sa.Column("endpoint", sa.String(length=40), nullable=False),
        sa.Column("route", sa.String(length=40), nullable=False),
        sa.Column("medium", sa.Text(), nullable=False),
        sa.Column(
            "matrix_specification_state",
            sa.String(length=40),
            nullable=False,
        ),
        sa.Column("matrix_composition_json", sa.JSON(), nullable=False),
        sa.Column(
            "concentration_basis",
            sa.String(length=60),
            nullable=False,
        ),
        sa.Column("apparatus_json", sa.JSON(), nullable=False),
        sa.Column("population_json", sa.JSON(), nullable=False),
        sa.Column(
            "training_state",
            sa.String(length=40),
            nullable=False,
        ),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column(
            "psychophysical_procedure",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "content_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"endpoint IN ({_quoted(THRESHOLD_ENDPOINTS)})",
            name="ck_lab_threshold_context_endpoint",
        ),
        sa.CheckConstraint(
            f"route IN ({_quoted(THRESHOLD_ROUTES)})",
            name="ck_lab_threshold_context_route",
        ),
        sa.CheckConstraint(
            f"matrix_specification_state IN ({_quoted(THRESHOLD_MATRIX_STATES)})",
            name="ck_lab_threshold_context_matrix_state",
        ),
        sa.CheckConstraint(
            f"concentration_basis IN ({_quoted(THRESHOLD_CONCENTRATION_BASES)})",
            name="ck_lab_threshold_context_basis",
        ),
        sa.CheckConstraint(
            f"training_state IN ({_quoted(THRESHOLD_TRAINING_STATES)})",
            name="ck_lab_threshold_context_training",
        ),
        sa.CheckConstraint(
            "sample_size >= 1",
            name="ck_lab_threshold_context_sample_size",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_threshold_context_content_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["lab_property_observations.id"],
            ondelete="RESTRICT",
            name="fk_lab_threshold_context_observation",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "observation_id",
            name="uq_lab_threshold_context_observation",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_threshold_context_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_threshold_observation_contexts_observation_id",
        "lab_threshold_observation_contexts",
        ["observation_id"],
        unique=True,
    )

    op.create_table(
        "lab_oav_assessments",
        *_record_columns(),
        sa.Column(
            "schema_version",
            sa.String(length=80),
            nullable=False,
        ),
        sa.Column(
            "concentration_observation_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "threshold_assertion_id",
            sa.String(length=36),
        ),
        sa.Column(
            "requested_endpoint",
            sa.String(length=40),
            nullable=False,
        ),
        sa.Column(
            "requested_route",
            sa.String(length=40),
            nullable=False,
        ),
        sa.Column(
            "strict_science_mode",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("oav_value", sa.Float()),
        sa.Column("mismatch_count", sa.Integer(), nullable=False),
        sa.Column("mismatch_codes_json", sa.JSON(), nullable=False),
        sa.Column(
            "conversion_prerequisites_json",
            sa.JSON(),
            nullable=False,
        ),
        sa.Column("input_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("permitted_uses_json", sa.JSON(), nullable=False),
        sa.Column("prohibited_claims_json", sa.JSON(), nullable=False),
        sa.Column(
            "content_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"status IN ({_quoted(OAV_ASSESSMENT_STATUSES)})",
            name="ck_lab_oav_assessment_status",
        ),
        sa.CheckConstraint(
            "("
            "(status = 'COMPUTED' AND oav_value IS NOT NULL "
            "AND oav_value >= 0 AND mismatch_count = 0) OR "
            "(status = 'WITHHELD' AND oav_value IS NULL "
            "AND mismatch_count >= 1)"
            ")",
            name="ck_lab_oav_assessment_shape",
        ),
        sa.CheckConstraint(
            "strict_science_mode = 1",
            name="ck_lab_oav_assessment_strict",
        ),
        sa.CheckConstraint(
            f"requested_endpoint IN ({_quoted(THRESHOLD_ENDPOINTS)})",
            name="ck_lab_oav_assessment_endpoint",
        ),
        sa.CheckConstraint(
            f"requested_route IN ({_quoted(THRESHOLD_ROUTES)})",
            name="ck_lab_oav_assessment_route",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_oav_assessment_content_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["concentration_observation_id"],
            ["lab_property_observations.id"],
            ondelete="RESTRICT",
            name="fk_lab_oav_assessment_concentration",
        ),
        sa.ForeignKeyConstraint(
            ["threshold_assertion_id"],
            ["lab_selected_assertions.id"],
            ondelete="RESTRICT",
            name="fk_lab_oav_assessment_threshold_assertion",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_oav_assessment_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_oav_assessments_concentration_observation_id",
        "lab_oav_assessments",
        ["concentration_observation_id"],
        unique=False,
    )
    op.create_index(
        "ix_lab_oav_assessments_threshold_assertion_id",
        "lab_oav_assessments",
        ["threshold_assertion_id"],
        unique=False,
    )

    op.create_table(
        "lab_legacy_threshold_records",
        *_record_columns(),
        sa.Column(
            "schema_version",
            sa.String(length=80),
            nullable=False,
        ),
        sa.Column("material_key", sa.Text(), nullable=False),
        sa.Column("medium", sa.String(length=60), nullable=False),
        sa.Column("numeric_value", sa.Float(), nullable=False),
        sa.Column("original_unit", sa.Text(), nullable=False),
        sa.Column(
            "verification_status",
            sa.String(length=80),
            nullable=False,
        ),
        sa.Column(
            "authority_state",
            sa.String(length=60),
            nullable=False,
        ),
        sa.Column("source_payload_json", sa.JSON(), nullable=False),
        sa.Column(
            "content_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(verification_status) > 0",
            name="ck_lab_legacy_threshold_status",
        ),
        sa.CheckConstraint(
            f"authority_state = '{LEGACY_THRESHOLD_AUTHORITY}'",
            name="ck_lab_legacy_threshold_authority",
        ),
        sa.CheckConstraint(
            "numeric_value > 0",
            name="ck_lab_legacy_threshold_value",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_legacy_threshold_content_sha256",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_legacy_threshold_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_legacy_threshold_records_material_key",
        "lab_legacy_threshold_records",
        ["material_key"],
        unique=False,
    )

    for table_name in B3_TABLES:
        _create_append_only_triggers(table_name)


def downgrade() -> None:
    for table_name in reversed(B3_TABLES):
        _drop_append_only_triggers(table_name)
    op.drop_index(
        "ix_lab_legacy_threshold_records_material_key",
        table_name="lab_legacy_threshold_records",
    )
    op.drop_table("lab_legacy_threshold_records")
    op.drop_index(
        "ix_lab_oav_assessments_threshold_assertion_id",
        table_name="lab_oav_assessments",
    )
    op.drop_index(
        "ix_lab_oav_assessments_concentration_observation_id",
        table_name="lab_oav_assessments",
    )
    op.drop_table("lab_oav_assessments")
    op.drop_index(
        "ix_lab_threshold_observation_contexts_observation_id",
        table_name="lab_threshold_observation_contexts",
    )
    op.drop_table("lab_threshold_observation_contexts")
