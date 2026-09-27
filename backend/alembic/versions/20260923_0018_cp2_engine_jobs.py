"""Add durable Checkpoint-2 engine jobs.

Revision ID: 20260923_0018
Revises: 20260923_0017
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260923_0018"
down_revision: str | None = "20260923_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "lab_engine_jobs",
    "lab_engine_job_events",
    "lab_engine_job_results",
)
JOB_TYPES = (
    "FORMULA_ANALYSIS",
    "RELEASE_GATE",
    "MIXER_SEQUENCE",
    "OPTIMIZER_SEARCH",
    "SHORTLIST_EVALUATION",
    "BATCH_GATE",
)
EXECUTION_CLASSES = ("READ_ONLY_DIAGNOSTIC", "READ_ONLY_BATCH")
JOB_STATES = (
    "QUEUED",
    "LEASED",
    "RUNNING",
    "SUCCEEDED",
    "WITHHELD",
    "FAILED",
    "CANCEL_REQUESTED",
    "CANCELLED",
)
TERMINAL_STATES = ("SUCCEEDED", "WITHHELD", "FAILED", "CANCELLED")


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _base_columns() -> tuple[sa.Column, sa.Column]:
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
        op.execute(
            f"DROP TRIGGER IF EXISTS "
            f"trg_{table_name}_{operation.lower()}_append_only"
        )


def upgrade() -> None:
    op.create_table(
        "lab_engine_jobs",
        *_base_columns(),
        sa.Column("schema_version", sa.String(length=80), nullable=False),
        sa.Column("contract_version", sa.String(length=80), nullable=False),
        sa.Column("job_type", sa.String(length=60), nullable=False),
        sa.Column("execution_class", sa.String(length=40), nullable=False),
        sa.Column("requester_scope", sa.String(length=255), nullable=False),
        sa.Column(
            "source_request_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "normalized_payload_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("source_request_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "normalized_payload_sha256", sa.String(length=64), nullable=False
        ),
        sa.Column(
            "implementation_fingerprint_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "implementation_manifest_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("reference_bundle_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "inventory_fingerprint_sha256", sa.String(length=64), nullable=False
        ),
        sa.Column(
            "capability_fingerprint_sha256", sa.String(length=64), nullable=False
        ),
        sa.Column("authority_context_sha256", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key_sha256", sa.String(length=64), nullable=False),
        sa.Column("command_sha256", sa.String(length=64), nullable=False),
        sa.Column("job_fingerprint_sha256", sa.String(length=64), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column(
            "max_attempts",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"job_type IN ({_quoted(JOB_TYPES)})",
            name="ck_lab_engine_job_type",
        ),
        sa.CheckConstraint(
            f"execution_class IN ({_quoted(EXECUTION_CLASSES)})",
            name="ck_lab_engine_job_execution_class",
        ),
        sa.CheckConstraint(
            "length(source_request_sha256) = 64 AND "
            "length(normalized_payload_sha256) = 64 AND "
            "length(implementation_fingerprint_sha256) = 64 AND "
            "length(reference_bundle_sha256) = 64 AND "
            "length(inventory_fingerprint_sha256) = 64 AND "
            "length(capability_fingerprint_sha256) = 64 AND "
            "length(authority_context_sha256) = 64 AND "
            "length(idempotency_key_sha256) = 64 AND "
            "length(command_sha256) = 64 AND "
            "length(job_fingerprint_sha256) = 64",
            name="ck_lab_engine_job_hashes",
        ),
        sa.CheckConstraint(
            "timeout_seconds > 0 AND max_attempts = 1",
            name="ck_lab_engine_job_execution_policy",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "requester_scope",
            "idempotency_key_sha256",
            name="uq_lab_engine_job_idempotency",
        ),
        sa.UniqueConstraint(
            "job_fingerprint_sha256",
            name="uq_lab_engine_job_fingerprint",
        ),
    )
    op.create_index(
        "ix_lab_engine_job_created",
        "lab_engine_jobs",
        ["created_at", "job_type"],
    )

    op.create_table(
        "lab_engine_job_events",
        *_base_columns(),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("lease_owner", sa.String(length=255)),
        sa.Column(
            "lease_epoch",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("lease_token_sha256", sa.String(length=64)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column(
            "attempt",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("sanitized_reason", sa.Text()),
        sa.Column(
            "detail_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("parent_event_sha256", sa.String(length=64)),
        sa.Column("event_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            f"state IN ({_quoted(JOB_STATES)})",
            name="ck_lab_engine_job_event_state",
        ),
        sa.CheckConstraint(
            "sequence >= 1 AND lease_epoch >= 0 AND attempt >= 0",
            name="ck_lab_engine_job_event_sequence_attempt",
        ),
        sa.CheckConstraint(
            "(sequence = 1 AND parent_event_sha256 IS NULL) OR "
            "(sequence > 1 AND length(parent_event_sha256) = 64)",
            name="ck_lab_engine_job_event_chain",
        ),
        sa.CheckConstraint(
            "length(event_sha256) = 64 AND "
            "(lease_token_sha256 IS NULL OR length(lease_token_sha256) = 64)",
            name="ck_lab_engine_job_event_hashes",
        ),
        sa.CheckConstraint(
            "(state IN ('LEASED', 'RUNNING') AND lease_owner IS NOT NULL "
            "AND lease_epoch >= 1 AND lease_expires_at IS NOT NULL "
            "AND lease_token_sha256 IS NOT NULL) OR "
            "(state NOT IN ('LEASED', 'RUNNING') AND lease_owner IS NULL "
            "AND lease_expires_at IS NULL AND lease_token_sha256 IS NULL)",
            name="ck_lab_engine_job_event_lease_shape",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["lab_engine_jobs.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_id", "sequence", name="uq_lab_engine_job_event_sequence"
        ),
        sa.UniqueConstraint(
            "event_sha256", name="uq_lab_engine_job_event_hash"
        ),
    )
    op.create_index(
        "ix_lab_engine_job_event_poll",
        "lab_engine_job_events",
        ["state", "lease_expires_at", "created_at"],
    )
    op.create_index(
        "ix_lab_engine_job_event_latest",
        "lab_engine_job_events",
        ["job_id", "sequence"],
    )

    op.create_table(
        "lab_engine_job_results",
        *_base_columns(),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("terminal_state", sa.String(length=32), nullable=False),
        sa.Column(
            "result_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("result_sha256", sa.String(length=64), nullable=False),
        sa.Column("validation_state", sa.String(length=80), nullable=False),
        sa.Column(
            "diagnostics_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "release_authority",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "safety_authority",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "compounding_authority",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "evidence_admission_authorized",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"terminal_state IN ({_quoted(TERMINAL_STATES)})",
            name="ck_lab_engine_job_result_terminal_state",
        ),
        sa.CheckConstraint(
            "length(result_sha256) = 64",
            name="ck_lab_engine_job_result_hash",
        ),
        sa.CheckConstraint(
            "release_authority = 0 AND safety_authority = 0 AND "
            "compounding_authority = 0 AND "
            "evidence_admission_authorized = 0",
            name="ck_lab_engine_job_result_no_authority",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["lab_engine_jobs.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", name="uq_lab_engine_job_result_job"),
    )
    op.create_index(
        "ix_lab_engine_job_result_state",
        "lab_engine_job_results",
        ["terminal_state", "created_at"],
    )

    for table_name in TABLES:
        _create_append_only_triggers(table_name)


def downgrade() -> None:
    for table_name in reversed(TABLES):
        _drop_append_only_triggers(table_name)
    op.drop_index(
        "ix_lab_engine_job_result_state", table_name="lab_engine_job_results"
    )
    op.drop_table("lab_engine_job_results")
    op.drop_index(
        "ix_lab_engine_job_event_latest", table_name="lab_engine_job_events"
    )
    op.drop_index(
        "ix_lab_engine_job_event_poll", table_name="lab_engine_job_events"
    )
    op.drop_table("lab_engine_job_events")
    op.drop_index("ix_lab_engine_job_created", table_name="lab_engine_jobs")
    op.drop_table("lab_engine_jobs")
