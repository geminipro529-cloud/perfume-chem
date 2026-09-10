"""Add append-only, operation-scoped B1 source-use assertions.

Revision ID: 20260810_0015
Revises: 20260810_0014

These rows preserve source-declared permissions, prohibitions, conflicts, and
unresolved terms for one exact operation.  They are not legal conclusions and
do not grant formula, model, publication, or release authority.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260810_0015"
down_revision: str | None = "20260810_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SOURCE_REVIEW_STATES = ("UNREVIEWED", "REVIEWED", "REJECTED", "SUPERSEDED")
SOURCE_USE_ARTIFACT_SCOPES = (
    "SOURCE_RECORD",
    "METADATA",
    "ABSTRACT",
    "FULL_TEXT",
    "DATASET",
    "API_RESPONSE",
    "SOFTWARE",
    "USER_GENERATED_CONTENT",
    "DERIVATIVE_OUTPUT",
    "OTHER",
)
SOURCE_USE_ACTIONS = (
    "DISCOVERY_METADATA",
    "API_FETCH",
    "LOCAL_CACHE",
    "ARCHIVE_SOURCE_BYTES",
    "INTERNAL_ANALYSIS",
    "ML_TRAIN_OR_EVALUATE",
    "PUBLISH_DERIVATIVE",
    "REDISTRIBUTE_RAW",
    "COMMERCIAL_RUNTIME",
    "EXTERNAL_TRANSMISSION",
)
SOURCE_USE_DECISIONS = (
    "DECLARED_ALLOWED",
    "DECLARED_PROHIBITED",
    "UNRESOLVED",
    "CONFLICT",
)
TABLE_NAME = "lab_source_use_constraint_versions"


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
        trigger_name = f"trg_{table_name}_{operation.lower()}_append_only"
        op.execute(f"DROP TRIGGER IF EXISTS {trigger_name}")


def upgrade() -> None:
    op.create_table(
        TABLE_NAME,
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("constraint_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column(
            "subject_source_version_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "terms_source_version_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column("artifact_scope", sa.String(length=40), nullable=False),
        sa.Column(
            "artifact_locator_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("channel", sa.String(length=120), nullable=False),
        sa.Column("intended_action", sa.String(length=60), nullable=False),
        sa.Column("purpose_context", sa.String(length=160), nullable=False),
        sa.Column("decision", sa.String(length=40), nullable=False),
        sa.Column(
            "constraints_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("terms_effective_date", sa.Date()),
        sa.Column("terms_retrieval_date", sa.Date(), nullable=False),
        sa.Column("reviewer_pseudonym", sa.String(length=255)),
        sa.Column("review_state", sa.String(length=40), nullable=False),
        sa.Column(
            "legal_review_required",
            sa.Boolean(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column("supersedes_version_id", sa.String(length=36)),
        sa.Column("parent_record_sha256", sa.String(length=64)),
        sa.Column("record_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "version_number >= 1",
            name="ck_lab_source_use_constraint_version_positive",
        ),
        sa.CheckConstraint(
            f"artifact_scope IN ({_quoted(SOURCE_USE_ARTIFACT_SCOPES)})",
            name="ck_lab_source_use_artifact_scope",
        ),
        sa.CheckConstraint(
            f"intended_action IN ({_quoted(SOURCE_USE_ACTIONS)})",
            name="ck_lab_source_use_action",
        ),
        sa.CheckConstraint(
            f"decision IN ({_quoted(SOURCE_USE_DECISIONS)})",
            name="ck_lab_source_use_decision",
        ),
        sa.CheckConstraint(
            f"review_state IN ({_quoted(SOURCE_REVIEW_STATES)})",
            name="ck_lab_source_use_review_state",
        ),
        sa.CheckConstraint(
            "review_state <> 'REVIEWED' OR reviewer_pseudonym IS NOT NULL",
            name="ck_lab_source_use_reviewed_by",
        ),
        sa.CheckConstraint(
            "length(record_sha256) = 64",
            name="ck_lab_source_use_record_sha256",
        ),
        sa.CheckConstraint(
            "(version_number = 1 AND supersedes_version_id IS NULL "
            "AND parent_record_sha256 IS NULL) OR "
            "(version_number > 1 AND supersedes_version_id IS NOT NULL "
            "AND length(parent_record_sha256) = 64)",
            name="ck_lab_source_use_version_chain",
        ),
        sa.ForeignKeyConstraint(
            ["subject_source_version_id"],
            ["lab_source_document_versions.id"],
            ondelete="RESTRICT",
            name="fk_lab_source_use_subject_source",
        ),
        sa.ForeignKeyConstraint(
            ["terms_source_version_id"],
            ["lab_source_document_versions.id"],
            ondelete="RESTRICT",
            name="fk_lab_source_use_terms_source",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_version_id"],
            [f"{TABLE_NAME}.id"],
            ondelete="RESTRICT",
            name="fk_lab_source_use_supersedes",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "constraint_id",
            "version_number",
            name="uq_lab_source_use_constraint_version",
        ),
        sa.UniqueConstraint(
            "record_sha256",
            name="uq_lab_source_use_constraint_record_sha256",
        ),
    )
    for column in (
        "constraint_id",
        "subject_source_version_id",
        "terms_source_version_id",
    ):
        op.create_index(
            f"ix_{TABLE_NAME}_{column}",
            TABLE_NAME,
            [column],
            unique=False,
        )
    _create_append_only_triggers(TABLE_NAME)


def downgrade() -> None:
    _drop_append_only_triggers(TABLE_NAME)
    for column in reversed(
        (
            "constraint_id",
            "subject_source_version_id",
            "terms_source_version_id",
        )
    ):
        op.drop_index(
            f"ix_{TABLE_NAME}_{column}",
            table_name=TABLE_NAME,
        )
    op.drop_table(TABLE_NAME)
