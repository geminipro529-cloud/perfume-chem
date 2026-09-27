"""Add immutable instrumental research observation intake.

Revision ID: 20260927_0022
Revises: 20260927_0021
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260927_0022"
down_revision: str | None = "20260927_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "lab_instrumental_observations"


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
    op.create_table(
        TABLE,
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("schema_version", sa.String(length=96), nullable=False),
        sa.Column("observation_id", sa.String(length=255), nullable=False),
        sa.Column("requester_scope", sa.String(length=255), nullable=False),
        sa.Column("formula_sha256", sa.String(length=64), nullable=False),
        sa.Column("inventory_sha256", sa.String(length=64), nullable=False),
        sa.Column("stock_lot_bundle_sha256", sa.String(length=64), nullable=False),
        sa.Column("preparation_receipt_sha256", sa.String(length=64), nullable=False),
        sa.Column("release_scenario_sha256", sa.String(length=64), nullable=False),
        sa.Column("deposit_decimal_text", sa.String(length=128), nullable=False),
        sa.Column("deposit_unit", sa.String(length=8), nullable=False),
        sa.Column("matrix_id", sa.String(length=255), nullable=False),
        sa.Column("substrate", sa.String(length=32), nullable=False),
        sa.Column("temperature_k_decimal_text", sa.String(length=128), nullable=False),
        sa.Column("relative_humidity_decimal_text", sa.String(length=128), nullable=False),
        sa.Column("airflow_m_s_decimal_text", sa.String(length=128), nullable=False),
        sa.Column("surface_area_m2_decimal_text", sa.String(length=128), nullable=False),
        sa.Column("delivery_geometry_id", sa.String(length=255), nullable=False),
        sa.Column("sampling_method_id", sa.String(length=255), nullable=False),
        sa.Column("instrument_id", sa.String(length=255), nullable=False),
        sa.Column("calibration_receipt_sha256", sa.String(length=64), nullable=False),
        sa.Column("blank_receipt_sha256", sa.String(length=64), nullable=False),
        sa.Column("time_seconds_decimal_text", sa.String(length=128), nullable=False),
        sa.Column("replicate_id", sa.String(length=255), nullable=False),
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("raw_data_sha256", sa.String(length=64), nullable=False),
        sa.Column("processed_result_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "protocol_deviations_json",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column(
            "review_state",
            sa.String(length=32),
            server_default="UNREVIEWED",
            nullable=False,
        ),
        sa.Column(
            "payload_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("idempotency_key_sha256", sa.String(length=64), nullable=False),
        sa.Column("command_sha256", sa.String(length=64), nullable=False),
        sa.Column("record_sha256", sa.String(length=64), nullable=False),
        sa.Column("review_note", sa.Text()),
        sa.Column("processing_allowed", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("scientific_authority", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("model_calibration_authority", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("release_authority", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("safety_authority", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("compounding_authority", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("evidence_admission_authorized", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.CheckConstraint(
            "substrate IN ('GLASS', 'BLOTTER', 'SKIN_SURROGATE', 'SKIN')",
            name="ck_lab_instrumental_observation_substrate",
        ),
        sa.CheckConstraint(
            "deposit_unit IN ('mg', 'g', 'uL', 'mL')",
            name="ck_lab_instrumental_observation_deposit_unit",
        ),
        sa.CheckConstraint(
            "review_state = 'UNREVIEWED'",
            name="ck_lab_instrumental_observation_review_state",
        ),
        sa.CheckConstraint(
            "length(formula_sha256) = 64 AND length(inventory_sha256) = 64 "
            "AND length(stock_lot_bundle_sha256) = 64 "
            "AND length(preparation_receipt_sha256) = 64 "
            "AND length(release_scenario_sha256) = 64 "
            "AND length(calibration_receipt_sha256) = 64 "
            "AND length(blank_receipt_sha256) = 64 "
            "AND length(raw_data_sha256) = 64 "
            "AND length(processed_result_sha256) = 64 "
            "AND length(idempotency_key_sha256) = 64 "
            "AND length(command_sha256) = 64 AND length(record_sha256) = 64",
            name="ck_lab_instrumental_observation_hashes",
        ),
        sa.CheckConstraint(
            "processing_allowed = 0 AND scientific_authority = 0 "
            "AND model_calibration_authority = 0 AND release_authority = 0 "
            "AND safety_authority = 0 AND compounding_authority = 0 "
            "AND evidence_admission_authorized = 0",
            name="ck_lab_instrumental_observation_no_authority",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "requester_scope",
            "idempotency_key_sha256",
            name="uq_lab_instrumental_observation_idempotency",
        ),
        sa.UniqueConstraint(
            "observation_id",
            name="uq_lab_instrumental_observation_identity",
        ),
        sa.UniqueConstraint(
            "record_sha256",
            name="uq_lab_instrumental_observation_record_hash",
        ),
    )
    op.create_index(
        "ix_lab_instrumental_observation_scope",
        TABLE,
        ["formula_sha256", "release_scenario_sha256", "session_id"],
    )
    _create_append_only_triggers()


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        for operation in ("update", "delete"):
            op.execute(f"DROP TRIGGER IF EXISTS trg_{TABLE}_{operation}_append_only")
    op.drop_index("ix_lab_instrumental_observation_scope", table_name=TABLE)
    op.drop_table(TABLE)
