"""Add the append-only B1 source and provenance registry."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260730_0005"
down_revision = "20260730_0004"
branch_labels = None
depends_on = None

SOURCE_TYPES = (
    "AUTHENTICATED_FORMULA_OR_DOSSIER",
    "PRIMARY_PEER_REVIEWED_PAPER",
    "REVIEW_PAPER",
    "STANDARD",
    "REGULATION_OR_OFFICIAL_GUIDANCE",
    "AUTHORITATIVE_DATABASE_RECORD",
    "SUPPLIER_COA",
    "SUPPLIER_SPECIFICATION",
    "SUPPLIER_SDS",
    "SUPPLIER_IFRA_CERTIFICATE",
    "SUPPLIER_ALLERGEN_DECLARATION",
    "PATENT",
    "LOCAL_ANALYTICAL_EXPERIMENT",
    "LOCAL_SENSORY_EXPERIMENT",
    "EXPERT_NOTE",
    "SECONDARY_RECONSTRUCTION",
    "COMMUNITY_OBSERVATION",
    "AI_GENERATED_HYPOTHESIS",
)
EVIDENCE_WORKFLOW_STATES = (
    "STAGED",
    "PARSED",
    "IDENTITY_RESOLVED",
    "UNIT_NORMALIZED",
    "CONDITION_NORMALIZED",
    "CONFLICT_CHECKED",
    "HUMAN_REVIEWED",
    "ACCEPTED_FOR_SCOPED_USE",
    "REJECTED",
    "SUPERSEDED",
)
SOURCE_REVIEW_STATES = ("UNREVIEWED", "REVIEWED", "REJECTED", "SUPERSEDED")
SOURCE_DERIVATION_RELATIONS = (
    "DERIVED_FROM",
    "REPRODUCES",
    "CITES",
    "INCORPORATES",
)
WORKFLOW_SUBJECT_TYPES = ("SOURCE_VERSION", "EXTRACTION_RECORD")
SOURCE_TABLES = (
    "lab_source_document_versions",
    "lab_source_derivation_links",
    "lab_source_extraction_records",
    "lab_evidence_workflow_events",
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
        op.execute(f"DROP TRIGGER IF EXISTS {trigger_name}")


def upgrade() -> None:
    op.create_table(
        "lab_source_document_versions",
        *_record_columns(),
        sa.Column("source_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.String(length=80), nullable=False),
        sa.Column("source_type", sa.String(length=60), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column(
            "authors_json",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("issuing_organization", sa.Text()),
        sa.Column("container_title", sa.Text()),
        sa.Column("publisher_or_authority", sa.Text()),
        sa.Column(
            "identifiers_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("publication_date", sa.Date()),
        sa.Column("revision_date", sa.Date()),
        sa.Column("effective_date", sa.Date()),
        sa.Column("retrieval_date", sa.Date()),
        sa.Column("edition_or_amendment", sa.Text()),
        sa.Column(
            "default_locator_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("license_or_reuse_restriction", sa.Text()),
        sa.Column("language", sa.String(length=40), nullable=False),
        sa.Column("original_unit", sa.Text()),
        sa.Column("original_terminology", sa.Text()),
        sa.Column("reviewer_pseudonym", sa.String(length=255)),
        sa.Column("review_state", sa.String(length=40), nullable=False),
        sa.Column("supersedes_version_id", sa.String(length=36)),
        sa.Column(
            "independence_group",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column("preserved_artifact_path", sa.Text()),
        sa.Column("parent_record_sha256", sa.String(length=64)),
        sa.Column("record_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "version_number >= 1",
            name="ck_lab_source_version_positive",
        ),
        sa.CheckConstraint(
            f"source_type IN ({_quoted(SOURCE_TYPES)})",
            name="ck_lab_source_type",
        ),
        sa.CheckConstraint(
            f"review_state IN ({_quoted(SOURCE_REVIEW_STATES)})",
            name="ck_lab_source_review_state",
        ),
        sa.CheckConstraint(
            "length(artifact_sha256) = 64",
            name="ck_lab_source_artifact_sha256",
        ),
        sa.CheckConstraint(
            "length(record_sha256) = 64",
            name="ck_lab_source_record_sha256",
        ),
        sa.CheckConstraint(
            "(version_number = 1 AND supersedes_version_id IS NULL "
            "AND parent_record_sha256 IS NULL) OR "
            "(version_number > 1 AND supersedes_version_id IS NOT NULL "
            "AND length(parent_record_sha256) = 64)",
            name="ck_lab_source_version_chain",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_version_id"],
            ["lab_source_document_versions.id"],
            ondelete="RESTRICT",
            name="fk_lab_source_document_supersedes",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_id",
            "version_number",
            name="uq_lab_source_document_version",
        ),
        sa.UniqueConstraint(
            "record_sha256",
            name="uq_lab_source_document_record_sha256",
        ),
    )
    op.create_index(
        "ix_lab_source_document_versions_source_id",
        "lab_source_document_versions",
        ["source_id"],
        unique=False,
    )
    op.create_index(
        "ix_lab_source_document_versions_independence_group",
        "lab_source_document_versions",
        ["independence_group"],
        unique=False,
    )

    op.create_table(
        "lab_source_derivation_links",
        *_record_columns(),
        sa.Column(
            "child_source_version_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "parent_source_version_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column("relation", sa.String(length=40), nullable=False),
        sa.Column("record_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            f"relation IN ({_quoted(SOURCE_DERIVATION_RELATIONS)})",
            name="ck_lab_source_derivation_relation",
        ),
        sa.CheckConstraint(
            "child_source_version_id <> parent_source_version_id",
            name="ck_lab_source_derivation_not_self",
        ),
        sa.CheckConstraint(
            "length(record_sha256) = 64",
            name="ck_lab_source_derivation_record_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["child_source_version_id"],
            ["lab_source_document_versions.id"],
            ondelete="RESTRICT",
            name="fk_lab_source_derivation_child",
        ),
        sa.ForeignKeyConstraint(
            ["parent_source_version_id"],
            ["lab_source_document_versions.id"],
            ondelete="RESTRICT",
            name="fk_lab_source_derivation_parent",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "child_source_version_id",
            "parent_source_version_id",
            "relation",
            name="uq_lab_source_derivation_link",
        ),
        sa.UniqueConstraint(
            "record_sha256",
            name="uq_lab_source_derivation_record_sha256",
        ),
    )
    op.create_index(
        "ix_lab_source_derivation_links_child_source_version_id",
        "lab_source_derivation_links",
        ["child_source_version_id"],
        unique=False,
    )
    op.create_index(
        "ix_lab_source_derivation_links_parent_source_version_id",
        "lab_source_derivation_links",
        ["parent_source_version_id"],
        unique=False,
    )

    op.create_table(
        "lab_source_extraction_records",
        *_record_columns(),
        sa.Column("source_version_id", sa.String(length=36), nullable=False),
        sa.Column(
            "locator_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "structure_context_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("original_wording", sa.Text()),
        sa.Column("original_value_json", sa.JSON()),
        sa.Column("parsed_value_json", sa.JSON()),
        sa.Column(
            "normalization_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("parser_or_model_version", sa.Text(), nullable=False),
        sa.Column("reviewer_pseudonym", sa.String(length=255)),
        sa.Column(
            "uncertainty_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "ambiguity_json",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("output_observation_id", sa.String(length=36)),
        sa.Column("input_sha256", sa.String(length=64), nullable=False),
        sa.Column("output_sha256", sa.String(length=64), nullable=False),
        sa.Column("record_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "length(input_sha256) = 64",
            name="ck_lab_source_extraction_input_sha256",
        ),
        sa.CheckConstraint(
            "length(output_sha256) = 64",
            name="ck_lab_source_extraction_output_sha256",
        ),
        sa.CheckConstraint(
            "length(record_sha256) = 64",
            name="ck_lab_source_extraction_record_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["source_version_id"],
            ["lab_source_document_versions.id"],
            ondelete="RESTRICT",
            name="fk_lab_source_extraction_source",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "record_sha256",
            name="uq_lab_source_extraction_record_sha256",
        ),
    )
    op.create_index(
        "ix_lab_source_extraction_records_source_version_id",
        "lab_source_extraction_records",
        ["source_version_id"],
        unique=False,
    )
    op.create_index(
        "ix_lab_source_extraction_records_output_observation_id",
        "lab_source_extraction_records",
        ["output_observation_id"],
        unique=False,
    )

    op.create_table(
        "lab_evidence_workflow_events",
        *_record_columns(),
        sa.Column("subject_type", sa.String(length=40), nullable=False),
        sa.Column("subject_id", sa.String(length=36), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("from_state", sa.String(length=40)),
        sa.Column("to_state", sa.String(length=40), nullable=False),
        sa.Column("reviewer_pseudonym", sa.String(length=255)),
        sa.Column(
            "scope_json",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text()),
        sa.Column("record_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "sequence_number >= 1",
            name="ck_lab_evidence_workflow_sequence_positive",
        ),
        sa.CheckConstraint(
            f"subject_type IN ({_quoted(WORKFLOW_SUBJECT_TYPES)})",
            name="ck_lab_evidence_workflow_subject_type",
        ),
        sa.CheckConstraint(
            f"from_state IS NULL OR from_state IN "
            f"({_quoted(EVIDENCE_WORKFLOW_STATES)})",
            name="ck_lab_evidence_workflow_from_state",
        ),
        sa.CheckConstraint(
            f"to_state IN ({_quoted(EVIDENCE_WORKFLOW_STATES)})",
            name="ck_lab_evidence_workflow_to_state",
        ),
        sa.CheckConstraint(
            "from_state IS NULL OR from_state <> to_state",
            name="ck_lab_evidence_workflow_transition_changes_state",
        ),
        sa.CheckConstraint(
            "length(record_sha256) = 64",
            name="ck_lab_evidence_workflow_record_sha256",
        ),
        sa.CheckConstraint(
            "(sequence_number = 1 AND from_state IS NULL "
            "AND to_state = 'STAGED') OR "
            "(sequence_number > 1 AND from_state IS NOT NULL)",
            name="ck_lab_evidence_workflow_initial_state",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "subject_type",
            "subject_id",
            "sequence_number",
            name="uq_lab_evidence_workflow_sequence",
        ),
        sa.UniqueConstraint(
            "record_sha256",
            name="uq_lab_evidence_workflow_record_sha256",
        ),
    )
    op.create_index(
        "ix_lab_evidence_workflow_subject",
        "lab_evidence_workflow_events",
        ["subject_type", "subject_id"],
        unique=False,
    )

    for table_name in SOURCE_TABLES:
        _create_append_only_triggers(table_name)


def downgrade() -> None:
    for table_name in reversed(SOURCE_TABLES):
        _drop_append_only_triggers(table_name)

    op.drop_index(
        "ix_lab_evidence_workflow_subject",
        table_name="lab_evidence_workflow_events",
    )
    op.drop_table("lab_evidence_workflow_events")

    op.drop_index(
        "ix_lab_source_extraction_records_output_observation_id",
        table_name="lab_source_extraction_records",
    )
    op.drop_index(
        "ix_lab_source_extraction_records_source_version_id",
        table_name="lab_source_extraction_records",
    )
    op.drop_table("lab_source_extraction_records")

    op.drop_index(
        "ix_lab_source_derivation_links_parent_source_version_id",
        table_name="lab_source_derivation_links",
    )
    op.drop_index(
        "ix_lab_source_derivation_links_child_source_version_id",
        table_name="lab_source_derivation_links",
    )
    op.drop_table("lab_source_derivation_links")

    op.drop_index(
        "ix_lab_source_document_versions_independence_group",
        table_name="lab_source_document_versions",
    )
    op.drop_index(
        "ix_lab_source_document_versions_source_id",
        table_name="lab_source_document_versions",
    )
    op.drop_table("lab_source_document_versions")
