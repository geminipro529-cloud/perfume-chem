"""Canonical local laboratory schema with immutable scientific history."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from app.models.base import Base

INVENTORY_MOVEMENT_TYPES = (
    "RESERVATION",
    "RESERVATION_RELEASE",
    "CONSUMPTION",
    "RETURN",
    "ADJUSTMENT",
    "TRANSFER",
    "CORRECTION",
    "REVERSAL",
)


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _uuid() -> str:
    return str(uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator[datetime]):
    """Store UTC in SQLite while restoring an aware value on every read."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("UTCDateTime values must be timezone-aware")
        utc_value = value.astimezone(timezone.utc)
        if dialect.name == "sqlite":
            return utc_value.replace(tzinfo=None)
        return utc_value

    def process_result_value(self, value, _dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class LabRecord(Base):
    __abstract__ = True

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(timezone=True), default=_utcnow, nullable=False
    )


class LabEvidenceRecord(LabRecord):
    __tablename__ = "lab_evidence_records"

    claim_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    classification: Mapped[str] = mapped_column(String(40), nullable=False)
    source_locator: Mapped[str] = mapped_column(Text, nullable=False)
    source_version: Mapped[str | None] = mapped_column(String(100))
    method: Mapped[str | None] = mapped_column(Text)
    assumptions_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    limitations_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    payload_sha256: Mapped[str | None] = mapped_column(String(64))


class LabMaterial(LabRecord):
    __tablename__ = "lab_materials"

    canonical_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    cas_number: Mapped[str | None] = mapped_column(String(50), index=True)
    original_payload_json: Mapped[dict | None] = mapped_column(JSON)


class LabMaterialAlias(LabRecord):
    __tablename__ = "lab_material_aliases"
    __table_args__ = (UniqueConstraint("normalized_alias", name="uq_lab_material_alias"),)

    material_id: Mapped[str] = mapped_column(
        ForeignKey("lab_materials.id", ondelete="RESTRICT"), nullable=False
    )
    alias: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(255), nullable=False)


class LabMaterialProperty(LabRecord):
    __tablename__ = "lab_material_properties"

    material_id: Mapped[str] = mapped_column(
        ForeignKey("lab_materials.id", ondelete="RESTRICT"), nullable=False
    )
    property_key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(80), nullable=False)
    conditions_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    standard_uncertainty: Mapped[float | None] = mapped_column(Float)
    evidence_id: Mapped[str] = mapped_column(
        ForeignKey("lab_evidence_records.id", ondelete="RESTRICT"), nullable=False
    )


class LabRestriction(LabRecord):
    __tablename__ = "lab_restrictions"

    material_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_materials.id", ondelete="RESTRICT")
    )
    substance_name: Mapped[str] = mapped_column(String(255), nullable=False)
    standard_source: Mapped[str] = mapped_column(String(255), nullable=False)
    amendment: Mapped[str] = mapped_column(String(80), nullable=False)
    product_category: Mapped[str] = mapped_column(String(80), nullable=False)
    concentration_basis: Mapped[str] = mapped_column(String(80), nullable=False)
    maximum_fraction: Mapped[float | None] = mapped_column(Float)
    restriction_type: Mapped[str] = mapped_column(String(40), nullable=False)
    evidence_id: Mapped[str] = mapped_column(
        ForeignKey("lab_evidence_records.id", ondelete="RESTRICT"), nullable=False
    )


class LabConstituent(LabRecord):
    __tablename__ = "lab_constituents"

    parent_material_id: Mapped[str] = mapped_column(
        ForeignKey("lab_materials.id", ondelete="RESTRICT"), nullable=False
    )
    constituent_name: Mapped[str] = mapped_column(String(255), nullable=False)
    cas_number: Mapped[str | None] = mapped_column(String(50))
    fraction: Mapped[float] = mapped_column(Float, nullable=False)
    fraction_basis: Mapped[str] = mapped_column(String(80), nullable=False)
    evidence_id: Mapped[str] = mapped_column(
        ForeignKey("lab_evidence_records.id", ondelete="RESTRICT"), nullable=False
    )


class LabStockSolution(LabRecord):
    __tablename__ = "lab_stock_solutions"

    material_id: Mapped[str] = mapped_column(
        ForeignKey("lab_materials.id", ondelete="RESTRICT"), nullable=False
    )
    supplier: Mapped[str | None] = mapped_column(String(255))
    lot_number: Mapped[str | None] = mapped_column(String(100))
    active_fraction: Mapped[float] = mapped_column(Float, nullable=False)
    fraction_basis: Mapped[str] = mapped_column(String(80), nullable=False)
    density_g_ml: Mapped[float | None] = mapped_column(Float)
    solvent_name: Mapped[str | None] = mapped_column(String(255))
    initial_mass_g: Mapped[float] = mapped_column(Float, nullable=False)
    remaining_mass_g: Mapped[float | None] = mapped_column(Float)
    source_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class LabFormula(LabRecord):
    __tablename__ = "lab_formulas"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)


class LabFormulaVersion(LabRecord):
    __tablename__ = "lab_formula_versions"
    __table_args__ = (
        UniqueConstraint("formula_id", "version_number", name="uq_lab_formula_version"),
    )

    formula_id: Mapped[str] = mapped_column(
        ForeignKey("lab_formulas.id", ondelete="RESTRICT"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    brief_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    constraints_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    concentration_fraction: Mapped[float | None] = mapped_column(Float)
    concentration_basis: Mapped[str | None] = mapped_column(String(80))
    source_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )


class LabFormulaComponent(LabRecord):
    __tablename__ = "lab_formula_components"
    __table_args__ = (
        UniqueConstraint(
            "formula_version_id", "position", name="uq_lab_formula_component_position"
        ),
    )

    formula_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_formula_versions.id", ondelete="RESTRICT"), nullable=False
    )
    stock_solution_id: Mapped[str] = mapped_column(
        ForeignKey("lab_stock_solutions.id", ondelete="RESTRICT"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    requested_mass_g: Mapped[float] = mapped_column(Float, nullable=False)
    requested_volume_ul: Mapped[float | None] = mapped_column(Float)
    role: Mapped[str | None] = mapped_column(String(40))
    unit: Mapped[str | None] = mapped_column(String(20))


class LabBatch(LabRecord):
    __tablename__ = "lab_batches"

    formula_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_formula_versions.id", ondelete="RESTRICT"), nullable=False
    )
    batch_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    actual_mass_g: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)


class LabBottle(LabRecord):
    __tablename__ = "lab_bottles"

    label: Mapped[str] = mapped_column(String(255), nullable=False)
    batch_id: Mapped[str | None] = mapped_column(ForeignKey("lab_batches.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False)


class LabBottleEvent(LabRecord):
    __tablename__ = "lab_bottle_events"
    __table_args__ = (
        UniqueConstraint("bottle_id", "stream_sequence", name="uq_lab_bottle_stream_sequence"),
        UniqueConstraint("bottle_id", "command_id", name="uq_lab_bottle_command"),
        UniqueConstraint("id", "bottle_id", name="uq_lab_bottle_event_id_bottle"),
        UniqueConstraint("correction_of_event_id", name="uq_lab_bottle_event_correction"),
        CheckConstraint("stream_sequence >= 1", name="ck_lab_bottle_event_sequence"),
    )

    bottle_id: Mapped[str] = mapped_column(
        ForeignKey("lab_bottles.id", ondelete="RESTRICT"), nullable=False
    )
    stream_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    command_id: Mapped[str] = mapped_column(String(64), nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    correction_of_event_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_bottle_events.id", ondelete="RESTRICT")
    )
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class LabBottleEventEffect(LabRecord):
    __tablename__ = "lab_bottle_event_effects"
    __table_args__ = (
        UniqueConstraint("id", "stock_solution_id", name="uq_lab_effect_id_stock"),
        ForeignKeyConstraint(
            ["event_id", "bottle_id"],
            ["lab_bottle_events.id", "lab_bottle_events.bottle_id"],
            name="fk_lab_effect_event_bottle",
            ondelete="RESTRICT",
        ),
    )

    event_id: Mapped[str] = mapped_column(String(36), nullable=False)
    bottle_id: Mapped[str] = mapped_column(String(36), nullable=False)
    stock_solution_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_stock_solutions.id", ondelete="RESTRICT")
    )
    material_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_materials.id", ondelete="RESTRICT")
    )
    mass_delta_g: Mapped[float] = mapped_column(Float, nullable=False)
    measured_volume_ul: Mapped[float | None] = mapped_column(Float)
    density_g_ml: Mapped[float | None] = mapped_column(Float)


class LabInventoryMovement(LabRecord):
    __tablename__ = "lab_inventory_movements"
    __table_args__ = (
        UniqueConstraint("event_effect_id", name="uq_lab_inventory_event_effect"),
        UniqueConstraint(
            "idempotency_key",
            name="uq_lab_inventory_movement_idempotency",
        ),
        UniqueConstraint(
            "correction_of_movement_id",
            name="uq_lab_inventory_movement_correction",
        ),
        UniqueConstraint(
            "reversal_of_movement_id",
            name="uq_lab_inventory_movement_reversal",
        ),
        ForeignKeyConstraint(
            ["event_effect_id", "stock_solution_id"],
            ["lab_bottle_event_effects.id", "lab_bottle_event_effects.stock_solution_id"],
            name="fk_lab_inventory_effect_stock",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            f"movement_type IN ({_quoted(INVENTORY_MOVEMENT_TYPES)})",
            name="ck_lab_inventory_movement_type",
        ),
        CheckConstraint(
            "raw_quantity >= 0 AND active_quantity >= 0 "
            "AND active_quantity <= raw_quantity "
            "AND (standard_uncertainty IS NULL "
            "OR standard_uncertainty >= 0)",
            name="ck_lab_inventory_movement_quantities",
        ),
        CheckConstraint(
            "balance_before >= 0 AND balance_after >= 0",
            name="ck_lab_inventory_movement_balances",
        ),
        CheckConstraint(
            "NOT (correction_of_movement_id IS NOT NULL "
            "AND reversal_of_movement_id IS NOT NULL) "
            "AND ((movement_type = 'CORRECTION' "
            "AND correction_of_movement_id IS NOT NULL) "
            "OR (movement_type != 'CORRECTION' "
            "AND correction_of_movement_id IS NULL)) "
            "AND ((movement_type = 'REVERSAL' "
            "AND reversal_of_movement_id IS NOT NULL) "
            "OR (movement_type != 'REVERSAL' "
            "AND reversal_of_movement_id IS NULL))",
            name="ck_lab_inventory_movement_reference",
        ),
        CheckConstraint(
            "build_plan_line_id IS NOT NULL "
            "OR reservation_event_id IS NOT NULL "
            "OR bottle_event_id IS NOT NULL "
            "OR event_effect_id IS NOT NULL "
            "OR admin_cause IS NOT NULL",
            name="ck_lab_inventory_movement_cause",
        ),
    )

    stock_solution_id: Mapped[str] = mapped_column(String(36), nullable=False)
    event_effect_id: Mapped[str | None] = mapped_column(String(36))
    build_plan_line_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_build_plan_lines.id", ondelete="RESTRICT")
    )
    reservation_event_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_inventory_reservation_events.id", ondelete="RESTRICT")
    )
    bottle_event_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_bottle_events.id", ondelete="RESTRICT")
    )
    movement_type: Mapped[str] = mapped_column(String(40), nullable=False)
    raw_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    active_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False)
    basis: Mapped[str] = mapped_column(String(80), nullable=False)
    balance_before: Mapped[float] = mapped_column(Float, nullable=False)
    balance_after: Mapped[float] = mapped_column(Float, nullable=False)
    standard_uncertainty: Mapped[float | None] = mapped_column(Float)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    transaction_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    admin_cause: Mapped[str | None] = mapped_column(Text)
    correction_of_movement_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_inventory_movements.id", ondelete="RESTRICT")
    )
    reversal_of_movement_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_inventory_movements.id", ondelete="RESTRICT")
    )
    mass_delta_g: Mapped[float] = mapped_column(Float, nullable=False)
    measured_volume_ul: Mapped[float | None] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(String(100), nullable=False)


class LabBottleMeasurement(LabRecord):
    __tablename__ = "lab_bottle_measurements"
    __table_args__ = (
        UniqueConstraint(
            "proposal_id",
            "quantity_kind",
            name="uq_lab_bottle_measurement_proposal_kind",
        ),
        CheckConstraint(
            "(bottle_event_id IS NOT NULL AND proposal_id IS NULL) OR "
            "(bottle_event_id IS NULL AND proposal_id IS NOT NULL "
            "AND method IS NOT NULL AND measured_at IS NOT NULL "
            "AND actor IS NOT NULL)",
            name="ck_lab_bottle_measurement_authority",
        ),
    )

    bottle_event_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_bottle_events.id", ondelete="RESTRICT")
    )
    proposal_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_bottle_action_proposals.id", ondelete="RESTRICT")
    )
    quantity_kind: Mapped[str] = mapped_column(String(80), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False)
    standard_uncertainty: Mapped[float | None] = mapped_column(Float)
    method: Mapped[str | None] = mapped_column(String(100))
    measured_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(timezone=True)
    )
    actor: Mapped[str | None] = mapped_column(String(255))


class LabExperiment(LabRecord):
    __tablename__ = "lab_experiments"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    protocol_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="planned", nullable=False)


class LabSample(LabRecord):
    __tablename__ = "lab_samples"

    experiment_id: Mapped[str] = mapped_column(
        ForeignKey("lab_experiments.id", ondelete="RESTRICT"), nullable=False
    )
    bottle_id: Mapped[str] = mapped_column(
        ForeignKey("lab_bottles.id", ondelete="RESTRICT"), nullable=False
    )
    blind_code: Mapped[str] = mapped_column(String(100), nullable=False)


class LabApplication(LabRecord):
    __tablename__ = "lab_applications"

    sample_id: Mapped[str] = mapped_column(
        ForeignKey("lab_samples.id", ondelete="RESTRICT"), nullable=False
    )
    applied_at: Mapped[datetime] = mapped_column(UTCDateTime(timezone=True), nullable=False)
    dose_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    context_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class LabObservation(LabRecord):
    __tablename__ = "lab_observations"

    application_id: Mapped[str] = mapped_column(
        ForeignKey("lab_applications.id", ondelete="RESTRICT"), nullable=False
    )
    elapsed_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    observations_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class LabPairwiseComparison(LabRecord):
    __tablename__ = "lab_pairwise_comparisons"

    experiment_id: Mapped[str] = mapped_column(
        ForeignKey("lab_experiments.id", ondelete="RESTRICT"), nullable=False
    )
    left_sample_id: Mapped[str] = mapped_column(
        ForeignKey("lab_samples.id", ondelete="RESTRICT"), nullable=False
    )
    right_sample_id: Mapped[str] = mapped_column(
        ForeignKey("lab_samples.id", ondelete="RESTRICT"), nullable=False
    )
    preferred_sample_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_samples.id", ondelete="RESTRICT")
    )
    context_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class LabPrediction(LabRecord):
    __tablename__ = "lab_predictions"

    experiment_id: Mapped[str] = mapped_column(
        ForeignKey("lab_experiments.id", ondelete="RESTRICT"), nullable=False
    )
    sample_id: Mapped[str | None] = mapped_column(ForeignKey("lab_samples.id", ondelete="RESTRICT"))
    model_key: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    prediction_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    evidence_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_evidence_records.id", ondelete="RESTRICT")
    )


class LabOutcome(LabRecord):
    __tablename__ = "lab_outcomes"

    prediction_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_predictions.id", ondelete="RESTRICT")
    )
    experiment_id: Mapped[str] = mapped_column(
        ForeignKey("lab_experiments.id", ondelete="RESTRICT"), nullable=False
    )
    outcome_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


from app.models.lab_execution import (  # noqa: E402,F401
    EXECUTION_TABLE_NAMES,
    LabBottleActionCommit,
    LabBottleActionConfirmation,
    LabBottleActionProposal,
)
from app.models.lab_planning import (  # noqa: E402,F401
    PLANNING_TABLE_NAMES,
    LabAcceptedTargetVersion,
    LabBuildPlanEvidenceLink,
    LabBuildPlanLine,
    LabBuildPlanVersion,
    LabFormulaVersionEdge,
    LabInventoryMappingEvidenceLink,
    LabInventoryMappingVersion,
    LabInventoryReservationEvent,
    LabTargetEvidenceLink,
    LabTargetHypothesisVersion,
    LabTargetLine,
)
from app.models.lab_science import (  # noqa: E402,F401
    SCIENCE_AUTHORITY_TABLE_NAMES,
    LabAnalyticalAttachment,
    LabAnalyticalMethodVersion,
    LabAnalyticalPeak,
    LabAnalyticalQCRecord,
    LabAnalyticalRun,
    LabClaimAssessmentEvidenceLink,
    LabClaimAssessmentVersion,
    LabGCOEvent,
    LabRegulatoryAssessmentVersion,
    LabRegulatoryFinding,
)
from app.models.lab_sources import (  # noqa: E402,F401
    SOURCE_AUTHORITY_TABLE_NAMES,
    LabEvidenceWorkflowEvent,
    LabSourceDerivationLink,
    LabSourceDocumentVersion,
    LabSourceExtractionRecord,
)

LAB_TABLE_NAMES = {
    table.name for table in Base.metadata.sorted_tables if table.name.startswith("lab_")
}

APPEND_ONLY_TABLES = {
    "lab_evidence_records",
    "lab_formula_versions",
    "lab_formula_components",
    "lab_bottle_events",
    "lab_bottle_event_effects",
    "lab_inventory_movements",
    "lab_bottle_measurements",
    "lab_observations",
    "lab_pairwise_comparisons",
    "lab_predictions",
    "lab_outcomes",
    *PLANNING_TABLE_NAMES,
    *SCIENCE_AUTHORITY_TABLE_NAMES,
    *SOURCE_AUTHORITY_TABLE_NAMES,
    *EXECUTION_TABLE_NAMES,
}


__all__ = [name for name in globals() if name.startswith("Lab")] + [
    "APPEND_ONLY_TABLES",
    "INVENTORY_MOVEMENT_TYPES",
    "LAB_TABLE_NAMES",
]
