"""Add the B1-bound external-study admission slice.

Revision ID: 20260810_0016
Revises: 20260810_0015

The tables preserve published/source-reported study grains.  They are
append-only and authority-false; local physical Laboratory Beta records remain
separate.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260810_0016"
down_revision: str | None = "20260810_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STUDY_DOMAINS = (
    "HUMAN_SENSORY",
    "ANALYTICAL_CHEMISTRY",
    "BIOLOGICAL_ASSAY",
    "PHYSICAL_CHEMISTRY",
    "MIXED_METHODS",
    "OTHER",
)
STIMULUS_KINDS = (
    "SINGLE",
    "MIXTURE",
    "CONTROL",
    "RECOMBINATION",
    "OMISSION",
    "ADDITION",
    "PAIR",
    "TRIANGLE_SET",
    "OTHER",
)
CONDITION_ROLES = (
    "BASELINE",
    "CONTROL",
    "TEST",
    "OMISSION",
    "ADDITION",
    "RATIO",
    "OTHER",
)
UNIT_GRAINS = ("PARTICIPANT", "GROUP", "AGGREGATE", "SAMPLE")
OBSERVATION_GRAINS = (
    "INDIVIDUAL",
    "GROUP_AGGREGATE",
    "STUDY_AGGREGATE",
    "SAMPLE",
)
AGGREGATION_STATISTICS = (
    "RAW",
    "COUNT",
    "MEAN",
    "MEDIAN",
    "PROPORTION",
    "SCORE",
    "SIGNIFICANCE",
    "OTHER",
)
MISSINGNESS_STATES = (
    "OBSERVED",
    "MISSING",
    "NOT_APPLICABLE",
    "NOT_REPORTED",
)
CROSSWALK_STATUSES = (
    "EXACT_PROJECT_MATERIAL",
    "EXACT_EXTERNAL_IDENTITY_ONLY",
    "CANDIDATE",
    "CONFLICT",
    "UNRESOLVED",
    "OPAQUE_PRODUCT",
)
CONFLICT_TYPES = (
    "TABLE_PROSE",
    "METHOD_RESULT",
    "ETHICS",
    "RIGHTS",
    "IDENTITY",
    "UNIT",
    "OTHER",
)
CONFLICT_STATES = ("OPEN", "NARROWED", "RESOLVED")

TABLES = (
    "lab_external_study_versions",
    "lab_external_stimulus_versions",
    "lab_external_stimulus_components",
    "lab_external_conditions",
    "lab_external_experimental_units",
    "lab_external_observations",
    "lab_external_identity_crosswalks",
    "lab_external_study_conflicts",
)


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


def _base_columns() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "lab_external_study_versions",
        *_base_columns(),
        sa.Column("study_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("source_version_id", sa.String(length=36), nullable=False),
        sa.Column("source_extraction_id", sa.String(length=36), nullable=False),
        sa.Column("source_family", sa.String(length=255), nullable=False),
        sa.Column("study_key", sa.String(length=255), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("study_domain", sa.String(length=60), nullable=False),
        sa.Column("design_json", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("protocol_json", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("source_use_request_sha256", sa.String(length=64), nullable=False),
        sa.Column("source_use_assessment_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "source_use_constraint_version_ids_json",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column(
            "source_use_constraint_record_sha256s_json",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("adapter_name", sa.String(length=160), nullable=False),
        sa.Column("adapter_version", sa.String(length=100), nullable=False),
        sa.Column(
            "adapter_config_json",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "authority_state",
            sa.String(length=40),
            server_default=sa.text("'SOURCE_REPORTED_ONLY'"),
            nullable=False,
        ),
        sa.Column("supersedes_version_id", sa.String(length=36)),
        sa.Column("parent_record_sha256", sa.String(length=64)),
        sa.Column("record_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "version_number >= 1",
            name="ck_lab_external_study_version_positive",
        ),
        sa.CheckConstraint(
            f"study_domain IN ({_quoted(STUDY_DOMAINS)})",
            name="ck_lab_external_study_domain",
        ),
        sa.CheckConstraint(
            "authority_state = 'SOURCE_REPORTED_ONLY'",
            name="ck_lab_external_study_authority",
        ),
        sa.CheckConstraint(
            "length(source_use_request_sha256) = 64 AND "
            "length(source_use_assessment_sha256) = 64 AND "
            "length(record_sha256) = 64",
            name="ck_lab_external_study_hashes",
        ),
        sa.CheckConstraint(
            "(version_number = 1 AND supersedes_version_id IS NULL "
            "AND parent_record_sha256 IS NULL) OR "
            "(version_number > 1 AND supersedes_version_id IS NOT NULL "
            "AND length(parent_record_sha256) = 64)",
            name="ck_lab_external_study_version_chain",
        ),
        sa.ForeignKeyConstraint(
            ["source_version_id"],
            ["lab_source_document_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_extraction_id"],
            ["lab_source_extraction_records.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_version_id"],
            ["lab_external_study_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "study_id",
            "version_number",
            name="uq_lab_external_study_version",
        ),
        sa.UniqueConstraint(
            "record_sha256",
            name="uq_lab_external_study_record_sha256",
        ),
    )
    op.create_index(
        "ix_lab_external_study_versions_study_id",
        "lab_external_study_versions",
        ["study_id"],
    )
    op.create_index(
        "ix_lab_external_study_versions_source_version_id",
        "lab_external_study_versions",
        ["source_version_id"],
    )

    op.create_table(
        "lab_external_stimulus_versions",
        *_base_columns(),
        sa.Column("study_version_id", sa.String(length=36), nullable=False),
        sa.Column("stimulus_key", sa.String(length=255), nullable=False),
        sa.Column("source_extraction_id", sa.String(length=36), nullable=False),
        sa.Column("stimulus_kind", sa.String(length=40), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("matrix_json", sa.JSON(), nullable=False),
        sa.Column("preparation_json", sa.JSON(), nullable=False),
        sa.Column("context_json", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("record_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            f"stimulus_kind IN ({_quoted(STIMULUS_KINDS)})",
            name="ck_lab_external_stimulus_kind",
        ),
        sa.CheckConstraint(
            "length(record_sha256) = 64",
            name="ck_lab_external_stimulus_record_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["study_version_id"],
            ["lab_external_study_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_extraction_id"],
            ["lab_source_extraction_records.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "study_version_id",
            "stimulus_key",
            name="uq_lab_external_stimulus_key",
        ),
        sa.UniqueConstraint(
            "record_sha256",
            name="uq_lab_external_stimulus_record_sha256",
        ),
    )
    op.create_index(
        "ix_lab_external_stimulus_versions_study_version_id",
        "lab_external_stimulus_versions",
        ["study_version_id"],
    )

    op.create_table(
        "lab_external_stimulus_components",
        *_base_columns(),
        sa.Column("stimulus_version_id", sa.String(length=36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("component_key", sa.String(length=255), nullable=False),
        sa.Column("source_extraction_id", sa.String(length=36), nullable=False),
        sa.Column("source_identity_json", sa.JSON(), nullable=False),
        sa.Column("quantity_value_text", sa.String(length=128)),
        sa.Column("quantity_unit", sa.String(length=80)),
        sa.Column("quantity_basis", sa.String(length=100)),
        sa.Column("concentration_value_text", sa.String(length=128)),
        sa.Column("concentration_unit", sa.String(length=80)),
        sa.Column("concentration_basis", sa.String(length=100)),
        sa.Column("carrier_json", sa.JSON(), nullable=False),
        sa.Column("purity_json", sa.JSON(), nullable=False),
        sa.Column("role", sa.String(length=100)),
        sa.Column("record_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "position >= 1",
            name="ck_lab_external_component_position",
        ),
        sa.CheckConstraint(
            "(quantity_value_text IS NULL AND quantity_unit IS NULL "
            "AND quantity_basis IS NULL) OR "
            "(quantity_value_text IS NOT NULL AND quantity_unit IS NOT NULL "
            "AND quantity_basis IS NOT NULL)",
            name="ck_lab_external_component_quantity_shape",
        ),
        sa.CheckConstraint(
            "(concentration_value_text IS NULL AND concentration_unit IS NULL "
            "AND concentration_basis IS NULL) OR "
            "(concentration_value_text IS NOT NULL "
            "AND concentration_unit IS NOT NULL "
            "AND concentration_basis IS NOT NULL)",
            name="ck_lab_external_component_concentration_shape",
        ),
        sa.CheckConstraint(
            "length(record_sha256) = 64",
            name="ck_lab_external_component_record_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["stimulus_version_id"],
            ["lab_external_stimulus_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_extraction_id"],
            ["lab_source_extraction_records.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "stimulus_version_id",
            "position",
            name="uq_lab_external_component_position",
        ),
        sa.UniqueConstraint(
            "stimulus_version_id",
            "component_key",
            name="uq_lab_external_component_key",
        ),
        sa.UniqueConstraint(
            "record_sha256",
            name="uq_lab_external_component_record_sha256",
        ),
    )
    op.create_index(
        "ix_lab_external_stimulus_components_stimulus_version_id",
        "lab_external_stimulus_components",
        ["stimulus_version_id"],
    )

    op.create_table(
        "lab_external_conditions",
        *_base_columns(),
        sa.Column("study_version_id", sa.String(length=36), nullable=False),
        sa.Column("condition_key", sa.String(length=255), nullable=False),
        sa.Column("source_extraction_id", sa.String(length=36), nullable=False),
        sa.Column("condition_role", sa.String(length=40), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("primary_stimulus_version_id", sa.String(length=36)),
        sa.Column("factors_json", sa.JSON(), nullable=False),
        sa.Column("context_json", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("record_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            f"condition_role IN ({_quoted(CONDITION_ROLES)})",
            name="ck_lab_external_condition_role",
        ),
        sa.CheckConstraint(
            "length(record_sha256) = 64",
            name="ck_lab_external_condition_record_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["study_version_id"],
            ["lab_external_study_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_extraction_id"],
            ["lab_source_extraction_records.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["primary_stimulus_version_id"],
            ["lab_external_stimulus_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "study_version_id",
            "condition_key",
            name="uq_lab_external_condition_key",
        ),
        sa.UniqueConstraint(
            "record_sha256",
            name="uq_lab_external_condition_record_sha256",
        ),
    )
    op.create_index(
        "ix_lab_external_conditions_study_version_id",
        "lab_external_conditions",
        ["study_version_id"],
    )

    op.create_table(
        "lab_external_experimental_units",
        *_base_columns(),
        sa.Column("study_version_id", sa.String(length=36), nullable=False),
        sa.Column("unit_key", sa.String(length=255), nullable=False),
        sa.Column("source_extraction_id", sa.String(length=36), nullable=False),
        sa.Column("unit_grain", sa.String(length=40), nullable=False),
        sa.Column("parent_unit_id", sa.String(length=36)),
        sa.Column("pseudonymous_token", sa.String(length=255)),
        sa.Column("reported_n", sa.Integer()),
        sa.Column("context_json", sa.JSON(), nullable=False),
        sa.Column("record_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            f"unit_grain IN ({_quoted(UNIT_GRAINS)})",
            name="ck_lab_external_unit_grain",
        ),
        sa.CheckConstraint(
            "reported_n IS NULL OR reported_n >= 1",
            name="ck_lab_external_unit_reported_n",
        ),
        sa.CheckConstraint(
            "parent_unit_id IS NULL OR parent_unit_id <> id",
            name="ck_lab_external_unit_not_self_parent",
        ),
        sa.CheckConstraint(
            "length(record_sha256) = 64",
            name="ck_lab_external_unit_record_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["study_version_id"],
            ["lab_external_study_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_extraction_id"],
            ["lab_source_extraction_records.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parent_unit_id"],
            ["lab_external_experimental_units.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "study_version_id",
            "unit_key",
            name="uq_lab_external_unit_key",
        ),
        sa.UniqueConstraint(
            "record_sha256",
            name="uq_lab_external_unit_record_sha256",
        ),
    )
    op.create_index(
        "ix_lab_external_experimental_units_study_version_id",
        "lab_external_experimental_units",
        ["study_version_id"],
    )

    op.create_table(
        "lab_external_observations",
        *_base_columns(),
        sa.Column("study_version_id", sa.String(length=36), nullable=False),
        sa.Column("observation_key", sa.String(length=255), nullable=False),
        sa.Column("source_extraction_id", sa.String(length=36), nullable=False),
        sa.Column("condition_id", sa.String(length=36), nullable=False),
        sa.Column("experimental_unit_id", sa.String(length=36), nullable=False),
        sa.Column("primary_stimulus_version_id", sa.String(length=36)),
        sa.Column("trial_key", sa.String(length=255), nullable=False),
        sa.Column("session_key", sa.String(length=255)),
        sa.Column("repeat_index", sa.Integer()),
        sa.Column("presentation_json", sa.JSON(), nullable=False),
        sa.Column("endpoint_key", sa.String(length=255), nullable=False),
        sa.Column("value_json", sa.JSON(none_as_null=True)),
        sa.Column("original_unit", sa.String(length=100), nullable=False),
        sa.Column("scale_json", sa.JSON(), nullable=False),
        sa.Column("timepoint_json", sa.JSON(), nullable=False),
        sa.Column("replicate_index", sa.Integer()),
        sa.Column("observation_grain", sa.String(length=40), nullable=False),
        sa.Column("aggregation_statistic", sa.String(length=40), nullable=False),
        sa.Column("missingness", sa.String(length=40), nullable=False),
        sa.Column("uncertainty_json", sa.JSON(), nullable=False),
        sa.Column("limitations_json", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("record_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            f"observation_grain IN ({_quoted(OBSERVATION_GRAINS)})",
            name="ck_lab_external_observation_grain",
        ),
        sa.CheckConstraint(
            f"aggregation_statistic IN ({_quoted(AGGREGATION_STATISTICS)})",
            name="ck_lab_external_observation_statistic",
        ),
        sa.CheckConstraint(
            f"missingness IN ({_quoted(MISSINGNESS_STATES)})",
            name="ck_lab_external_observation_missingness",
        ),
        sa.CheckConstraint(
            "(missingness = 'OBSERVED' AND value_json IS NOT NULL) OR "
            "(missingness <> 'OBSERVED' AND value_json IS NULL)",
            name="ck_lab_external_observation_value_shape",
        ),
        sa.CheckConstraint(
            "(repeat_index IS NULL OR repeat_index >= 1) AND "
            "(replicate_index IS NULL OR replicate_index >= 1)",
            name="ck_lab_external_observation_indices",
        ),
        sa.CheckConstraint(
            "length(record_sha256) = 64",
            name="ck_lab_external_observation_record_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["study_version_id"],
            ["lab_external_study_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_extraction_id"],
            ["lab_source_extraction_records.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["condition_id"],
            ["lab_external_conditions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["experimental_unit_id"],
            ["lab_external_experimental_units.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["primary_stimulus_version_id"],
            ["lab_external_stimulus_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "study_version_id",
            "observation_key",
            name="uq_lab_external_observation_key",
        ),
        sa.UniqueConstraint(
            "record_sha256",
            name="uq_lab_external_observation_record_sha256",
        ),
    )
    op.create_index(
        "ix_lab_external_observations_study_version_id",
        "lab_external_observations",
        ["study_version_id"],
    )

    op.create_table(
        "lab_external_identity_crosswalks",
        *_base_columns(),
        sa.Column("component_id", sa.String(length=36), nullable=False),
        sa.Column("source_extraction_id", sa.String(length=36), nullable=False),
        sa.Column("resolution_status", sa.String(length=50), nullable=False),
        sa.Column("material_id", sa.String(length=36)),
        sa.Column("source_identity_json", sa.JSON(), nullable=False),
        sa.Column("resolved_identity_json", sa.JSON(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("record_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            f"resolution_status IN ({_quoted(CROSSWALK_STATUSES)})",
            name="ck_lab_external_crosswalk_status",
        ),
        sa.CheckConstraint(
            "(resolution_status = 'EXACT_PROJECT_MATERIAL' "
            "AND material_id IS NOT NULL) OR "
            "(resolution_status IN "
            "('EXACT_EXTERNAL_IDENTITY_ONLY', 'UNRESOLVED', 'OPAQUE_PRODUCT') "
            "AND material_id IS NULL) OR "
            "resolution_status IN ('CANDIDATE', 'CONFLICT')",
            name="ck_lab_external_crosswalk_material_shape",
        ),
        sa.CheckConstraint(
            "length(record_sha256) = 64",
            name="ck_lab_external_crosswalk_record_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["component_id"],
            ["lab_external_stimulus_components.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_extraction_id"],
            ["lab_source_extraction_records.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["material_id"],
            ["lab_materials.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "component_id",
            name="uq_lab_external_crosswalk_component",
        ),
        sa.UniqueConstraint(
            "record_sha256",
            name="uq_lab_external_crosswalk_record_sha256",
        ),
    )
    op.create_index(
        "ix_lab_external_identity_crosswalks_component_id",
        "lab_external_identity_crosswalks",
        ["component_id"],
    )

    op.create_table(
        "lab_external_study_conflicts",
        *_base_columns(),
        sa.Column("study_version_id", sa.String(length=36), nullable=False),
        sa.Column("conflict_key", sa.String(length=255), nullable=False),
        sa.Column("conflict_type", sa.String(length=40), nullable=False),
        sa.Column("conflict_state", sa.String(length=40), nullable=False),
        sa.Column("source_extraction_id", sa.String(length=36), nullable=False),
        sa.Column("related_extraction_id", sa.String(length=36), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("record_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            f"conflict_type IN ({_quoted(CONFLICT_TYPES)})",
            name="ck_lab_external_conflict_type",
        ),
        sa.CheckConstraint(
            f"conflict_state IN ({_quoted(CONFLICT_STATES)})",
            name="ck_lab_external_conflict_state",
        ),
        sa.CheckConstraint(
            "source_extraction_id <> related_extraction_id",
            name="ck_lab_external_conflict_distinct_extractions",
        ),
        sa.CheckConstraint(
            "length(record_sha256) = 64",
            name="ck_lab_external_conflict_record_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["study_version_id"],
            ["lab_external_study_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_extraction_id"],
            ["lab_source_extraction_records.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["related_extraction_id"],
            ["lab_source_extraction_records.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "study_version_id",
            "conflict_key",
            name="uq_lab_external_conflict_key",
        ),
        sa.UniqueConstraint(
            "record_sha256",
            name="uq_lab_external_conflict_record_sha256",
        ),
    )
    op.create_index(
        "ix_lab_external_study_conflicts_study_version_id",
        "lab_external_study_conflicts",
        ["study_version_id"],
    )

    for table_name in TABLES:
        _create_append_only_triggers(table_name)


def downgrade() -> None:
    for table_name in reversed(TABLES):
        _drop_append_only_triggers(table_name)
    for table_name, index_name in (
        (
            "lab_external_study_conflicts",
            "ix_lab_external_study_conflicts_study_version_id",
        ),
        (
            "lab_external_identity_crosswalks",
            "ix_lab_external_identity_crosswalks_component_id",
        ),
        (
            "lab_external_observations",
            "ix_lab_external_observations_study_version_id",
        ),
        (
            "lab_external_experimental_units",
            "ix_lab_external_experimental_units_study_version_id",
        ),
        (
            "lab_external_conditions",
            "ix_lab_external_conditions_study_version_id",
        ),
        (
            "lab_external_stimulus_components",
            "ix_lab_external_stimulus_components_stimulus_version_id",
        ),
        (
            "lab_external_stimulus_versions",
            "ix_lab_external_stimulus_versions_study_version_id",
        ),
        (
            "lab_external_study_versions",
            "ix_lab_external_study_versions_source_version_id",
        ),
        (
            "lab_external_study_versions",
            "ix_lab_external_study_versions_study_id",
        ),
    ):
        op.drop_index(index_name, table_name=table_name)
    for table_name in reversed(TABLES):
        op.drop_table(table_name)
