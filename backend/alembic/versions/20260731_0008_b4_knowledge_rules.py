"""Build B4 append-only knowledge-rule authority and compilation history.

Revision ID: 20260731_0008
Revises: 20260730_0007
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260731_0008"
down_revision: str | None = "20260730_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RULE_ENDPOINT_KINDS = (
    "EXACT_IDENTITY",
    "GROUP",
    "GENERIC_PROSE",
    "UNRESOLVED",
)
RULE_RELATIONS = (
    "REINFORCES",
    "MASKS",
    "SUPPRESSES",
    "SYNERGIZES",
    "ADDS",
    "EXTENDS",
    "BRIDGES",
    "BRIGHTENS",
    "ROUNDS",
    "DRIES",
    "WARMS",
    "COOLS",
    "DIFFUSES",
    "TEMPORALLY_HANDS_OFF",
    "FUNCTIONALLY_SUBSTITUTES",
    "NON_EQUIVALENT",
    "MATRIX_DEPENDENT_INTERACTION",
    "SAFETY_CONTRIBUTION",
)
RULE_DIRECTIONALITIES = ("DIRECTED", "BIDIRECTIONAL", "SYMMETRIC")
RULE_STATUSES = (
    "AUTHORITATIVE",
    "SUPPORTED",
    "ADVISORY",
    "SPECULATIVE",
    "INVALID",
    "SUPERSEDED",
)
RULE_REVIEW_STATES = (
    "UNREVIEWED",
    "IN_REVIEW",
    "APPROVED",
    "REJECTED",
    "SUPERSEDED",
)
RULE_RUNTIME_ROLES = ("EXPLANATORY", "ADVISORY", "BLOCKING")
RULE_SUPPORT_KINDS = (
    "PROPERTY_OBSERVATION",
    "LAB_OBSERVATION",
    "LAB_EXPERIMENT",
    "TEST_ARTIFACT",
    "NUMERICAL_MODEL",
)
B4_TABLES = (
    "lab_rule_groups",
    "lab_rule_group_members",
    "lab_knowledge_rules",
    "lab_rule_contradictions",
    "lab_rule_support_evidence",
    "lab_rule_compilation_runs",
)


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _record_columns() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def _endpoint_shape(prefix: str) -> str:
    kind = f"{prefix}_kind"
    identity = f"{prefix}_identity_scope_sha256"
    group = f"{prefix}_group_id"
    label = f"{prefix}_raw_label"
    return (
        "("
        f"({kind} = 'EXACT_IDENTITY' AND {identity} IS NOT NULL "
        f"AND length({identity}) = 64 AND {group} IS NULL "
        f"AND length({label}) > 0) OR "
        f"({kind} = 'GROUP' AND {identity} IS NULL AND {group} IS NOT NULL "
        f"AND length({label}) > 0) OR "
        f"({kind} IN ('GENERIC_PROSE', 'UNRESOLVED') AND {identity} IS NULL "
        f"AND {group} IS NULL AND length({label}) > 0)"
        ")"
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
        "lab_rule_groups",
        *_record_columns(),
        sa.Column("group_key", sa.String(length=255), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("definition", sa.Text(), nullable=False),
        sa.Column(
            "source_document_version_id",
            sa.String(length=36),
        ),
        sa.Column("source_extraction_id", sa.String(length=36)),
        sa.Column("source_locator", sa.Text()),
        sa.Column("review_state", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("supersedes_group_id", sa.String(length=36)),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_lab_rule_group_version",
        ),
        sa.CheckConstraint(
            f"status IN ({_quoted(RULE_STATUSES)})",
            name="ck_lab_rule_group_status",
        ),
        sa.CheckConstraint(
            f"review_state IN ({_quoted(RULE_REVIEW_STATES)})",
            name="ck_lab_rule_group_review_state",
        ),
        sa.CheckConstraint(
            "status <> 'AUTHORITATIVE' OR ("
            "source_document_version_id IS NOT NULL "
            "AND source_extraction_id IS NOT NULL "
            "AND source_locator IS NOT NULL "
            "AND length(source_locator) > 0 "
            "AND review_state = 'APPROVED'"
            ")",
            name="ck_lab_rule_group_authority",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_rule_group_content_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["source_document_version_id"],
            ["lab_source_document_versions.id"],
            ondelete="RESTRICT",
            name="fk_lab_rule_group_source_version",
        ),
        sa.ForeignKeyConstraint(
            ["source_extraction_id"],
            ["lab_source_extraction_records.id"],
            ondelete="RESTRICT",
            name="fk_lab_rule_group_extraction",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_group_id"],
            ["lab_rule_groups.id"],
            ondelete="RESTRICT",
            name="fk_lab_rule_group_supersedes",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "group_key",
            "version",
            name="uq_lab_rule_group_key_version",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_rule_group_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_rule_groups_group_key",
        "lab_rule_groups",
        ["group_key"],
        unique=False,
    )

    op.create_table(
        "lab_rule_group_members",
        *_record_columns(),
        sa.Column("group_id", sa.String(length=36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("identity_scope_sha256", sa.String(length=64)),
        sa.Column("nested_group_id", sa.String(length=36)),
        sa.Column("member_role", sa.Text()),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "position >= 1",
            name="ck_lab_rule_group_member_position",
        ),
        sa.CheckConstraint(
            "("
            "(identity_scope_sha256 IS NOT NULL AND nested_group_id IS NULL) OR "
            "(identity_scope_sha256 IS NULL AND nested_group_id IS NOT NULL)"
            ")",
            name="ck_lab_rule_group_member_shape",
        ),
        sa.CheckConstraint(
            "identity_scope_sha256 IS NULL OR "
            "length(identity_scope_sha256) = 64",
            name="ck_lab_rule_group_member_identity_sha256",
        ),
        sa.CheckConstraint(
            "nested_group_id IS NULL OR nested_group_id <> group_id",
            name="ck_lab_rule_group_member_not_self",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_rule_group_member_content_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["lab_rule_groups.id"],
            ondelete="RESTRICT",
            name="fk_lab_rule_group_member_group",
        ),
        sa.ForeignKeyConstraint(
            ["nested_group_id"],
            ["lab_rule_groups.id"],
            ondelete="RESTRICT",
            name="fk_lab_rule_group_member_nested_group",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "group_id",
            "position",
            name="uq_lab_rule_group_member_position",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_rule_group_member_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_rule_group_members_group_id",
        "lab_rule_group_members",
        ["group_id"],
        unique=False,
    )

    op.create_table(
        "lab_knowledge_rules",
        *_record_columns(),
        sa.Column("rule_key", sa.String(length=255), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("subject_kind", sa.String(length=40), nullable=False),
        sa.Column("subject_raw_label", sa.Text(), nullable=False),
        sa.Column("subject_identity_scope_sha256", sa.String(length=64)),
        sa.Column("subject_group_id", sa.String(length=36)),
        sa.Column("relation", sa.String(length=60), nullable=False),
        sa.Column("object_kind", sa.String(length=40), nullable=False),
        sa.Column("object_raw_label", sa.Text(), nullable=False),
        sa.Column("object_identity_scope_sha256", sa.String(length=64)),
        sa.Column("object_group_id", sa.String(length=36)),
        sa.Column("directionality", sa.String(length=40), nullable=False),
        sa.Column("matrix_context_json", sa.JSON(), nullable=False),
        sa.Column("dose_domain_json", sa.JSON(), nullable=False),
        sa.Column("temporal_domain_json", sa.JSON(), nullable=False),
        sa.Column("expected_effect_json", sa.JSON(), nullable=False),
        sa.Column("attribute", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("source_document_version_id", sa.String(length=36)),
        sa.Column("source_extraction_id", sa.String(length=36)),
        sa.Column("source_locator", sa.Text(), nullable=False),
        sa.Column("evidence_class", sa.String(length=80), nullable=False),
        sa.Column("uncertainty_json", sa.JSON(), nullable=False),
        sa.Column("review_state", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("runtime_role", sa.String(length=40), nullable=False),
        sa.Column("numerical_model_ref", sa.Text()),
        sa.Column("supersedes_rule_id", sa.String(length=36)),
        sa.Column("raw_source_path", sa.Text(), nullable=False),
        sa.Column("raw_json_pointer", sa.Text(), nullable=False),
        sa.Column("raw_payload_sha256", sa.String(length=64), nullable=False),
        sa.Column("compiler_diagnostics_json", sa.JSON(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_lab_knowledge_rule_version",
        ),
        sa.CheckConstraint(
            f"subject_kind IN ({_quoted(RULE_ENDPOINT_KINDS)})",
            name="ck_lab_knowledge_rule_subject_kind",
        ),
        sa.CheckConstraint(
            f"object_kind IN ({_quoted(RULE_ENDPOINT_KINDS)})",
            name="ck_lab_knowledge_rule_object_kind",
        ),
        sa.CheckConstraint(
            _endpoint_shape("subject"),
            name="ck_lab_knowledge_rule_subject_shape",
        ),
        sa.CheckConstraint(
            _endpoint_shape("object"),
            name="ck_lab_knowledge_rule_object_shape",
        ),
        sa.CheckConstraint(
            f"relation IN ({_quoted(RULE_RELATIONS)})",
            name="ck_lab_knowledge_rule_relation",
        ),
        sa.CheckConstraint(
            f"directionality IN ({_quoted(RULE_DIRECTIONALITIES)})",
            name="ck_lab_knowledge_rule_directionality",
        ),
        sa.CheckConstraint(
            f"status IN ({_quoted(RULE_STATUSES)})",
            name="ck_lab_knowledge_rule_status",
        ),
        sa.CheckConstraint(
            f"review_state IN ({_quoted(RULE_REVIEW_STATES)})",
            name="ck_lab_knowledge_rule_review_state",
        ),
        sa.CheckConstraint(
            "status <> 'AUTHORITATIVE' OR ("
            "source_document_version_id IS NOT NULL "
            "AND source_extraction_id IS NOT NULL "
            "AND length(source_locator) > 0 "
            "AND review_state = 'APPROVED'"
            ")",
            name="ck_lab_knowledge_rule_authority_scope",
        ),
        sa.CheckConstraint(
            f"runtime_role IN ({_quoted(RULE_RUNTIME_ROLES)})",
            name="ck_lab_knowledge_rule_runtime_role",
        ),
        sa.CheckConstraint(
            "runtime_role <> 'BLOCKING' OR status = 'AUTHORITATIVE'",
            name="ck_lab_knowledge_rule_blocking_authority",
        ),
        sa.CheckConstraint(
            "("
            "subject_kind NOT IN ('GENERIC_PROSE', 'UNRESOLVED') "
            "AND object_kind NOT IN ('GENERIC_PROSE', 'UNRESOLVED')"
            ") OR (runtime_role <> 'BLOCKING' AND status <> 'AUTHORITATIVE' "
            "AND numerical_model_ref IS NULL)",
            name="ck_lab_knowledge_rule_generic_nonblocking",
        ),
        sa.CheckConstraint(
            "length(raw_source_path) > 0 AND length(raw_json_pointer) > 0",
            name="ck_lab_knowledge_rule_raw_locator",
        ),
        sa.CheckConstraint(
            "length(raw_payload_sha256) = 64",
            name="ck_lab_knowledge_rule_payload_sha256",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_knowledge_rule_content_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["subject_group_id"],
            ["lab_rule_groups.id"],
            ondelete="RESTRICT",
            name="fk_lab_knowledge_rule_subject_group",
        ),
        sa.ForeignKeyConstraint(
            ["object_group_id"],
            ["lab_rule_groups.id"],
            ondelete="RESTRICT",
            name="fk_lab_knowledge_rule_object_group",
        ),
        sa.ForeignKeyConstraint(
            ["source_document_version_id"],
            ["lab_source_document_versions.id"],
            ondelete="RESTRICT",
            name="fk_lab_knowledge_rule_source_version",
        ),
        sa.ForeignKeyConstraint(
            ["source_extraction_id"],
            ["lab_source_extraction_records.id"],
            ondelete="RESTRICT",
            name="fk_lab_knowledge_rule_extraction",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_rule_id"],
            ["lab_knowledge_rules.id"],
            ondelete="RESTRICT",
            name="fk_lab_knowledge_rule_supersedes",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "rule_key",
            "version",
            name="uq_lab_knowledge_rule_key_version",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_knowledge_rule_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_knowledge_rules_rule_key",
        "lab_knowledge_rules",
        ["rule_key"],
        unique=False,
    )
    op.create_index(
        "ix_lab_knowledge_rules_status",
        "lab_knowledge_rules",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_lab_knowledge_rules_subject_identity",
        "lab_knowledge_rules",
        ["subject_identity_scope_sha256"],
        unique=False,
    )
    op.create_index(
        "ix_lab_knowledge_rules_object_identity",
        "lab_knowledge_rules",
        ["object_identity_scope_sha256"],
        unique=False,
    )

    op.create_table(
        "lab_rule_contradictions",
        *_record_columns(),
        sa.Column("rule_id", sa.String(length=36), nullable=False),
        sa.Column(
            "contradictory_rule_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column("reason_code", sa.String(length=80), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("blocking", sa.Boolean(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "rule_id <> contradictory_rule_id",
            name="ck_lab_rule_contradiction_distinct",
        ),
        sa.CheckConstraint(
            "rule_id < contradictory_rule_id",
            name="ck_lab_rule_contradiction_ordered",
        ),
        sa.CheckConstraint(
            "length(reason_code) > 0",
            name="ck_lab_rule_contradiction_reason",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_rule_contradiction_content_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["rule_id"],
            ["lab_knowledge_rules.id"],
            ondelete="RESTRICT",
            name="fk_lab_rule_contradiction_rule",
        ),
        sa.ForeignKeyConstraint(
            ["contradictory_rule_id"],
            ["lab_knowledge_rules.id"],
            ondelete="RESTRICT",
            name="fk_lab_rule_contradiction_other_rule",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "rule_id",
            "contradictory_rule_id",
            "reason_code",
            name="uq_lab_rule_contradiction_pair_reason",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_rule_contradiction_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_rule_contradictions_rule_id",
        "lab_rule_contradictions",
        ["rule_id"],
        unique=False,
    )

    op.create_table(
        "lab_rule_support_evidence",
        *_record_columns(),
        sa.Column("rule_id", sa.String(length=36), nullable=False),
        sa.Column("support_kind", sa.String(length=40), nullable=False),
        sa.Column("reference_id", sa.Text(), nullable=False),
        sa.Column("controlled", sa.Boolean(), nullable=False),
        sa.Column("matrix_context_sha256", sa.String(length=64)),
        sa.Column("dose_domain_sha256", sa.String(length=64)),
        sa.Column("uncertainty_json", sa.JSON(), nullable=False),
        sa.Column("review_state", sa.String(length=40), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            f"support_kind IN ({_quoted(RULE_SUPPORT_KINDS)})",
            name="ck_lab_rule_support_kind",
        ),
        sa.CheckConstraint(
            "length(reference_id) > 0",
            name="ck_lab_rule_support_reference",
        ),
        sa.CheckConstraint(
            "("
            "(matrix_context_sha256 IS NULL AND dose_domain_sha256 IS NULL) OR "
            "(length(matrix_context_sha256) = 64 "
            "AND length(dose_domain_sha256) = 64)"
            ")",
            name="ck_lab_rule_support_context_hashes",
        ),
        sa.CheckConstraint(
            f"review_state IN ({_quoted(RULE_REVIEW_STATES)})",
            name="ck_lab_rule_support_review_state",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_rule_support_content_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["rule_id"],
            ["lab_knowledge_rules.id"],
            ondelete="RESTRICT",
            name="fk_lab_rule_support_rule",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_rule_support_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_rule_support_evidence_rule_id",
        "lab_rule_support_evidence",
        ["rule_id"],
        unique=False,
    )

    op.create_table(
        "lab_rule_compilation_runs",
        *_record_columns(),
        sa.Column("compiler_version", sa.String(length=80), nullable=False),
        sa.Column("source_manifest_json", sa.JSON(), nullable=False),
        sa.Column("source_corpus_sha256", sa.String(length=64), nullable=False),
        sa.Column("source_record_count", sa.Integer(), nullable=False),
        sa.Column("compiled_rule_count", sa.Integer(), nullable=False),
        sa.Column("invalid_exact_count", sa.Integer(), nullable=False),
        sa.Column("duplicate_count", sa.Integer(), nullable=False),
        sa.Column("contradiction_count", sa.Integer(), nullable=False),
        sa.Column("cycle_count", sa.Integer(), nullable=False),
        sa.Column("orphan_count", sa.Integer(), nullable=False),
        sa.Column("generic_count", sa.Integer(), nullable=False),
        sa.Column(
            "baseline_invalid_exact_count",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("report_sha256", sa.String(length=64), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "source_record_count >= 0 AND compiled_rule_count >= 0 "
            "AND invalid_exact_count >= 0 AND duplicate_count >= 0 "
            "AND contradiction_count >= 0 AND cycle_count >= 0 "
            "AND orphan_count >= 0 AND generic_count >= 0",
            name="ck_lab_rule_compilation_counts",
        ),
        sa.CheckConstraint(
            "baseline_invalid_exact_count >= 0 AND "
            "(passed = 0 OR invalid_exact_count <= baseline_invalid_exact_count)",
            name="ck_lab_rule_compilation_baseline",
        ),
        sa.CheckConstraint(
            "length(source_corpus_sha256) = 64 "
            "AND length(report_sha256) = 64 "
            "AND length(content_sha256) = 64",
            name="ck_lab_rule_compilation_hashes",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_rule_compilation_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_rule_compilation_runs_source_corpus_sha256",
        "lab_rule_compilation_runs",
        ["source_corpus_sha256"],
        unique=False,
    )

    for table_name in B4_TABLES:
        _create_append_only_triggers(table_name)


def downgrade() -> None:
    for table_name in reversed(B4_TABLES):
        _drop_append_only_triggers(table_name)

    op.drop_index(
        "ix_lab_rule_compilation_runs_source_corpus_sha256",
        table_name="lab_rule_compilation_runs",
    )
    op.drop_table("lab_rule_compilation_runs")

    op.drop_index(
        "ix_lab_rule_support_evidence_rule_id",
        table_name="lab_rule_support_evidence",
    )
    op.drop_table("lab_rule_support_evidence")

    op.drop_index(
        "ix_lab_rule_contradictions_rule_id",
        table_name="lab_rule_contradictions",
    )
    op.drop_table("lab_rule_contradictions")

    op.drop_index(
        "ix_lab_knowledge_rules_object_identity",
        table_name="lab_knowledge_rules",
    )
    op.drop_index(
        "ix_lab_knowledge_rules_subject_identity",
        table_name="lab_knowledge_rules",
    )
    op.drop_index(
        "ix_lab_knowledge_rules_status",
        table_name="lab_knowledge_rules",
    )
    op.drop_index(
        "ix_lab_knowledge_rules_rule_key",
        table_name="lab_knowledge_rules",
    )
    op.drop_table("lab_knowledge_rules")

    op.drop_index(
        "ix_lab_rule_group_members_group_id",
        table_name="lab_rule_group_members",
    )
    op.drop_table("lab_rule_group_members")

    op.drop_index(
        "ix_lab_rule_groups_group_key",
        table_name="lab_rule_groups",
    )
    op.drop_table("lab_rule_groups")
