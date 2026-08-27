"""Create the laboratory beta schema from a frozen definition."""

import sqlalchemy as sa

from alembic import op

revision = "20260716_0001"
down_revision = None
branch_labels = None
depends_on = None


APPEND_ONLY_TABLES = (
    "lab_bottle_event_effects",
    "lab_bottle_events",
    "lab_bottle_measurements",
    "lab_evidence_records",
    "lab_formula_components",
    "lab_formula_versions",
    "lab_inventory_movements",
    "lab_observations",
    "lab_outcomes",
    "lab_pairwise_comparisons",
    "lab_predictions",
)


def _record_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    ]


def _trigger_name(operation: str, table_name: str) -> str:
    return f"trg_{table_name}_{operation}_append_only"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        # sqlite3 legacy transaction control otherwise rolls back Alembic's
        # revision-row INSERT while leaving this revision's DDL in place.
        bind.connection.driver_connection.isolation_level = None

    op.create_table(
        "lab_evidence_records",
        *_record_columns(),
        sa.Column("claim_key", sa.String(length=255), nullable=False),
        sa.Column("classification", sa.String(length=40), nullable=False),
        sa.Column("source_locator", sa.Text(), nullable=False),
        sa.Column("source_version", sa.String(length=100), nullable=True),
        sa.Column("method", sa.Text(), nullable=True),
        sa.Column("assumptions_json", sa.JSON(), nullable=False),
        sa.Column("limitations_json", sa.JSON(), nullable=False),
        sa.Column("payload_sha256", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_lab_evidence_records_claim_key",
        "lab_evidence_records",
        ["claim_key"],
        unique=False,
    )
    op.create_table(
        "lab_experiments",
        *_record_columns(),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("protocol_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "lab_formulas",
        *_record_columns(),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_lab_formulas_name", "lab_formulas", ["name"], unique=False
    )
    op.create_table(
        "lab_materials",
        *_record_columns(),
        sa.Column("canonical_name", sa.String(length=255), nullable=False),
        sa.Column("cas_number", sa.String(length=50), nullable=True),
        sa.Column("original_payload_json", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("canonical_name"),
    )
    op.create_index(
        "ix_lab_materials_cas_number",
        "lab_materials",
        ["cas_number"],
        unique=False,
    )
    op.create_table(
        "lab_constituents",
        *_record_columns(),
        sa.Column("parent_material_id", sa.String(length=36), nullable=False),
        sa.Column("constituent_name", sa.String(length=255), nullable=False),
        sa.Column("cas_number", sa.String(length=50), nullable=True),
        sa.Column("fraction", sa.Float(), nullable=False),
        sa.Column("fraction_basis", sa.String(length=80), nullable=False),
        sa.Column("evidence_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["evidence_id"], ["lab_evidence_records.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["parent_material_id"], ["lab_materials.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "lab_formula_versions",
        *_record_columns(),
        sa.Column("formula_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("brief_json", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column(
            "constraints_json", sa.JSON(), server_default=sa.text("'{}'"), nullable=False
        ),
        sa.Column("concentration_fraction", sa.Float(), nullable=True),
        sa.Column("concentration_basis", sa.String(length=80), nullable=True),
        sa.Column("source_json", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.ForeignKeyConstraint(
            ["formula_id"], ["lab_formulas.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "formula_id", "version_number", name="uq_lab_formula_version"
        ),
    )
    op.create_table(
        "lab_material_aliases",
        *_record_columns(),
        sa.Column("material_id", sa.String(length=36), nullable=False),
        sa.Column("alias", sa.String(length=255), nullable=False),
        sa.Column("normalized_alias", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(
            ["material_id"], ["lab_materials.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_alias", name="uq_lab_material_alias"),
    )
    op.create_table(
        "lab_material_properties",
        *_record_columns(),
        sa.Column("material_id", sa.String(length=36), nullable=False),
        sa.Column("property_key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=80), nullable=False),
        sa.Column("conditions_json", sa.JSON(), nullable=False),
        sa.Column("standard_uncertainty", sa.Float(), nullable=True),
        sa.Column("evidence_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["evidence_id"], ["lab_evidence_records.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["material_id"], ["lab_materials.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "lab_restrictions",
        *_record_columns(),
        sa.Column("material_id", sa.String(length=36), nullable=True),
        sa.Column("substance_name", sa.String(length=255), nullable=False),
        sa.Column("standard_source", sa.String(length=255), nullable=False),
        sa.Column("amendment", sa.String(length=80), nullable=False),
        sa.Column("product_category", sa.String(length=80), nullable=False),
        sa.Column("concentration_basis", sa.String(length=80), nullable=False),
        sa.Column("maximum_fraction", sa.Float(), nullable=True),
        sa.Column("restriction_type", sa.String(length=40), nullable=False),
        sa.Column("evidence_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["evidence_id"], ["lab_evidence_records.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["material_id"], ["lab_materials.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "lab_stock_solutions",
        *_record_columns(),
        sa.Column("material_id", sa.String(length=36), nullable=False),
        sa.Column("supplier", sa.String(length=255), nullable=True),
        sa.Column("lot_number", sa.String(length=100), nullable=True),
        sa.Column("active_fraction", sa.Float(), nullable=False),
        sa.Column("fraction_basis", sa.String(length=80), nullable=False),
        sa.Column("density_g_ml", sa.Float(), nullable=True),
        sa.Column("solvent_name", sa.String(length=255), nullable=True),
        sa.Column("initial_mass_g", sa.Float(), nullable=False),
        sa.Column("source_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["material_id"], ["lab_materials.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "lab_batches",
        *_record_columns(),
        sa.Column("formula_version_id", sa.String(length=36), nullable=False),
        sa.Column("batch_code", sa.String(length=100), nullable=False),
        sa.Column("actual_mass_g", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["formula_version_id"], ["lab_formula_versions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("batch_code"),
    )
    op.create_table(
        "lab_formula_components",
        *_record_columns(),
        sa.Column("formula_version_id", sa.String(length=36), nullable=False),
        sa.Column("stock_solution_id", sa.String(length=36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("requested_mass_g", sa.Float(), nullable=False),
        sa.Column("requested_volume_ul", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(
            ["formula_version_id"], ["lab_formula_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["stock_solution_id"], ["lab_stock_solutions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "formula_version_id",
            "position",
            name="uq_lab_formula_component_position",
        ),
    )
    op.create_table(
        "lab_bottles",
        *_record_columns(),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("batch_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(
            ["batch_id"], ["lab_batches.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "lab_bottle_events",
        *_record_columns(),
        sa.Column("bottle_id", sa.String(length=36), nullable=False),
        sa.Column("stream_sequence", sa.Integer(), nullable=False),
        sa.Column("expected_sequence", sa.Integer(), nullable=False),
        sa.Column("command_id", sa.String(length=64), nullable=False),
        sa.Column("transaction_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("correction_of_event_id", sa.String(length=36), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "stream_sequence >= 1", name="ck_lab_bottle_event_sequence"
        ),
        sa.ForeignKeyConstraint(
            ["bottle_id"], ["lab_bottles.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["correction_of_event_id"],
            ["lab_bottle_events.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "bottle_id", "command_id", name="uq_lab_bottle_command"
        ),
        sa.UniqueConstraint(
            "id", "bottle_id", name="uq_lab_bottle_event_id_bottle"
        ),
        sa.UniqueConstraint(
            "correction_of_event_id", name="uq_lab_bottle_event_correction"
        ),
        sa.UniqueConstraint(
            "bottle_id", "stream_sequence", name="uq_lab_bottle_stream_sequence"
        ),
    )
    op.create_index(
        "ix_lab_bottle_events_transaction_id",
        "lab_bottle_events",
        ["transaction_id"],
        unique=False,
    )
    op.create_table(
        "lab_samples",
        *_record_columns(),
        sa.Column("experiment_id", sa.String(length=36), nullable=False),
        sa.Column("bottle_id", sa.String(length=36), nullable=False),
        sa.Column("blind_code", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(
            ["bottle_id"], ["lab_bottles.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["experiment_id"], ["lab_experiments.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "lab_applications",
        *_record_columns(),
        sa.Column("sample_id", sa.String(length=36), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dose_json", sa.JSON(), nullable=False),
        sa.Column("context_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["sample_id"], ["lab_samples.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "lab_bottle_event_effects",
        *_record_columns(),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("bottle_id", sa.String(length=36), nullable=False),
        sa.Column("stock_solution_id", sa.String(length=36), nullable=True),
        sa.Column("material_id", sa.String(length=36), nullable=True),
        sa.Column("mass_delta_g", sa.Float(), nullable=False),
        sa.Column("measured_volume_ul", sa.Float(), nullable=True),
        sa.Column("density_g_ml", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(
            ["event_id", "bottle_id"],
            ["lab_bottle_events.id", "lab_bottle_events.bottle_id"],
            name="fk_lab_effect_event_bottle",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["material_id"], ["lab_materials.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["stock_solution_id"], ["lab_stock_solutions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id", "stock_solution_id", name="uq_lab_effect_id_stock"
        ),
    )
    op.create_table(
        "lab_bottle_measurements",
        *_record_columns(),
        sa.Column("bottle_event_id", sa.String(length=36), nullable=False),
        sa.Column("quantity_kind", sa.String(length=80), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=40), nullable=False),
        sa.Column("standard_uncertainty", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(
            ["bottle_event_id"], ["lab_bottle_events.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "lab_pairwise_comparisons",
        *_record_columns(),
        sa.Column("experiment_id", sa.String(length=36), nullable=False),
        sa.Column("left_sample_id", sa.String(length=36), nullable=False),
        sa.Column("right_sample_id", sa.String(length=36), nullable=False),
        sa.Column("preferred_sample_id", sa.String(length=36), nullable=True),
        sa.Column("context_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["experiment_id"], ["lab_experiments.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["left_sample_id"], ["lab_samples.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["preferred_sample_id"], ["lab_samples.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["right_sample_id"], ["lab_samples.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "lab_predictions",
        *_record_columns(),
        sa.Column("experiment_id", sa.String(length=36), nullable=False),
        sa.Column("sample_id", sa.String(length=36), nullable=True),
        sa.Column("model_key", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("prediction_json", sa.JSON(), nullable=False),
        sa.Column("evidence_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(
            ["evidence_id"], ["lab_evidence_records.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["experiment_id"], ["lab_experiments.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["sample_id"], ["lab_samples.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "lab_inventory_movements",
        *_record_columns(),
        sa.Column("stock_solution_id", sa.String(length=36), nullable=False),
        sa.Column("event_effect_id", sa.String(length=36), nullable=True),
        sa.Column("mass_delta_g", sa.Float(), nullable=False),
        sa.Column("measured_volume_ul", sa.Float(), nullable=True),
        sa.Column("reason", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(
            ["event_effect_id", "stock_solution_id"],
            ["lab_bottle_event_effects.id", "lab_bottle_event_effects.stock_solution_id"],
            name="fk_lab_inventory_effect_stock",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "event_effect_id", name="uq_lab_inventory_event_effect"
        ),
    )
    op.create_table(
        "lab_observations",
        *_record_columns(),
        sa.Column("application_id", sa.String(length=36), nullable=False),
        sa.Column("elapsed_seconds", sa.Float(), nullable=False),
        sa.Column("observations_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"], ["lab_applications.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "lab_outcomes",
        *_record_columns(),
        sa.Column("prediction_id", sa.String(length=36), nullable=True),
        sa.Column("experiment_id", sa.String(length=36), nullable=False),
        sa.Column("outcome_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["experiment_id"], ["lab_experiments.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["prediction_id"], ["lab_predictions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    for table_name in APPEND_ONLY_TABLES:
        for operation in ("update", "delete"):
            op.execute(
                f"""CREATE TRIGGER {_trigger_name(operation, table_name)}
                    BEFORE {operation.upper()} ON {table_name}
                    BEGIN
                        SELECT RAISE(ABORT, 'append-only: {table_name}');
                    END"""
            )


def downgrade() -> None:
    for table_name in APPEND_ONLY_TABLES:
        for operation in ("update", "delete"):
            op.execute(f"DROP TRIGGER {_trigger_name(operation, table_name)}")

    op.drop_table("lab_outcomes")
    op.drop_table("lab_observations")
    op.drop_table("lab_inventory_movements")
    op.drop_table("lab_predictions")
    op.drop_table("lab_pairwise_comparisons")
    op.drop_table("lab_bottle_measurements")
    op.drop_table("lab_bottle_event_effects")
    op.drop_table("lab_applications")
    op.drop_table("lab_samples")
    op.drop_index("ix_lab_bottle_events_transaction_id", table_name="lab_bottle_events")
    op.drop_table("lab_bottle_events")
    op.drop_table("lab_bottles")
    op.drop_table("lab_formula_components")
    op.drop_table("lab_batches")
    op.drop_table("lab_stock_solutions")
    op.drop_table("lab_restrictions")
    op.drop_table("lab_material_properties")
    op.drop_table("lab_material_aliases")
    op.drop_table("lab_formula_versions")
    op.drop_table("lab_constituents")
    op.drop_index("ix_lab_materials_cas_number", table_name="lab_materials")
    op.drop_table("lab_materials")
    op.drop_index("ix_lab_formulas_name", table_name="lab_formulas")
    op.drop_table("lab_formulas")
    op.drop_table("lab_experiments")
    op.drop_index(
        "ix_lab_evidence_records_claim_key", table_name="lab_evidence_records"
    )
    op.drop_table("lab_evidence_records")
