"""Checkpoint-2 exact physical binding and compounding receipt records."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.lab import LabRecord, UTCDateTime

PHYSICAL_AMOUNT_UNITS = ("g", "mg", "mL", "uL")
PHYSICAL_OPERATIONS = (
    "PRECHARGE",
    "DIRECT_ADD",
    "POSTCHARGE",
    "MASS_ADD",
)
COMPOUNDING_COMMAND_TYPES = (
    "TRANSFER",
    "CANCEL",
    "RUN_COMPLETE",
)
COMPOUNDING_COMMAND_STATUSES = (
    "COMPLETED",
    "CANCELLED",
    "HOLD",
    "REJECTED",
)


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


_FALSE_AUTHORITY_CHECK = (
    "release_authority = 0 AND safety_authority = 0 "
    "AND compounding_authority = 0"
)


class LabBuildPlanPhysicalBinding(LabRecord):
    __tablename__ = "lab_build_plan_physical_bindings"
    __table_args__ = (
        UniqueConstraint(
            "build_plan_version_id",
            name="uq_lab_build_plan_physical_binding_version",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_build_plan_physical_binding_hash",
        ),
        CheckConstraint(
            "length(formula_sha256) = 64 AND "
            "length(inventory_snapshot_sha256) = 64 AND "
            "length(order_sha256) = 64 AND length(content_sha256) = 64",
            name="ck_lab_build_plan_physical_binding_hashes",
        ),
        CheckConstraint(
            "(immediate_parent_formula_version_id IS NULL AND "
            "immediate_parent_sha256 IS NULL) OR "
            "(immediate_parent_formula_version_id IS NOT NULL AND "
            "length(immediate_parent_sha256) = 64)",
            name="ck_lab_build_plan_physical_parent_shape",
        ),
        CheckConstraint(
            _FALSE_AUTHORITY_CHECK,
            name="ck_lab_build_plan_physical_no_authority",
        ),
    )

    build_plan_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_build_plan_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    formula_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_formula_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    formula_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    immediate_parent_formula_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_formula_versions.id", ondelete="RESTRICT")
    )
    immediate_parent_sha256: Mapped[str | None] = mapped_column(String(64))
    inventory_snapshot_ref: Mapped[str] = mapped_column(Text, nullable=False)
    inventory_snapshot_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    stock_lineage_receipts_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    release_authority_receipt_ids_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    order_policy: Mapped[str] = mapped_column(String(120), nullable=False)
    order_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    release_authority: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )
    safety_authority: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )
    compounding_authority: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )


class LabStockLotPhysicalReceipt(LabRecord):
    """Immutable lot/bottle/homogeneity evidence for one stock identity.

    A corrected physical assertion requires a new stock identity; existing
    receipt bytes are never overwritten.
    """

    __tablename__ = "lab_stock_lot_physical_receipts"
    __table_args__ = (
        UniqueConstraint(
            "stock_solution_id",
            name="uq_lab_stock_lot_physical_receipt_stock",
        ),
        UniqueConstraint(
            "idempotency_key_sha256",
            name="uq_lab_stock_lot_physical_receipt_idempotency",
        ),
        UniqueConstraint(
            "content_sha256",
            name="uq_lab_stock_lot_physical_receipt_content",
        ),
        CheckConstraint(
            "preparation_state IN ('SUPPLIER_AS_SUPPLIED', 'LOCALLY_PREPARED')",
            name="ck_lab_stock_lot_physical_preparation_state",
        ),
        CheckConstraint(
            "homogeneity_state IN ('CONFIRMED', 'NOT_APPLICABLE')",
            name="ck_lab_stock_lot_physical_homogeneity",
        ),
        CheckConstraint(
            "(preparation_state = 'LOCALLY_PREPARED' AND "
            "stock_preparation_receipt_id IS NOT NULL) OR "
            "(preparation_state = 'SUPPLIER_AS_SUPPLIED' AND "
            "stock_preparation_receipt_id IS NULL)",
            name="ck_lab_stock_lot_physical_preparation_receipt_shape",
        ),
        CheckConstraint(
            "length(idempotency_key_sha256) = 64 AND "
            "length(command_sha256) = 64 AND length(content_sha256) = 64",
            name="ck_lab_stock_lot_physical_hashes",
        ),
        CheckConstraint(
            _FALSE_AUTHORITY_CHECK,
            name="ck_lab_stock_lot_physical_no_authority",
        ),
    )

    stock_solution_id: Mapped[str] = mapped_column(
        ForeignKey("lab_stock_solutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    supplier: Mapped[str] = mapped_column(String(255), nullable=False)
    lot_number: Mapped[str] = mapped_column(String(100), nullable=False)
    bottle_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    active_fraction_decimal: Mapped[str] = mapped_column(
        String(128), nullable=False
    )
    fraction_basis: Mapped[str] = mapped_column(String(80), nullable=False)
    carrier: Mapped[str | None] = mapped_column(String(255))
    density_g_ml_decimal: Mapped[str | None] = mapped_column(String(128))
    density_provenance: Mapped[str | None] = mapped_column(Text)
    preparation_state: Mapped[str] = mapped_column(String(40), nullable=False)
    stock_preparation_receipt_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_stock_preparation_receipts.id", ondelete="RESTRICT")
    )
    homogeneity_state: Mapped[str] = mapped_column(String(30), nullable=False)
    source_reference: Mapped[str] = mapped_column(Text, nullable=False)
    reviewer: Mapped[str] = mapped_column(String(255), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(
        UTCDateTime(timezone=True), nullable=False
    )
    idempotency_key_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    command_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    release_authority: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )
    safety_authority: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )
    compounding_authority: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )


class LabStockPreparationReceipt(LabRecord):
    __tablename__ = "lab_stock_preparation_receipts"
    __table_args__ = (
        UniqueConstraint(
            "idempotency_key_sha256",
            name="uq_lab_stock_preparation_idempotency",
        ),
        UniqueConstraint(
            "content_sha256", name="uq_lab_stock_preparation_content"
        ),
        CheckConstraint(
            "basis IN ('W_W', 'V_V')",
            name="ck_lab_stock_preparation_basis",
        ),
        CheckConstraint(
            f"parent_quantity_unit IN ({_quoted(PHYSICAL_AMOUNT_UNITS)}) "
            f"AND carrier_quantity_unit IN ({_quoted(PHYSICAL_AMOUNT_UNITS)}) "
            f"AND result_quantity_unit IN ({_quoted(PHYSICAL_AMOUNT_UNITS)})",
            name="ck_lab_stock_preparation_units",
        ),
        CheckConstraint(
            "homogeneity_state IN ('CONFIRMED', 'UNKNOWN', 'FAILED')",
            name="ck_lab_stock_preparation_homogeneity",
        ),
        CheckConstraint(
            "length(idempotency_key_sha256) = 64 AND "
            "length(command_sha256) = 64 AND length(content_sha256) = 64",
            name="ck_lab_stock_preparation_hashes",
        ),
        CheckConstraint(
            _FALSE_AUTHORITY_CHECK,
            name="ck_lab_stock_preparation_no_authority",
        ),
    )

    build_plan_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_build_plan_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    parent_stock_solution_id: Mapped[str] = mapped_column(
        ForeignKey("lab_stock_solutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    carrier_stock_solution_id: Mapped[str] = mapped_column(
        ForeignKey("lab_stock_solutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    prepared_stock_solution_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_stock_solutions.id", ondelete="RESTRICT")
    )
    basis: Mapped[str] = mapped_column(String(20), nullable=False)
    parent_quantity_decimal: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_quantity_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    carrier_quantity_decimal: Mapped[str] = mapped_column(String(128), nullable=False)
    carrier_quantity_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    result_quantity_decimal: Mapped[str] = mapped_column(String(128), nullable=False)
    result_quantity_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    resulting_active_fraction_decimal: Mapped[str] = mapped_column(
        String(128), nullable=False
    )
    density_g_ml_decimal: Mapped[str | None] = mapped_column(String(128))
    density_provenance: Mapped[str | None] = mapped_column(Text)
    homogeneity_state: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    operator: Mapped[str] = mapped_column(String(255), nullable=False)
    prepared_at: Mapped[datetime] = mapped_column(
        UTCDateTime(timezone=True), nullable=False
    )
    idempotency_key_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    command_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    release_authority: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )
    safety_authority: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )
    compounding_authority: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )


class LabBuildPlanLinePhysicalBinding(LabRecord):
    __tablename__ = "lab_build_plan_line_physical_bindings"
    __table_args__ = (
        UniqueConstraint(
            "build_plan_physical_binding_id",
            "command_sequence",
            name="uq_lab_build_plan_line_physical_sequence",
        ),
        UniqueConstraint(
            "build_plan_physical_binding_id",
            "build_plan_line_id",
            name="uq_lab_build_plan_line_physical_line",
        ),
        UniqueConstraint(
            "command_identity_sha256",
            name="uq_lab_build_plan_line_physical_command",
        ),
        CheckConstraint(
            "length(basket) >= 2 AND command_sequence >= 1",
            name="ck_lab_build_plan_line_physical_order",
        ),
        CheckConstraint(
            f"operation IN ({_quoted(PHYSICAL_OPERATIONS)})",
            name="ck_lab_build_plan_line_physical_operation",
        ),
        CheckConstraint(
            f"amount_unit IN ({_quoted(PHYSICAL_AMOUNT_UNITS)})",
            name="ck_lab_build_plan_line_physical_unit",
        ),
        CheckConstraint(
            "length(command_identity_sha256) = 64 AND "
            "length(content_sha256) = 64",
            name="ck_lab_build_plan_line_physical_hashes",
        ),
        CheckConstraint(
            _FALSE_AUTHORITY_CHECK,
            name="ck_lab_build_plan_line_physical_no_authority",
        ),
    )

    build_plan_physical_binding_id: Mapped[str] = mapped_column(
        ForeignKey("lab_build_plan_physical_bindings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    build_plan_line_id: Mapped[str] = mapped_column(
        ForeignKey("lab_build_plan_lines.id", ondelete="RESTRICT"),
        nullable=False,
    )
    formula_component_id: Mapped[str] = mapped_column(
        ForeignKey("lab_formula_components.id", ondelete="RESTRICT"),
        nullable=False,
    )
    basket: Mapped[str] = mapped_column(String(40), nullable=False)
    operation: Mapped[str] = mapped_column(String(30), nullable=False)
    stock_solution_id: Mapped[str] = mapped_column(
        ForeignKey("lab_stock_solutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    concentration_fraction_decimal: Mapped[str] = mapped_column(
        String(128), nullable=False
    )
    concentration_basis: Mapped[str] = mapped_column(String(80), nullable=False)
    carrier: Mapped[str | None] = mapped_column(String(255))
    stock_preparation_receipt_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_stock_preparation_receipts.id", ondelete="RESTRICT")
    )
    amount_decimal: Mapped[str] = mapped_column(String(128), nullable=False)
    amount_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    density_g_ml_decimal: Mapped[str | None] = mapped_column(String(128))
    density_provenance: Mapped[str | None] = mapped_column(Text)
    command_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    command_identity_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    release_authority: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )
    safety_authority: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )
    compounding_authority: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )


class LabCompoundingRun(LabRecord):
    __tablename__ = "lab_compounding_runs"
    __table_args__ = (
        UniqueConstraint(
            "logical_plan_id", name="uq_lab_compounding_run_logical_plan"
        ),
        UniqueConstraint(
            "content_sha256", name="uq_lab_compounding_run_content"
        ),
        CheckConstraint(
            "length(order_sha256) = 64 AND length(content_sha256) = 64",
            name="ck_lab_compounding_run_hashes",
        ),
        CheckConstraint(
            _FALSE_AUTHORITY_CHECK,
            name="ck_lab_compounding_run_no_authority",
        ),
    )

    logical_plan_id: Mapped[str] = mapped_column(String(36), nullable=False)
    build_plan_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_build_plan_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    physical_binding_id: Mapped[str] = mapped_column(
        ForeignKey("lab_build_plan_physical_bindings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    order_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    operator: Mapped[str] = mapped_column(String(255), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        UTCDateTime(timezone=True), nullable=False
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    release_authority: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )
    safety_authority: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )
    compounding_authority: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )


class LabCompoundingCommandReceipt(LabRecord):
    __tablename__ = "lab_compounding_command_receipts"
    __table_args__ = (
        UniqueConstraint(
            "compounding_run_id",
            "sequence",
            name="uq_lab_compounding_receipt_sequence",
        ),
        UniqueConstraint(
            "compounding_run_id",
            "command_id",
            name="uq_lab_compounding_receipt_command",
        ),
        UniqueConstraint(
            "idempotency_key_sha256",
            name="uq_lab_compounding_receipt_idempotency",
        ),
        UniqueConstraint(
            "receipt_sha256", name="uq_lab_compounding_receipt_hash"
        ),
        CheckConstraint(
            "sequence >= 1",
            name="ck_lab_compounding_receipt_sequence",
        ),
        CheckConstraint(
            f"command_type IN ({_quoted(COMPOUNDING_COMMAND_TYPES)})",
            name="ck_lab_compounding_receipt_type",
        ),
        CheckConstraint(
            f"status IN ({_quoted(COMPOUNDING_COMMAND_STATUSES)})",
            name="ck_lab_compounding_receipt_status",
        ),
        CheckConstraint(
            "amount_unit IS NULL OR amount_unit IN "
            f"({_quoted(PHYSICAL_AMOUNT_UNITS)})",
            name="ck_lab_compounding_receipt_unit",
        ),
        CheckConstraint(
            "length(idempotency_key_sha256) = 64 AND "
            "length(command_sha256) = 64 AND length(receipt_sha256) = 64 "
            "AND (parent_receipt_sha256 IS NULL OR "
            "length(parent_receipt_sha256) = 64)",
            name="ck_lab_compounding_receipt_hashes",
        ),
        CheckConstraint(
            _FALSE_AUTHORITY_CHECK,
            name="ck_lab_compounding_receipt_no_authority",
        ),
    )

    compounding_run_id: Mapped[str] = mapped_column(
        ForeignKey("lab_compounding_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    command_id: Mapped[str] = mapped_column(String(80), nullable=False)
    command_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    line_physical_binding_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "lab_build_plan_line_physical_bindings.id",
            ondelete="RESTRICT",
        )
    )
    bottle_action_commit_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_bottle_action_commits.id", ondelete="RESTRICT")
    )
    reservation_event_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_inventory_reservation_events.id", ondelete="RESTRICT")
    )
    stock_solution_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_stock_solutions.id", ondelete="RESTRICT")
    )
    amount_decimal: Mapped[str | None] = mapped_column(String(128))
    amount_unit: Mapped[str | None] = mapped_column(String(20))
    operator: Mapped[str] = mapped_column(String(255), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(
        UTCDateTime(timezone=True), nullable=False
    )
    detail_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    idempotency_key_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    command_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_receipt_sha256: Mapped[str | None] = mapped_column(String(64))
    receipt_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    release_authority: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )
    safety_authority: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )
    compounding_authority: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )


CP2_PHYSICAL_TABLE_NAMES = {
    "lab_build_plan_physical_bindings",
    "lab_build_plan_line_physical_bindings",
    "lab_stock_preparation_receipts",
    "lab_compounding_runs",
    "lab_compounding_command_receipts",
}

CP18_STOCK_LOT_TABLE_NAMES = {
    "lab_stock_lot_physical_receipts",
}

PHYSICAL_LINEAGE_TABLE_NAMES = (
    CP2_PHYSICAL_TABLE_NAMES | CP18_STOCK_LOT_TABLE_NAMES
)


__all__ = [
    "COMPOUNDING_COMMAND_STATUSES",
    "COMPOUNDING_COMMAND_TYPES",
    "CP18_STOCK_LOT_TABLE_NAMES",
    "CP2_PHYSICAL_TABLE_NAMES",
    "LabBuildPlanLinePhysicalBinding",
    "LabBuildPlanPhysicalBinding",
    "LabCompoundingCommandReceipt",
    "LabCompoundingRun",
    "LabStockLotPhysicalReceipt",
    "LabStockPreparationReceipt",
    "PHYSICAL_AMOUNT_UNITS",
    "PHYSICAL_LINEAGE_TABLE_NAMES",
    "PHYSICAL_OPERATIONS",
]
