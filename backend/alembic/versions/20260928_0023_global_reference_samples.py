"""Add governed commercial-reference samples and comparison engine jobs.

Revision ID: 20260928_0023
Revises: 20260927_0022
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260928_0023"
down_revision: str | None = "20260927_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "lab_commercial_reference_samples"
PREVIOUS_JOB_TYPES = (
    "FORMULA_ANALYSIS",
    "RELEASE_SIMULATION",
    "RELEASE_GATE",
    "MIXER_SEQUENCE",
    "OPTIMIZER_SEARCH",
    "CANDIDATE_EVALUATION",
    "SHORTLIST_EVALUATION",
    "MODEL_BENCHMARK",
    "PREFERENCE_ANALYSIS",
    "BATCH_GATE",
)
CURRENT_JOB_TYPES = (*PREVIOUS_JOB_TYPES[:-1], "REFERENCE_PANEL_EVALUATION", "BATCH_GATE")


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _replace_job_type_constraint(values: tuple[str, ...]) -> None:
    if op.get_bind().dialect.name == "sqlite":
        for operation in ("update", "delete"):
            op.execute(f"DROP TRIGGER IF EXISTS trg_lab_engine_jobs_{operation}_append_only")
    with op.batch_alter_table("lab_engine_jobs", recreate="always") as batch:
        batch.drop_constraint("ck_lab_engine_job_type", type_="check")
        batch.create_check_constraint(
            "ck_lab_engine_job_type",
            f"job_type IN ({_quoted(values)})",
        )
    if op.get_bind().dialect.name == "sqlite":
        for operation in ("UPDATE", "DELETE"):
            op.execute(
                f"""
                CREATE TRIGGER trg_lab_engine_jobs_{operation.lower()}_append_only
                BEFORE {operation} ON lab_engine_jobs
                BEGIN
                    SELECT RAISE(ABORT, 'append-only: lab_engine_jobs');
                END
                """
            )


def _create_append_only_triggers() -> None:
    if op.get_bind().dialect.name != "sqlite":
        return
    for operation in ("UPDATE", "DELETE"):
        op.execute(
            f"""
            CREATE TRIGGER trg_{TABLE}_{operation.lower()}_append_only
            BEFORE {operation} ON {TABLE}
            BEGIN
                SELECT RAISE(ABORT, 'append-only: {TABLE}');
            END
            """
        )


def upgrade() -> None:
    _replace_job_type_constraint(CURRENT_JOB_TYPES)
    op.create_table(
        TABLE,
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("schema_version", sa.String(length=96), nullable=False),
        sa.Column("sample_id", sa.String(length=36), nullable=False),
        sa.Column("requester_scope", sa.String(length=255), nullable=False),
        sa.Column("product_id", sa.String(length=255), nullable=False),
        sa.Column("concentration", sa.String(length=255), nullable=False),
        sa.Column("edition", sa.String(length=255), nullable=False),
        sa.Column("sample_identifier", sa.String(length=255), nullable=False),
        sa.Column("registry_sha256", sa.String(length=64), nullable=False),
        sa.Column("panel_id", sa.String(length=255)),
        sa.Column("panel_sha256", sa.String(length=64)),
        sa.Column("purchase_source", sa.String(length=500)),
        sa.Column("batch_code", sa.String(length=255)),
        sa.Column("acquisition_date", sa.Date()),
        sa.Column(
            "authenticity_documentation_state",
            sa.String(length=80),
            server_default="NOT_PROVIDED_PERSONAL_MODE",
            nullable=False,
        ),
        sa.Column("payload_json", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("idempotency_key_sha256", sa.String(length=64), nullable=False),
        sa.Column("command_sha256", sa.String(length=64), nullable=False),
        sa.Column("record_sha256", sa.String(length=64), nullable=False),
        sa.Column("release_authority", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("safety_authority", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("compounding_authority", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("evidence_admission_authorized", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.CheckConstraint(
            "length(registry_sha256) = 64 AND "
            "(panel_sha256 IS NULL OR length(panel_sha256) = 64) AND "
            "length(idempotency_key_sha256) = 64 AND "
            "length(command_sha256) = 64 AND length(record_sha256) = 64",
            name="ck_lab_commercial_reference_sample_hashes",
        ),
        sa.CheckConstraint(
            "release_authority = 0 AND safety_authority = 0 "
            "AND compounding_authority = 0 AND evidence_admission_authorized = 0",
            name="ck_lab_commercial_reference_sample_no_authority",
        ),
        sa.ForeignKeyConstraint(["sample_id"], ["lab_samples.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sample_id", name="uq_lab_commercial_reference_sample_link"),
        sa.UniqueConstraint(
            "requester_scope",
            "idempotency_key_sha256",
            name="uq_lab_commercial_reference_sample_idempotency",
        ),
        sa.UniqueConstraint("record_sha256", name="uq_lab_commercial_reference_sample_hash"),
    )
    op.create_index(
        "ix_lab_commercial_reference_sample_product",
        TABLE,
        ["product_id", "sample_identifier"],
    )
    op.create_index(
        "ix_lab_commercial_reference_sample_sample_id",
        TABLE,
        ["sample_id"],
    )
    _create_append_only_triggers()


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        for operation in ("update", "delete"):
            op.execute(f"DROP TRIGGER IF EXISTS trg_{TABLE}_{operation}_append_only")
    op.drop_index("ix_lab_commercial_reference_sample_sample_id", table_name=TABLE)
    op.drop_index("ix_lab_commercial_reference_sample_product", table_name=TABLE)
    op.drop_table(TABLE)
    _replace_job_type_constraint(PREVIOUS_JOB_TYPES)
