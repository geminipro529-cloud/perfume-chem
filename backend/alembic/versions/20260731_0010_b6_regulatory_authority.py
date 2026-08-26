"""Build B6 append-only safety and regulatory screening authority.

Revision ID: 20260731_0010
Revises: 20260731_0009
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260731_0010"
down_revision: str | None = "20260731_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REGULATORY_SOURCE_STATUSES = (
    "CURRENT_ENFORCED_OR_FORMALLY_NOTIFIED",
    "FUTURE_EFFECTIVE",
    "DRAFT",
    "CONSULTATION",
    "WATCHLIST",
    "SUPERSEDED",
)
REGULATORY_RESULT_STATES = (
    "PASS_FOR_DECLARED_SCOPE",
    "FAIL",
    "UNKNOWN",
    "NOT_EVALUATED",
)
REGULATORY_AUTHORITY_FAMILIES = (
    "IFRA_STANDARD",
    "JURISDICTIONAL_LEGISLATION",
    "OFFICIAL_GUIDANCE",
)
REGULATORY_RULE_FAMILIES = (
    "IFRA_RESTRICTION",
    "LEGAL_RESTRICTION",
    "ALLERGEN_LABELING",
)
REGULATORY_RULE_KINDS = (
    "MAXIMUM_FINISHED_FRACTION",
    "DECLARATION_THRESHOLD",
)
SUPPLIER_DOCUMENT_SCOPES = ("SUPPLIER_PRODUCT", "SUPPLIER_LOT")
SUPPLIER_REGULATORY_DOCUMENT_TYPES = (
    "SUPPLIER_COA",
    "SUPPLIER_SPECIFICATION",
    "SUPPLIER_SDS",
    "SUPPLIER_IFRA_CERTIFICATE",
    "SUPPLIER_ALLERGEN_DECLARATION",
)
REGULATORY_COMPOSITION_ORIGINS = ("SYNTHETIC", "NATURAL", "TRADE_GRADE")
REGULATORY_COMPOSITION_BASES = (
    "LOT_SPECIFIC",
    "DOCUMENTED_PROXY",
    "UNKNOWN",
)
REGULATORY_COMPOSITION_COMPLETENESS = ("COMPLETE", "PARTIAL", "UNKNOWN")
REGULATORY_SUBJECT_TYPES = ("FORMULA_VERSION", "BUILD_PLAN_VERSION")
REGULATORY_MARKET_ACTIONS = (
    "PLACE_ON_MARKET",
    "MAKE_AVAILABLE",
    "INTERNAL_SCREENING",
)
B6_TABLES = (
    "lab_regulatory_source_versions",
    "lab_regulatory_rule_versions",
    "lab_supplier_document_bindings",
    "lab_regulatory_composition_profiles",
    "lab_regulatory_composition_entries",
    "lab_regulatory_snapshot_versions",
    "lab_regulatory_authority_findings",
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
        "lab_regulatory_source_versions",
        *_record_columns(),
        sa.Column("authority_id", sa.String(length=36), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("parent_version_id", sa.String(length=36), nullable=True),
        sa.Column("schema_version", sa.String(length=80), nullable=False),
        sa.Column("authority_family", sa.String(length=60), nullable=False),
        sa.Column("identifier", sa.Text(), nullable=False),
        sa.Column("published_version", sa.String(length=100), nullable=False),
        sa.Column("jurisdiction", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.Column("notified_on", sa.Date(), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_through", sa.Date(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "supersedes_source_version_id",
            sa.String(length=36),
            nullable=True,
        ),
        sa.Column(
            "official_source_document_version_id",
            sa.String(length=36),
            nullable=False,
        ),
        _json_object("source_locator_json"),
        sa.Column(
            "official_source_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        _json_object("notes_json"),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "revision_number >= 1",
            name="ck_lab_regulatory_source_version_positive",
        ),
        sa.CheckConstraint(
            f"authority_family IN ({_quoted(REGULATORY_AUTHORITY_FAMILIES)})",
            name="ck_lab_regulatory_source_family",
        ),
        sa.CheckConstraint(
            f"status IN ({_quoted(REGULATORY_SOURCE_STATUSES)})",
            name="ck_lab_regulatory_source_status",
        ),
        sa.CheckConstraint(
            "effective_through IS NULL OR effective_from IS NULL "
            "OR effective_through >= effective_from",
            name="ck_lab_regulatory_source_date_range",
        ),
        sa.CheckConstraint(
            "length(official_source_sha256) = 64",
            name="ck_lab_regulatory_source_official_sha256",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_regulatory_source_content_sha256",
        ),
        sa.CheckConstraint(
            "(revision_number = 1 AND parent_version_id IS NULL) OR "
            "(revision_number > 1 AND parent_version_id IS NOT NULL)",
            name="ck_lab_regulatory_source_version_chain",
        ),
        sa.ForeignKeyConstraint(
            ["parent_version_id"],
            ["lab_regulatory_source_versions.id"],
            ondelete="RESTRICT",
            name="fk_lab_regulatory_source_parent",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_source_version_id"],
            ["lab_regulatory_source_versions.id"],
            ondelete="RESTRICT",
            name="fk_lab_regulatory_source_supersedes",
        ),
        sa.ForeignKeyConstraint(
            ["official_source_document_version_id"],
            ["lab_source_document_versions.id"],
            ondelete="RESTRICT",
            name="fk_lab_regulatory_source_document",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "authority_id",
            "revision_number",
            name="uq_lab_regulatory_source_version",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_regulatory_source_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_regulatory_source_authority_status",
        "lab_regulatory_source_versions",
        ["authority_id", "status"],
        unique=False,
    )

    op.create_table(
        "lab_regulatory_rule_versions",
        *_record_columns(),
        sa.Column("rule_id", sa.String(length=36), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("parent_version_id", sa.String(length=36), nullable=True),
        sa.Column("schema_version", sa.String(length=80), nullable=False),
        sa.Column(
            "regulatory_source_version_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column("rule_family", sa.String(length=50), nullable=False),
        sa.Column("rule_identifier", sa.Text(), nullable=False),
        sa.Column("material_id", sa.String(length=36), nullable=True),
        sa.Column("substance_name", sa.Text(), nullable=False),
        sa.Column("cas_number", sa.String(length=50), nullable=True),
        sa.Column("jurisdiction", sa.String(length=100), nullable=False),
        sa.Column("product_category", sa.String(length=100), nullable=False),
        sa.Column("use_classification", sa.String(length=80), nullable=False),
        sa.Column("concentration_basis", sa.String(length=80), nullable=False),
        sa.Column("rule_kind", sa.String(length=50), nullable=False),
        sa.Column("threshold_fraction", sa.Float(), nullable=True),
        sa.Column("maximum_fraction", sa.Float(), nullable=True),
        sa.Column("declaration_wording", sa.Text(), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_through", sa.Date(), nullable=True),
        sa.Column("placement_transition_end", sa.Date(), nullable=True),
        sa.Column("availability_transition_end", sa.Date(), nullable=True),
        _json_object("transition_conditions_json"),
        _json_array("assumptions_json"),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "revision_number >= 1",
            name="ck_lab_regulatory_rule_version_positive",
        ),
        sa.CheckConstraint(
            "(revision_number = 1 AND parent_version_id IS NULL) OR "
            "(revision_number > 1 AND parent_version_id IS NOT NULL)",
            name="ck_lab_regulatory_rule_version_chain",
        ),
        sa.CheckConstraint(
            f"rule_family IN ({_quoted(REGULATORY_RULE_FAMILIES)})",
            name="ck_lab_regulatory_rule_family",
        ),
        sa.CheckConstraint(
            f"rule_kind IN ({_quoted(REGULATORY_RULE_KINDS)})",
            name="ck_lab_regulatory_rule_kind",
        ),
        sa.CheckConstraint(
            "(rule_kind = 'MAXIMUM_FINISHED_FRACTION' "
            "AND maximum_fraction IS NOT NULL "
            "AND threshold_fraction IS NULL "
            "AND declaration_wording IS NULL) OR "
            "(rule_kind = 'DECLARATION_THRESHOLD' "
            "AND threshold_fraction IS NOT NULL "
            "AND maximum_fraction IS NULL "
            "AND length(trim(declaration_wording)) > 0)",
            name="ck_lab_regulatory_rule_shape",
        ),
        sa.CheckConstraint(
            "(threshold_fraction IS NULL OR "
            "(threshold_fraction >= 0 AND threshold_fraction <= 1)) AND "
            "(maximum_fraction IS NULL OR "
            "(maximum_fraction >= 0 AND maximum_fraction <= 1))",
            name="ck_lab_regulatory_rule_fraction",
        ),
        sa.CheckConstraint(
            "effective_through IS NULL OR effective_from IS NULL "
            "OR effective_through >= effective_from",
            name="ck_lab_regulatory_rule_date_range",
        ),
        sa.CheckConstraint(
            "placement_transition_end IS NULL "
            "OR availability_transition_end IS NULL "
            "OR availability_transition_end >= placement_transition_end",
            name="ck_lab_regulatory_rule_transition_order",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_regulatory_rule_content_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["parent_version_id"],
            ["lab_regulatory_rule_versions.id"],
            ondelete="RESTRICT",
            name="fk_lab_regulatory_rule_parent",
        ),
        sa.ForeignKeyConstraint(
            ["regulatory_source_version_id"],
            ["lab_regulatory_source_versions.id"],
            ondelete="RESTRICT",
            name="fk_lab_regulatory_rule_source",
        ),
        sa.ForeignKeyConstraint(
            ["material_id"],
            ["lab_materials.id"],
            ondelete="RESTRICT",
            name="fk_lab_regulatory_rule_material",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "rule_id",
            "revision_number",
            name="uq_lab_regulatory_rule_version",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_regulatory_rule_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_regulatory_rule_source_family",
        "lab_regulatory_rule_versions",
        ["regulatory_source_version_id", "rule_family"],
        unique=False,
    )

    op.create_table(
        "lab_supplier_document_bindings",
        *_record_columns(),
        sa.Column("stock_solution_id", sa.String(length=36), nullable=False),
        sa.Column("scope", sa.String(length=40), nullable=False),
        sa.Column("supplier", sa.Text(), nullable=False),
        sa.Column("supplier_product", sa.Text(), nullable=False),
        sa.Column(
            "supplier_product_code",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column("grade", sa.String(length=100), nullable=False),
        sa.Column("document_type", sa.String(length=60), nullable=False),
        sa.Column("document_version", sa.String(length=100), nullable=False),
        sa.Column("lot_number", sa.String(length=100), nullable=True),
        sa.Column("effective_on", sa.Date(), nullable=False),
        sa.Column("expires_on", sa.Date(), nullable=True),
        sa.Column(
            "source_document_version_id",
            sa.String(length=36),
            nullable=False,
        ),
        _json_object("source_locator_json"),
        sa.Column(
            "source_artifact_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "supplier_identity_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            f"scope IN ({_quoted(SUPPLIER_DOCUMENT_SCOPES)})",
            name="ck_lab_supplier_document_scope",
        ),
        sa.CheckConstraint(
            "(scope = 'SUPPLIER_PRODUCT' AND lot_number IS NULL) OR "
            "(scope = 'SUPPLIER_LOT' AND length(trim(lot_number)) > 0)",
            name="ck_lab_supplier_document_scope_shape",
        ),
        sa.CheckConstraint(
            f"document_type IN "
            f"({_quoted(SUPPLIER_REGULATORY_DOCUMENT_TYPES)})",
            name="ck_lab_supplier_document_type",
        ),
        sa.CheckConstraint(
            "expires_on IS NULL OR expires_on >= effective_on",
            name="ck_lab_supplier_document_date_range",
        ),
        sa.CheckConstraint(
            "length(source_artifact_sha256) = 64",
            name="ck_lab_supplier_document_source_sha256",
        ),
        sa.CheckConstraint(
            "length(supplier_identity_sha256) = 64",
            name="ck_lab_supplier_document_identity_sha256",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_supplier_document_content_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["stock_solution_id"],
            ["lab_stock_solutions.id"],
            ondelete="RESTRICT",
            name="fk_lab_supplier_document_stock",
        ),
        sa.ForeignKeyConstraint(
            ["source_document_version_id"],
            ["lab_source_document_versions.id"],
            ondelete="RESTRICT",
            name="fk_lab_supplier_document_source",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_supplier_document_binding_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_supplier_document_stock_type",
        "lab_supplier_document_bindings",
        ["stock_solution_id", "document_type"],
        unique=False,
    )

    op.create_table(
        "lab_regulatory_composition_profiles",
        *_record_columns(),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("parent_version_id", sa.String(length=36), nullable=True),
        sa.Column("stock_solution_id", sa.String(length=36), nullable=False),
        sa.Column("schema_version", sa.String(length=80), nullable=False),
        sa.Column("origin", sa.String(length=40), nullable=False),
        sa.Column("composition_basis", sa.String(length=40), nullable=False),
        sa.Column("completeness", sa.String(length=40), nullable=False),
        sa.Column(
            "supplier_document_binding_id",
            sa.String(length=36),
            nullable=True,
        ),
        _json_array("assumptions_json"),
        _json_array("limitations_json"),
        sa.Column("reviewer_pseudonym", sa.Text(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "version_number >= 1",
            name="ck_lab_regulatory_composition_version_positive",
        ),
        sa.CheckConstraint(
            "(version_number = 1 AND parent_version_id IS NULL) OR "
            "(version_number > 1 AND parent_version_id IS NOT NULL)",
            name="ck_lab_regulatory_composition_version_chain",
        ),
        sa.CheckConstraint(
            f"origin IN ({_quoted(REGULATORY_COMPOSITION_ORIGINS)})",
            name="ck_lab_regulatory_composition_origin",
        ),
        sa.CheckConstraint(
            f"composition_basis IN "
            f"({_quoted(REGULATORY_COMPOSITION_BASES)})",
            name="ck_lab_regulatory_composition_basis",
        ),
        sa.CheckConstraint(
            f"completeness IN "
            f"({_quoted(REGULATORY_COMPOSITION_COMPLETENESS)})",
            name="ck_lab_regulatory_composition_completeness",
        ),
        sa.CheckConstraint(
            "(composition_basis = 'UNKNOWN' "
            "AND completeness = 'UNKNOWN' "
            "AND supplier_document_binding_id IS NULL) OR "
            "(composition_basis IN ('LOT_SPECIFIC', 'DOCUMENTED_PROXY') "
            "AND completeness IN ('COMPLETE', 'PARTIAL') "
            "AND supplier_document_binding_id IS NOT NULL)",
            name="ck_lab_regulatory_composition_shape",
        ),
        sa.CheckConstraint(
            "length(trim(reviewer_pseudonym)) > 0 AND reviewed_at IS NOT NULL",
            name="ck_lab_regulatory_composition_review",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_regulatory_composition_content_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["parent_version_id"],
            ["lab_regulatory_composition_profiles.id"],
            ondelete="RESTRICT",
            name="fk_lab_regulatory_composition_parent",
        ),
        sa.ForeignKeyConstraint(
            ["stock_solution_id"],
            ["lab_stock_solutions.id"],
            ondelete="RESTRICT",
            name="fk_lab_regulatory_composition_stock",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_document_binding_id"],
            ["lab_supplier_document_bindings.id"],
            ondelete="RESTRICT",
            name="fk_lab_regulatory_composition_supplier_document",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "profile_id",
            "version_number",
            name="uq_lab_regulatory_composition_profile_version",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_regulatory_composition_profile_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_regulatory_composition_stock",
        "lab_regulatory_composition_profiles",
        ["stock_solution_id", "version_number"],
        unique=False,
    )

    op.create_table(
        "lab_regulatory_composition_entries",
        *_record_columns(),
        sa.Column(
            "composition_profile_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "projection_family",
            sa.String(length=40),
            server_default=sa.text("'REGULATORY'"),
            nullable=False,
        ),
        sa.Column("material_id", sa.String(length=36), nullable=True),
        sa.Column("constituent_name", sa.Text(), nullable=False),
        sa.Column("cas_number", sa.String(length=50), nullable=True),
        sa.Column("fraction", sa.Float(), nullable=False),
        sa.Column("fraction_basis", sa.String(length=80), nullable=False),
        sa.Column("standard_uncertainty", sa.Float(), nullable=True),
        _json_object("source_locator_json"),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "position >= 1",
            name="ck_lab_regulatory_composition_entry_position",
        ),
        sa.CheckConstraint(
            "projection_family = 'REGULATORY'",
            name="ck_lab_regulatory_composition_entry_projection",
        ),
        sa.CheckConstraint(
            "fraction >= 0 AND fraction <= 1",
            name="ck_lab_regulatory_composition_entry_fraction",
        ),
        sa.CheckConstraint(
            "standard_uncertainty IS NULL OR standard_uncertainty >= 0",
            name="ck_lab_regulatory_composition_entry_uncertainty",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_regulatory_composition_entry_content_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["composition_profile_id"],
            ["lab_regulatory_composition_profiles.id"],
            ondelete="RESTRICT",
            name="fk_lab_regulatory_composition_entry_profile",
        ),
        sa.ForeignKeyConstraint(
            ["material_id"],
            ["lab_materials.id"],
            ondelete="RESTRICT",
            name="fk_lab_regulatory_composition_entry_material",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "composition_profile_id",
            "position",
            name="uq_lab_regulatory_composition_entry_position",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_regulatory_composition_entry_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_regulatory_composition_entries_composition_profile_id",
        "lab_regulatory_composition_entries",
        ["composition_profile_id"],
        unique=False,
    )

    op.create_table(
        "lab_regulatory_snapshot_versions",
        *_record_columns(),
        sa.Column("snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("parent_version_id", sa.String(length=36), nullable=True),
        sa.Column("schema_version", sa.String(length=80), nullable=False),
        sa.Column("subject_type", sa.String(length=40), nullable=False),
        sa.Column("subject_id", sa.String(length=36), nullable=False),
        sa.Column(
            "legacy_assessment_version_id",
            sa.String(length=36),
            nullable=True,
        ),
        sa.Column(
            "primary_source_version_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column("standard_identifier", sa.Text(), nullable=False),
        sa.Column("standard_version", sa.String(length=100), nullable=False),
        sa.Column(
            "official_source_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("jurisdiction", sa.String(length=100), nullable=False),
        sa.Column("product_category", sa.String(length=100), nullable=False),
        sa.Column("use_classification", sa.String(length=80), nullable=False),
        sa.Column(
            "finished_product_concentration",
            sa.Float(),
            nullable=False,
        ),
        sa.Column("constituent_basis", sa.String(length=80), nullable=False),
        _json_array("natural_material_assumptions_json"),
        sa.Column("effective_on", sa.Date(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "evaluator_software_version",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column("market_action", sa.String(length=40), nullable=False),
        sa.Column("market_action_on", sa.Date(), nullable=False),
        _json_array("current_state_source_ids_json"),
        _json_array("watch_source_ids_json"),
        _json_array("rule_version_ids_json"),
        _json_array("supplier_binding_ids_json"),
        _json_array("composition_profile_ids_json"),
        _json_object("upstream_hashes_json"),
        _json_array("unresolved_items_json"),
        _json_array("result_reasons_json"),
        sa.Column("result_state", sa.String(length=40), nullable=False),
        sa.Column("permitted_wording", sa.Text(), nullable=True),
        sa.Column("reviewer_pseudonym", sa.Text(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("parent_sha256", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "version_number >= 1",
            name="ck_lab_regulatory_snapshot_version_positive",
        ),
        sa.CheckConstraint(
            "(version_number = 1 AND parent_version_id IS NULL "
            "AND parent_sha256 IS NULL) OR "
            "(version_number > 1 AND parent_version_id IS NOT NULL "
            "AND length(parent_sha256) = 64)",
            name="ck_lab_regulatory_snapshot_version_chain",
        ),
        sa.CheckConstraint(
            f"subject_type IN ({_quoted(REGULATORY_SUBJECT_TYPES)})",
            name="ck_lab_regulatory_snapshot_subject_type",
        ),
        sa.CheckConstraint(
            f"result_state IN ({_quoted(REGULATORY_RESULT_STATES)})",
            name="ck_lab_regulatory_snapshot_result_state",
        ),
        sa.CheckConstraint(
            f"market_action IN ({_quoted(REGULATORY_MARKET_ACTIONS)})",
            name="ck_lab_regulatory_snapshot_market_action",
        ),
        sa.CheckConstraint(
            "finished_product_concentration >= 0 "
            "AND finished_product_concentration <= 1",
            name="ck_lab_regulatory_snapshot_concentration",
        ),
        sa.CheckConstraint(
            "(result_state = 'PASS_FOR_DECLARED_SCOPE' "
            "AND length(trim(permitted_wording)) > 0) OR "
            "(result_state != 'PASS_FOR_DECLARED_SCOPE' "
            "AND permitted_wording IS NULL)",
            name="ck_lab_regulatory_snapshot_wording",
        ),
        sa.CheckConstraint(
            "length(trim(reviewer_pseudonym)) > 0 AND reviewed_at IS NOT NULL",
            name="ck_lab_regulatory_snapshot_review",
        ),
        sa.CheckConstraint(
            "length(official_source_sha256) = 64",
            name="ck_lab_regulatory_snapshot_official_sha256",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_regulatory_snapshot_content_sha256",
        ),
        sa.CheckConstraint(
            "parent_sha256 IS NULL OR length(parent_sha256) = 64",
            name="ck_lab_regulatory_snapshot_parent_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["parent_version_id"],
            ["lab_regulatory_snapshot_versions.id"],
            ondelete="RESTRICT",
            name="fk_lab_regulatory_snapshot_parent",
        ),
        sa.ForeignKeyConstraint(
            ["legacy_assessment_version_id"],
            ["lab_regulatory_assessment_versions.id"],
            ondelete="RESTRICT",
            name="fk_lab_regulatory_snapshot_legacy_assessment",
        ),
        sa.ForeignKeyConstraint(
            ["primary_source_version_id"],
            ["lab_regulatory_source_versions.id"],
            ondelete="RESTRICT",
            name="fk_lab_regulatory_snapshot_primary_source",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "snapshot_id",
            "version_number",
            name="uq_lab_regulatory_snapshot_version",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_regulatory_snapshot_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_regulatory_snapshot_subject",
        "lab_regulatory_snapshot_versions",
        ["subject_type", "subject_id"],
        unique=False,
    )
    op.create_index(
        "ix_lab_regulatory_snapshot_result",
        "lab_regulatory_snapshot_versions",
        ["result_state", "evaluated_at"],
        unique=False,
    )

    op.create_table(
        "lab_regulatory_authority_findings",
        *_record_columns(),
        sa.Column("snapshot_version_id", sa.String(length=36), nullable=False),
        sa.Column("rule_version_id", sa.String(length=36), nullable=False),
        sa.Column("substance_name", sa.Text(), nullable=False),
        sa.Column("cas_number", sa.String(length=50), nullable=True),
        sa.Column("observed_fraction", sa.Float(), nullable=True),
        sa.Column("limit_fraction", sa.Float(), nullable=True),
        sa.Column("concentration_basis", sa.String(length=80), nullable=False),
        sa.Column("source_status", sa.String(length=60), nullable=False),
        sa.Column("enforced", sa.Boolean(), nullable=False),
        _json_array("contribution_lineage_json"),
        _json_array("reason_codes_json"),
        _json_object("detail_json"),
        sa.Column("result_state", sa.String(length=40), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            f"result_state IN ({_quoted(REGULATORY_RESULT_STATES)})",
            name="ck_lab_regulatory_finding_result_state",
        ),
        sa.CheckConstraint(
            f"source_status IN ({_quoted(REGULATORY_SOURCE_STATUSES)})",
            name="ck_lab_regulatory_finding_source_status",
        ),
        sa.CheckConstraint(
            "(observed_fraction IS NULL OR "
            "(observed_fraction >= 0 AND observed_fraction <= 1)) AND "
            "(limit_fraction IS NULL OR "
            "(limit_fraction >= 0 AND limit_fraction <= 1))",
            name="ck_lab_regulatory_finding_fraction",
        ),
        sa.CheckConstraint(
            "(enforced = 0 AND result_state = 'NOT_EVALUATED') OR "
            "(enforced = 1 AND result_state != 'NOT_EVALUATED')",
            name="ck_lab_regulatory_finding_enforcement_shape",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_regulatory_finding_content_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_version_id"],
            ["lab_regulatory_snapshot_versions.id"],
            ondelete="RESTRICT",
            name="fk_lab_regulatory_finding_snapshot",
        ),
        sa.ForeignKeyConstraint(
            ["rule_version_id"],
            ["lab_regulatory_rule_versions.id"],
            ondelete="RESTRICT",
            name="fk_lab_regulatory_finding_rule",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "snapshot_version_id",
            "rule_version_id",
            name="uq_lab_regulatory_finding_rule",
        ),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_regulatory_finding_content_sha256",
        ),
    )
    op.create_index(
        "ix_lab_regulatory_finding_snapshot_result",
        "lab_regulatory_authority_findings",
        ["snapshot_version_id", "result_state"],
        unique=False,
    )

    for table_name in B6_TABLES:
        _create_append_only_triggers(table_name)


def downgrade() -> None:
    for table_name in reversed(B6_TABLES):
        _drop_append_only_triggers(table_name)

    op.drop_index(
        "ix_lab_regulatory_finding_snapshot_result",
        table_name="lab_regulatory_authority_findings",
    )
    op.drop_table("lab_regulatory_authority_findings")

    op.drop_index(
        "ix_lab_regulatory_snapshot_result",
        table_name="lab_regulatory_snapshot_versions",
    )
    op.drop_index(
        "ix_lab_regulatory_snapshot_subject",
        table_name="lab_regulatory_snapshot_versions",
    )
    op.drop_table("lab_regulatory_snapshot_versions")

    op.drop_index(
        "ix_lab_regulatory_composition_entries_composition_profile_id",
        table_name="lab_regulatory_composition_entries",
    )
    op.drop_table("lab_regulatory_composition_entries")

    op.drop_index(
        "ix_lab_regulatory_composition_stock",
        table_name="lab_regulatory_composition_profiles",
    )
    op.drop_table("lab_regulatory_composition_profiles")

    op.drop_index(
        "ix_lab_supplier_document_stock_type",
        table_name="lab_supplier_document_bindings",
    )
    op.drop_table("lab_supplier_document_bindings")

    op.drop_index(
        "ix_lab_regulatory_rule_source_family",
        table_name="lab_regulatory_rule_versions",
    )
    op.drop_table("lab_regulatory_rule_versions")

    op.drop_index(
        "ix_lab_regulatory_source_authority_status",
        table_name="lab_regulatory_source_versions",
    )
    op.drop_table("lab_regulatory_source_versions")
