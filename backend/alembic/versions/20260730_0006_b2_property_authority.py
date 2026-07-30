"""Add append-only B2 property observations and selected assertions."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260730_0006"
down_revision = "20260730_0005"
branch_labels = None
depends_on = None

LEGACY_AUTHORITY_REASON = (
    "Pre-B2 scalar property without canonical observation lineage."
)
PROPERTY_IDENTITY_SCOPES = (
    "CHEMICAL_ENTITY",
    "STEREOISOMER_OR_ISOMERIC_MIXTURE",
    "TRADE_GRADE",
    "SUPPLIER_PRODUCT",
    "SUPPLIER_LOT",
    "STOCK_SOLUTION",
    "PHYSICAL_DOSE",
    "NATURAL_MATERIAL",
)
PROPERTY_VALUE_KINDS = (
    "NUMERIC",
    "CATEGORICAL",
    "INTERVAL",
    "DISTRIBUTION",
    "CENSORED",
)
PROPERTY_CENSORING_QUALIFIERS = (
    "LT_LOD",
    "LT_LOQ",
    "GT_UPPER_RANGE",
    "NOT_DETECTED",
    "TRACE",
)
PROPERTY_EVIDENCE_CLASSES = (
    "MEASURED",
    "LITERATURE_DERIVED",
    "SUPPLIER_PROVIDED",
    "EMPIRICALLY_CALIBRATED",
    "MODEL_ESTIMATED",
    "HEURISTIC",
    "SPECULATIVE",
    "UNKNOWN",
)
PROPERTY_REVIEW_STATES = (
    "STAGED",
    "REVIEWED",
    "ACCEPTED_FOR_SCOPED_USE",
    "REJECTED",
    "SUPERSEDED",
)
PROPERTY_CONFLICT_STATES = ("UNRESOLVED", "RESOLVED_FOR_SCOPE")
PROPERTY_CONFLICT_MATERIALITIES = ("BLOCKING", "NON_BLOCKING")
ASSERTION_CANDIDATE_DECISIONS = ("INCLUDE", "EXCLUDE")
ASSERTION_SELECTION_KINDS = ("OBSERVATION", "MODEL", "NONE")
ASSERTION_INTERPOLATION_STATES = (
    "EXACT",
    "INTERPOLATED",
    "EXTRAPOLATED",
    "NOT_APPLICABLE",
)
ASSERTION_AUTHORITY_STATES = (
    "AUTHORIZED_FOR_SCOPED_PROPERTY",
    "ADVISORY_ONLY",
    "WITHHELD_CONFLICT",
    "WITHHELD_UNKNOWN",
)
PROPERTY_AUTHORITY_TABLES = (
    "lab_property_observations",
    "lab_property_conflict_sets",
    "lab_property_conflict_members",
    "lab_selected_assertions",
    "lab_selected_assertion_candidates",
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
    op.add_column(
        "lab_material_properties",
        sa.Column(
            "authority_state",
            sa.String(length=40),
            server_default=sa.text("'LEGACY_HEURISTIC'"),
            nullable=False,
        ),
    )
    op.add_column(
        "lab_material_properties",
        sa.Column(
            "authority_reason",
            sa.Text(),
            server_default=sa.text(f"'{LEGACY_AUTHORITY_REASON}'"),
            nullable=False,
        ),
    )

    op.create_table(
        "lab_property_observations",
        *_record_columns(),
        sa.Column("schema_version", sa.String(length=80), nullable=False),
        sa.Column("identity_scope", sa.String(length=60), nullable=False),
        sa.Column("subject_identity_json", sa.JSON(), nullable=False),
        sa.Column(
            "subject_identity_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("property_type", sa.String(length=100), nullable=False),
        sa.Column("value_kind", sa.String(length=40), nullable=False),
        sa.Column("numeric_value", sa.Float()),
        sa.Column("categorical_value", sa.Text()),
        sa.Column("interval_lower", sa.Float()),
        sa.Column("interval_upper", sa.Float()),
        sa.Column("distribution_json", sa.JSON(none_as_null=True)),
        sa.Column("censoring_qualifier", sa.String(length=40)),
        sa.Column("censoring_limit", sa.Float()),
        sa.Column("original_unit", sa.Text(), nullable=False),
        sa.Column("canonical_unit", sa.Text(), nullable=False),
        sa.Column("temperature_k", sa.Float()),
        sa.Column("pressure_pa", sa.Float()),
        sa.Column("relative_humidity_percent", sa.Float()),
        sa.Column("matrix", sa.Text()),
        sa.Column("phase", sa.String(length=80)),
        sa.Column("purity_fraction", sa.Float()),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("source_version_id", sa.String(length=36), nullable=False),
        sa.Column(
            "extraction_record_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "source_locator_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "replicate_count",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column("statistic", sa.String(length=100), nullable=False),
        sa.Column("standard_uncertainty", sa.Float()),
        sa.Column(
            "uncertainty_interval_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("evidence_class", sa.String(length=40), nullable=False),
        sa.Column("review_state", sa.String(length=40), nullable=False),
        sa.Column(
            "quality_flags_json",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column(
            "applicability_domain_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "provenance_activity_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("supersedes_observation_id", sa.String(length=36)),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            f"identity_scope IN ({_quoted(PROPERTY_IDENTITY_SCOPES)})",
            name="ck_lab_property_observation_identity_scope",
        ),
        sa.CheckConstraint(
            f"value_kind IN ({_quoted(PROPERTY_VALUE_KINDS)})",
            name="ck_lab_property_observation_value_kind",
        ),
        sa.CheckConstraint(
            "("
            "(value_kind = 'NUMERIC' AND numeric_value IS NOT NULL "
            "AND categorical_value IS NULL AND interval_lower IS NULL "
            "AND interval_upper IS NULL AND distribution_json IS NULL) OR "
            "(value_kind = 'CATEGORICAL' AND numeric_value IS NULL "
            "AND categorical_value IS NOT NULL AND interval_lower IS NULL "
            "AND interval_upper IS NULL AND distribution_json IS NULL) OR "
            "(value_kind = 'INTERVAL' AND numeric_value IS NULL "
            "AND categorical_value IS NULL AND interval_lower IS NOT NULL "
            "AND interval_upper IS NOT NULL "
            "AND interval_lower <= interval_upper "
            "AND distribution_json IS NULL) OR "
            "(value_kind = 'DISTRIBUTION' AND numeric_value IS NULL "
            "AND categorical_value IS NULL AND interval_lower IS NULL "
            "AND interval_upper IS NULL AND distribution_json IS NOT NULL) OR "
            "(value_kind = 'CENSORED' AND numeric_value IS NULL "
            "AND categorical_value IS NULL AND interval_lower IS NULL "
            "AND interval_upper IS NULL AND distribution_json IS NULL)"
            ")",
            name="ck_lab_property_observation_value_shape",
        ),
        sa.CheckConstraint(
            "("
            "(value_kind <> 'CENSORED' AND censoring_qualifier IS NULL "
            "AND censoring_limit IS NULL) OR "
            "(value_kind = 'CENSORED' "
            f"AND censoring_qualifier IN "
            f"({_quoted(PROPERTY_CENSORING_QUALIFIERS)}) "
            "AND ((censoring_qualifier IN "
            "('LT_LOD', 'LT_LOQ', 'GT_UPPER_RANGE') "
            "AND censoring_limit IS NOT NULL) "
            "OR censoring_qualifier IN ('NOT_DETECTED', 'TRACE')))"
            ")",
            name="ck_lab_property_observation_censoring",
        ),
        sa.CheckConstraint(
            "(temperature_k IS NULL OR temperature_k > 0) "
            "AND (pressure_pa IS NULL OR pressure_pa > 0) "
            "AND (relative_humidity_percent IS NULL "
            "OR (relative_humidity_percent >= 0 "
            "AND relative_humidity_percent <= 100)) "
            "AND (purity_fraction IS NULL "
            "OR (purity_fraction >= 0 AND purity_fraction <= 1)) "
            "AND (standard_uncertainty IS NULL "
            "OR standard_uncertainty >= 0)",
            name="ck_lab_property_observation_conditions",
        ),
        sa.CheckConstraint(
            "replicate_count >= 1",
            name="ck_lab_property_observation_replicate_count",
        ),
        sa.CheckConstraint(
            f"evidence_class IN ({_quoted(PROPERTY_EVIDENCE_CLASSES)})",
            name="ck_lab_property_observation_evidence_class",
        ),
        sa.CheckConstraint(
            f"review_state IN ({_quoted(PROPERTY_REVIEW_STATES)})",
            name="ck_lab_property_observation_review_state",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_property_observation_content_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["source_version_id"],
            ["lab_source_document_versions.id"],
            ondelete="RESTRICT",
            name="fk_lab_property_observation_source",
        ),
        sa.ForeignKeyConstraint(
            ["extraction_record_id"],
            ["lab_source_extraction_records.id"],
            ondelete="RESTRICT",
            name="fk_lab_property_observation_extraction",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_observation_id"],
            ["lab_property_observations.id"],
            ondelete="RESTRICT",
            name="fk_lab_property_observation_supersedes",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_property_observation_content_sha256",
        ),
        sa.UniqueConstraint(
            "supersedes_observation_id",
            name="uq_lab_property_observation_supersedes",
        ),
    )
    for column_name in (
        "subject_identity_sha256",
        "property_type",
        "source_version_id",
        "extraction_record_id",
    ):
        op.create_index(
            f"ix_lab_property_observations_{column_name}",
            "lab_property_observations",
            [column_name],
            unique=False,
        )

    op.create_table(
        "lab_property_conflict_sets",
        *_record_columns(),
        sa.Column("schema_version", sa.String(length=80), nullable=False),
        sa.Column("requested_identity_json", sa.JSON(), nullable=False),
        sa.Column(
            "requested_identity_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("property_type", sa.String(length=100), nullable=False),
        sa.Column(
            "requested_conditions_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("state", sa.String(length=40), nullable=False),
        sa.Column("materiality", sa.String(length=40), nullable=False),
        sa.Column(
            "difference_dimensions_json",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            f"state IN ({_quoted(PROPERTY_CONFLICT_STATES)})",
            name="ck_lab_property_conflict_state",
        ),
        sa.CheckConstraint(
            f"materiality IN ({_quoted(PROPERTY_CONFLICT_MATERIALITIES)})",
            name="ck_lab_property_conflict_materiality",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_property_conflict_content_sha256",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_property_conflict_content_sha256",
        ),
    )
    for column_name in ("requested_identity_sha256", "property_type"):
        op.create_index(
            f"ix_lab_property_conflict_sets_{column_name}",
            "lab_property_conflict_sets",
            [column_name],
            unique=False,
        )

    op.create_table(
        "lab_property_conflict_members",
        *_record_columns(),
        sa.Column("conflict_set_id", sa.String(length=36), nullable=False),
        sa.Column("observation_id", sa.String(length=36), nullable=False),
        sa.Column(
            "differences_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conflict_set_id"],
            ["lab_property_conflict_sets.id"],
            ondelete="RESTRICT",
            name="fk_lab_property_conflict_member_set",
        ),
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["lab_property_observations.id"],
            ondelete="RESTRICT",
            name="fk_lab_property_conflict_member_observation",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "conflict_set_id",
            "observation_id",
            name="uq_lab_property_conflict_member",
        ),
    )
    for column_name in ("conflict_set_id", "observation_id"):
        op.create_index(
            f"ix_lab_property_conflict_members_{column_name}",
            "lab_property_conflict_members",
            [column_name],
            unique=False,
        )

    op.create_table(
        "lab_selected_assertions",
        *_record_columns(),
        sa.Column("schema_version", sa.String(length=80), nullable=False),
        sa.Column("requested_identity_json", sa.JSON(), nullable=False),
        sa.Column(
            "requested_identity_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "requested_property_type",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "requested_conditions_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("conflict_set_id", sa.String(length=36)),
        sa.Column("selection_policy_version", sa.Text(), nullable=False),
        sa.Column("selection_kind", sa.String(length=40), nullable=False),
        sa.Column("selected_observation_id", sa.String(length=36)),
        sa.Column("selected_model_json", sa.JSON(none_as_null=True)),
        sa.Column("interpolation_state", sa.String(length=40), nullable=False),
        sa.Column(
            "propagated_uncertainty_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "applicability_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("authority_state", sa.String(length=60), nullable=False),
        sa.Column("permitted_claim_wording", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            f"selection_kind IN ({_quoted(ASSERTION_SELECTION_KINDS)})",
            name="ck_lab_selected_assertion_selection_kind",
        ),
        sa.CheckConstraint(
            "("
            "(selection_kind = 'OBSERVATION' "
            "AND selected_observation_id IS NOT NULL "
            "AND selected_model_json IS NULL) OR "
            "(selection_kind = 'MODEL' "
            "AND selected_observation_id IS NULL "
            "AND selected_model_json IS NOT NULL) OR "
            "(selection_kind = 'NONE' "
            "AND selected_observation_id IS NULL "
            "AND selected_model_json IS NULL)"
            ")",
            name="ck_lab_selected_assertion_selection_shape",
        ),
        sa.CheckConstraint(
            f"interpolation_state IN "
            f"({_quoted(ASSERTION_INTERPOLATION_STATES)})",
            name="ck_lab_selected_assertion_interpolation",
        ),
        sa.CheckConstraint(
            f"authority_state IN ({_quoted(ASSERTION_AUTHORITY_STATES)})",
            name="ck_lab_selected_assertion_authority",
        ),
        sa.CheckConstraint(
            "length(content_sha256) = 64",
            name="ck_lab_selected_assertion_content_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["conflict_set_id"],
            ["lab_property_conflict_sets.id"],
            ondelete="RESTRICT",
            name="fk_lab_selected_assertion_conflict",
        ),
        sa.ForeignKeyConstraint(
            ["selected_observation_id"],
            ["lab_property_observations.id"],
            ondelete="RESTRICT",
            name="fk_lab_selected_assertion_observation",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "content_sha256",
            name="uq_lab_selected_assertion_content_sha256",
        ),
    )
    for column_name in (
        "requested_identity_sha256",
        "requested_property_type",
        "conflict_set_id",
        "selected_observation_id",
    ):
        op.create_index(
            f"ix_lab_selected_assertions_{column_name}",
            "lab_selected_assertions",
            [column_name],
            unique=False,
        )

    op.create_table(
        "lab_selected_assertion_candidates",
        *_record_columns(),
        sa.Column(
            "selected_assertion_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column("observation_id", sa.String(length=36), nullable=False),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.CheckConstraint(
            f"decision IN ({_quoted(ASSERTION_CANDIDATE_DECISIONS)})",
            name="ck_lab_selected_assertion_candidate_decision",
        ),
        sa.ForeignKeyConstraint(
            ["selected_assertion_id"],
            ["lab_selected_assertions.id"],
            ondelete="RESTRICT",
            name="fk_lab_selected_assertion_candidate_assertion",
        ),
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["lab_property_observations.id"],
            ondelete="RESTRICT",
            name="fk_lab_selected_assertion_candidate_observation",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "selected_assertion_id",
            "observation_id",
            name="uq_lab_selected_assertion_candidate",
        ),
    )
    for column_name in ("selected_assertion_id", "observation_id"):
        op.create_index(
            f"ix_lab_selected_assertion_candidates_{column_name}",
            "lab_selected_assertion_candidates",
            [column_name],
            unique=False,
        )

    _create_append_only_triggers("lab_material_properties")
    for table_name in PROPERTY_AUTHORITY_TABLES:
        _create_append_only_triggers(table_name)


def downgrade() -> None:
    _drop_append_only_triggers("lab_material_properties")
    for table_name in reversed(PROPERTY_AUTHORITY_TABLES):
        _drop_append_only_triggers(table_name)

    for column_name in ("selected_assertion_id", "observation_id"):
        op.drop_index(
            f"ix_lab_selected_assertion_candidates_{column_name}",
            table_name="lab_selected_assertion_candidates",
        )
    op.drop_table("lab_selected_assertion_candidates")

    for column_name in (
        "requested_identity_sha256",
        "requested_property_type",
        "conflict_set_id",
        "selected_observation_id",
    ):
        op.drop_index(
            f"ix_lab_selected_assertions_{column_name}",
            table_name="lab_selected_assertions",
        )
    op.drop_table("lab_selected_assertions")

    for column_name in ("conflict_set_id", "observation_id"):
        op.drop_index(
            f"ix_lab_property_conflict_members_{column_name}",
            table_name="lab_property_conflict_members",
        )
    op.drop_table("lab_property_conflict_members")

    for column_name in ("requested_identity_sha256", "property_type"):
        op.drop_index(
            f"ix_lab_property_conflict_sets_{column_name}",
            table_name="lab_property_conflict_sets",
        )
    op.drop_table("lab_property_conflict_sets")

    for column_name in (
        "subject_identity_sha256",
        "property_type",
        "source_version_id",
        "extraction_record_id",
    ):
        op.drop_index(
            f"ix_lab_property_observations_{column_name}",
            table_name="lab_property_observations",
        )
    op.drop_table("lab_property_observations")

    op.drop_column("lab_material_properties", "authority_reason")
    op.drop_column("lab_material_properties", "authority_state")
