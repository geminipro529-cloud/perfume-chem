"""Add strict Checkpoint-9 external-validation intake records.

Revision ID: 20260927_0019
Revises: 20260923_0018
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260927_0019"
down_revision: str | None = "20260923_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_NAME = "lab_external_validation_records"
RECORD_KINDS = ("TEMPORAL_OBSERVATION", "PAIRWISE_PREFERENCE")
MISSINGNESS_STATES = ("OBSERVED", "MISSING", "NOT_APPLICABLE")
PREFERENCE_OUTCOMES = ("PRIMARY", "SECONDARY", "TIE")


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


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
        TABLE_NAME,
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("schema_version", sa.String(length=96), nullable=False),
        sa.Column("record_kind", sa.String(length=40), nullable=False),
        sa.Column("experiment_id", sa.String(length=36), nullable=False),
        sa.Column("primary_application_id", sa.String(length=36), nullable=False),
        sa.Column("secondary_application_id", sa.String(length=36)),
        sa.Column("requester_scope", sa.String(length=255), nullable=False),
        sa.Column("protocol_id", sa.String(length=255), nullable=False),
        sa.Column("endpoint_id", sa.String(length=255), nullable=False),
        sa.Column("repeat_id", sa.String(length=255), nullable=False),
        sa.Column("time_seconds_decimal_text", sa.String(length=128), nullable=False),
        sa.Column("presentation_sequence_id", sa.String(length=255), nullable=False),
        sa.Column("presentation_position", sa.Integer()),
        sa.Column("missingness_state", sa.String(length=32), nullable=False),
        sa.Column("value_decimal_text", sa.String(length=128)),
        sa.Column("preference_outcome", sa.String(length=32)),
        sa.Column("missing_reason", sa.String(length=500)),
        sa.Column("protocol_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("sample_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("condition_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("order_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("assessor_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("provenance_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("idempotency_key_sha256", sa.String(length=64), nullable=False),
        sa.Column("command_sha256", sa.String(length=64), nullable=False),
        sa.Column("canonical_cell_sha256", sa.String(length=64), nullable=False),
        sa.Column("protocol_scope_sha256", sa.String(length=64), nullable=False),
        sa.Column("sample_scope_sha256", sa.String(length=64), nullable=False),
        sa.Column("condition_scope_sha256", sa.String(length=64), nullable=False),
        sa.Column("order_scope_sha256", sa.String(length=64), nullable=False),
        sa.Column("assessor_scope_sha256", sa.String(length=64), nullable=False),
        sa.Column("provenance_scope_sha256", sa.String(length=64), nullable=False),
        sa.Column("record_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "processing_allowed", sa.Boolean(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "scientific_authority", sa.Boolean(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "sensory_authority", sa.Boolean(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "model_calibration_authority",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "release_authority", sa.Boolean(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "safety_authority", sa.Boolean(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "compounding_authority", sa.Boolean(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "evidence_admission_authorized",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"record_kind IN ({_quoted(RECORD_KINDS)})",
            name="ck_lab_external_validation_kind",
        ),
        sa.CheckConstraint(
            f"missingness_state IN ({_quoted(MISSINGNESS_STATES)})",
            name="ck_lab_external_validation_missingness",
        ),
        sa.CheckConstraint(
            "preference_outcome IS NULL OR preference_outcome IN "
            f"({_quoted(PREFERENCE_OUTCOMES)})",
            name="ck_lab_external_validation_preference_outcome",
        ),
        sa.CheckConstraint(
            "(record_kind = 'TEMPORAL_OBSERVATION' "
            "AND secondary_application_id IS NULL "
            "AND presentation_position IS NOT NULL "
            "AND preference_outcome IS NULL) OR "
            "(record_kind = 'PAIRWISE_PREFERENCE' "
            "AND secondary_application_id IS NOT NULL "
            "AND presentation_position IS NULL "
            "AND value_decimal_text IS NULL)",
            name="ck_lab_external_validation_kind_shape",
        ),
        sa.CheckConstraint(
            "(missingness_state = 'OBSERVED' AND "
            "((record_kind = 'TEMPORAL_OBSERVATION' "
            "AND value_decimal_text IS NOT NULL) OR "
            "(record_kind = 'PAIRWISE_PREFERENCE' "
            "AND preference_outcome IS NOT NULL)) "
            "AND missing_reason IS NULL) OR "
            "(missingness_state != 'OBSERVED' "
            "AND value_decimal_text IS NULL "
            "AND preference_outcome IS NULL "
            "AND missing_reason IS NOT NULL)",
            name="ck_lab_external_validation_value_shape",
        ),
        sa.CheckConstraint(
            "presentation_position IS NULL OR presentation_position >= 1",
            name="ck_lab_external_validation_position",
        ),
        sa.CheckConstraint(
            "length(idempotency_key_sha256) = 64 AND "
            "length(command_sha256) = 64 AND "
            "length(canonical_cell_sha256) = 64 AND "
            "length(protocol_scope_sha256) = 64 AND "
            "length(sample_scope_sha256) = 64 AND "
            "length(condition_scope_sha256) = 64 AND "
            "length(order_scope_sha256) = 64 AND "
            "length(assessor_scope_sha256) = 64 AND "
            "length(provenance_scope_sha256) = 64 AND "
            "length(record_sha256) = 64",
            name="ck_lab_external_validation_hashes",
        ),
        sa.CheckConstraint(
            "processing_allowed = 0 AND scientific_authority = 0 "
            "AND sensory_authority = 0 AND model_calibration_authority = 0 "
            "AND release_authority = 0 AND safety_authority = 0 "
            "AND compounding_authority = 0 AND evidence_admission_authorized = 0",
            name="ck_lab_external_validation_no_authority",
        ),
        sa.ForeignKeyConstraint(
            ["experiment_id"], ["lab_experiments.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["primary_application_id"],
            ["lab_applications.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["secondary_application_id"],
            ["lab_applications.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "requester_scope",
            "idempotency_key_sha256",
            name="uq_lab_external_validation_idempotency",
        ),
        sa.UniqueConstraint(
            "canonical_cell_sha256",
            name="uq_lab_external_validation_cell",
        ),
        sa.UniqueConstraint(
            "record_sha256",
            name="uq_lab_external_validation_record_hash",
        ),
    )
    op.create_index(
        "ix_lab_external_validation_experiment",
        TABLE_NAME,
        ["experiment_id", "record_kind", "created_at"],
    )
    op.create_index(
        "ix_lab_external_validation_primary_application",
        TABLE_NAME,
        ["primary_application_id"],
    )
    op.create_index(
        "ix_lab_external_validation_secondary_application",
        TABLE_NAME,
        ["secondary_application_id"],
    )
    _create_append_only_triggers(TABLE_NAME)


def downgrade() -> None:
    _drop_append_only_triggers(TABLE_NAME)
    op.drop_index("ix_lab_external_validation_secondary_application", table_name=TABLE_NAME)
    op.drop_index("ix_lab_external_validation_primary_application", table_name=TABLE_NAME)
    op.drop_index("ix_lab_external_validation_experiment", table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)
