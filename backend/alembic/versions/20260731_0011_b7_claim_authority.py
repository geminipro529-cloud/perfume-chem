"""Build B7 append-only claim-specific scientific authority.

Revision ID: 20260731_0011
Revises: 20260731_0010
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260731_0011"
down_revision: str | None = "20260731_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CLAIM_AUTHORITY_TYPES = (
    "EXACT_CHEMICAL_IDENTITY",
    "GRADE_IDENTITY",
    "PROPERTY_VALUE",
    "THRESHOLD",
    "ABOVE_THRESHOLD_SCREENING",
    "ANALYTICAL_IDENTIFICATION",
    "ANALYTICAL_QUANTITATION",
    "NATURAL_CONSTITUENT_PROFILE",
    "KNOWLEDGE_RULE_RECOMMENDATION",
    "REGULATORY_SCREENING",
    "FORMULA_OR_MODEL_COMPARISON",
)
CLAIM_AUTHORITY_DECISIONS = (
    "ALLOW_EXACT",
    "ALLOW_SCOPED",
    "ADVISORY_ONLY",
    "WITHHOLD_UNKNOWN",
    "BLOCK",
)
CLAIM_AUTHORITY_SUPPORT_ROLES = (
    "SUPPORTING",
    "CONTRADICTING",
    "LIMITATION",
)
CLAIM_AUTHORITY_SUPPORT_KINDS = (
    "PROPERTY_ASSERTION",
    "OAV_ASSESSMENT",
    "KNOWLEDGE_RULE",
    "ANALYTICAL_ASSESSMENT",
    "COMPOSITION_PROFILE",
    "REGULATORY_SNAPSHOT",
)
B7_TABLES = (
    "lab_claim_authority_versions",
    "lab_claim_authority_support_links",
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
        "lab_claim_authority_versions",
        *_record_columns(),
        sa.Column("authority_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("parent_version_id", sa.String(length=36), nullable=True),
        sa.Column(
            "legacy_claim_assessment_version_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column("schema_version", sa.String(length=80), nullable=False),
        sa.Column("policy_version", sa.String(length=100), nullable=False),
        sa.Column("policy_sha256", sa.String(length=64), nullable=False),
        _json_object("policy_json"),
        sa.Column("claim_type", sa.String(length=80), nullable=False),
        sa.Column("subject_type", sa.String(length=40), nullable=False),
        sa.Column("subject_id", sa.String(length=36), nullable=False),
        _json_object("claim_payload_json"),
        _json_object("identity_scope_json"),
        sa.Column(
            "identity_scope_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        _json_object("condition_scope_json"),
        sa.Column(
            "condition_scope_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("claim_scope_sha256", sa.String(length=64), nullable=False),
        sa.Column("decision", sa.String(length=40), nullable=False),
        _json_object("dimension_results_json"),
        _json_array("supporting_observations_json"),
        _json_array("conflicts_json"),
        _json_array("missing_requirements_json"),
        _json_array("source_references_json"),
        _json_object("uncertainty_json"),
        sa.Column("permitted_wording", sa.Text(), nullable=False),
        sa.Column("forbidden_wording", sa.Text(), nullable=False),
        sa.Column("blocker_count", sa.Integer(), nullable=False),
        sa.Column("conflict_count", sa.Integer(), nullable=False),
        sa.Column("missing_requirement_count", sa.Integer(), nullable=False),
        sa.Column("critical_unknown_count", sa.Integer(), nullable=False),
        sa.Column("support_count", sa.Integer(), nullable=False),
        sa.Column("source_reference_count", sa.Integer(), nullable=False),
        sa.Column(
            "release_authority",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        _json_object("upstream_hashes_json"),
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
        sa.Column("parent_sha256", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "version_number >= 1",
            name="ck_lab_claim_authority_version_positive",
        ),
        sa.CheckConstraint(
            "(version_number = 1 AND parent_version_id IS NULL "
            "AND parent_sha256 IS NULL) OR "
            "(version_number > 1 AND parent_version_id IS NOT NULL "
            "AND length(parent_sha256) = 64)",
            name="ck_lab_claim_authority_version_chain",
        ),
        sa.CheckConstraint(
            f"claim_type IN ({_quoted(CLAIM_AUTHORITY_TYPES)})",
            name="ck_lab_claim_authority_type",
        ),
        sa.CheckConstraint(
            f"decision IN ({_quoted(CLAIM_AUTHORITY_DECISIONS)})",
            name="ck_lab_claim_authority_decision",
        ),
        sa.CheckConstraint(
            "blocker_count >= 0 AND conflict_count >= 0 "
            "AND missing_requirement_count >= 0 "
            "AND critical_unknown_count >= 0 AND support_count >= 0 "
            "AND source_reference_count >= 0",
            name="ck_lab_claim_authority_counts",
        ),
        sa.CheckConstraint(
            "decision <> 'ALLOW_EXACT' OR ("
            "blocker_count = 0 AND conflict_count = 0 "
            "AND missing_requirement_count = 0 "
            "AND critical_unknown_count = 0 AND support_count >= 1 "
            "AND source_reference_count >= 1 "
            "AND length(trim(permitted_wording)) > 0)",
            name="ck_lab_claim_authority_exact_shape",
        ),
        sa.CheckConstraint(
            "decision <> 'ALLOW_SCOPED' OR ("
            "blocker_count = 0 AND conflict_count = 0 "
            "AND critical_unknown_count = 0 AND support_count >= 1 "
            "AND length(trim(permitted_wording)) > 0)",
            name="ck_lab_claim_authority_scoped_shape",
        ),
        sa.CheckConstraint(
            "decision <> 'WITHHOLD_UNKNOWN' OR ("
            "missing_requirement_count > 0 OR critical_unknown_count > 0)",
            name="ck_lab_claim_authority_withheld_shape",
        ),
        sa.CheckConstraint(
            "decision <> 'BLOCK' OR blocker_count > 0",
            name="ck_lab_claim_authority_block_shape",
        ),
        sa.CheckConstraint(
            "release_authority = 0",
            name="ck_lab_claim_authority_no_release",
        ),
        sa.CheckConstraint(
            "length(trim(reviewer_pseudonym)) > 0 "
            "AND reviewed_at IS NOT NULL",
            name="ck_lab_claim_authority_review",
        ),
        sa.CheckConstraint(
            "length(policy_sha256) = 64",
            name="ck_lab_claim_authority_policy_sha256",
        ),
        sa.CheckConstraint(
            "length(identity_scope_sha256) = 64",
            name="ck_lab_claim_authority_identity_sha256",
        ),
        sa.CheckConstraint(
            "length(condition_scope_sha256) = 64",
            name="ck_lab_claim_authority_condition_sha256",
        ),
        sa.CheckConstraint(
            "length(claim_scope_sha256) = 64",
            name="ck_lab_claim_authority_scope_sha256",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_claim_authority_content_sha256",
        ),
        sa.CheckConstraint(
            "parent_sha256 IS NULL OR length(parent_sha256) = 64",
            name="ck_lab_claim_authority_parent_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["parent_version_id"],
            ["lab_claim_authority_versions.id"],
            name="fk_lab_claim_authority_parent",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["legacy_claim_assessment_version_id"],
            ["lab_claim_assessment_versions.id"],
            name="fk_lab_claim_authority_legacy_assessment",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "authority_id",
            "version_number",
            name="uq_lab_claim_authority_version",
        ),
        sa.UniqueConstraint(
            "parent_version_id",
            name="uq_lab_claim_authority_parent",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_claim_authority_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_claim_authority_claim_scope",
        "lab_claim_authority_versions",
        ["claim_type", "claim_scope_sha256", "decision"],
        unique=False,
    )
    op.create_index(
        "ix_lab_claim_authority_subject",
        "lab_claim_authority_versions",
        ["subject_type", "subject_id"],
        unique=False,
    )

    op.create_table(
        "lab_claim_authority_support_links",
        *_record_columns(),
        sa.Column(
            "claim_authority_version_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column("support_kind", sa.String(length=40), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column(
            "property_assertion_id",
            sa.String(length=36),
            nullable=True,
        ),
        sa.Column(
            "oav_assessment_id",
            sa.String(length=36),
            nullable=True,
        ),
        sa.Column(
            "knowledge_rule_id",
            sa.String(length=36),
            nullable=True,
        ),
        sa.Column(
            "analytical_assessment_id",
            sa.String(length=36),
            nullable=True,
        ),
        sa.Column(
            "composition_profile_id",
            sa.String(length=36),
            nullable=True,
        ),
        sa.Column(
            "regulatory_snapshot_version_id",
            sa.String(length=36),
            nullable=True,
        ),
        sa.Column(
            "upstream_content_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        _json_object("derived_facts_json"),
        _json_array("source_references_json"),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            f"support_kind IN ({_quoted(CLAIM_AUTHORITY_SUPPORT_KINDS)})",
            name="ck_lab_claim_authority_support_kind",
        ),
        sa.CheckConstraint(
            f"role IN ({_quoted(CLAIM_AUTHORITY_SUPPORT_ROLES)})",
            name="ck_lab_claim_authority_support_role",
        ),
        sa.CheckConstraint(
            "("
            "(support_kind = 'PROPERTY_ASSERTION' "
            "AND property_assertion_id IS NOT NULL "
            "AND oav_assessment_id IS NULL "
            "AND knowledge_rule_id IS NULL "
            "AND analytical_assessment_id IS NULL "
            "AND composition_profile_id IS NULL "
            "AND regulatory_snapshot_version_id IS NULL) OR "
            "(support_kind = 'OAV_ASSESSMENT' "
            "AND property_assertion_id IS NULL "
            "AND oav_assessment_id IS NOT NULL "
            "AND knowledge_rule_id IS NULL "
            "AND analytical_assessment_id IS NULL "
            "AND composition_profile_id IS NULL "
            "AND regulatory_snapshot_version_id IS NULL) OR "
            "(support_kind = 'KNOWLEDGE_RULE' "
            "AND property_assertion_id IS NULL "
            "AND oav_assessment_id IS NULL "
            "AND knowledge_rule_id IS NOT NULL "
            "AND analytical_assessment_id IS NULL "
            "AND composition_profile_id IS NULL "
            "AND regulatory_snapshot_version_id IS NULL) OR "
            "(support_kind = 'ANALYTICAL_ASSESSMENT' "
            "AND property_assertion_id IS NULL "
            "AND oav_assessment_id IS NULL "
            "AND knowledge_rule_id IS NULL "
            "AND analytical_assessment_id IS NOT NULL "
            "AND composition_profile_id IS NULL "
            "AND regulatory_snapshot_version_id IS NULL) OR "
            "(support_kind = 'COMPOSITION_PROFILE' "
            "AND property_assertion_id IS NULL "
            "AND oav_assessment_id IS NULL "
            "AND knowledge_rule_id IS NULL "
            "AND analytical_assessment_id IS NULL "
            "AND composition_profile_id IS NOT NULL "
            "AND regulatory_snapshot_version_id IS NULL) OR "
            "(support_kind = 'REGULATORY_SNAPSHOT' "
            "AND property_assertion_id IS NULL "
            "AND oav_assessment_id IS NULL "
            "AND knowledge_rule_id IS NULL "
            "AND analytical_assessment_id IS NULL "
            "AND composition_profile_id IS NULL "
            "AND regulatory_snapshot_version_id IS NOT NULL)"
            ")",
            name="ck_lab_claim_authority_support_shape",
        ),
        sa.CheckConstraint(
            "length(upstream_content_sha256) = 64",
            name="ck_lab_claim_authority_support_upstream_sha256",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_claim_authority_support_content_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["claim_authority_version_id"],
            ["lab_claim_authority_versions.id"],
            name="fk_lab_claim_authority_support_authority",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["property_assertion_id"],
            ["lab_selected_assertions.id"],
            name="fk_lab_claim_authority_support_property",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["oav_assessment_id"],
            ["lab_oav_assessments.id"],
            name="fk_lab_claim_authority_support_oav",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_rule_id"],
            ["lab_knowledge_rules.id"],
            name="fk_lab_claim_authority_support_rule",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["analytical_assessment_id"],
            ["lab_analytical_claim_assessments.id"],
            name="fk_lab_claim_authority_support_analytical",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["composition_profile_id"],
            ["lab_regulatory_composition_profiles.id"],
            name="fk_lab_claim_authority_support_composition",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["regulatory_snapshot_version_id"],
            ["lab_regulatory_snapshot_versions.id"],
            name="fk_lab_claim_authority_support_regulatory",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_claim_authority_support_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_claim_authority_support_authority",
        "lab_claim_authority_support_links",
        ["claim_authority_version_id"],
        unique=False,
    )
    op.create_index(
        "ix_lab_claim_authority_support_kind",
        "lab_claim_authority_support_links",
        ["support_kind"],
        unique=False,
    )

    for table_name in B7_TABLES:
        _create_append_only_triggers(table_name)


def downgrade() -> None:
    for table_name in reversed(B7_TABLES):
        _drop_append_only_triggers(table_name)

    op.drop_index(
        "ix_lab_claim_authority_support_kind",
        table_name="lab_claim_authority_support_links",
    )
    op.drop_index(
        "ix_lab_claim_authority_support_authority",
        table_name="lab_claim_authority_support_links",
    )
    op.drop_table("lab_claim_authority_support_links")

    op.drop_index(
        "ix_lab_claim_authority_subject",
        table_name="lab_claim_authority_versions",
    )
    op.drop_index(
        "ix_lab_claim_authority_claim_scope",
        table_name="lab_claim_authority_versions",
    )
    op.drop_table("lab_claim_authority_versions")
