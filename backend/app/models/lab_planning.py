"""Append-oriented A2 planning records for the canonical laboratory schema."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
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

from app.models.lab import LabRecord, UTCDateTime

BUILD_PLAN_STATUSES = (
    "DRAFT",
    "UNDER_REVIEW",
    "APPROVED",
    "RESERVED",
    "EXECUTING",
    "CLOSED",
    "SUPERSEDED",
    "CANCELLED",
)
RESERVATION_STATES = ("RESERVED", "RELEASED", "FULFILLED", "CANCELLED")
UNAVAILABLE_INVENTORY_STATUSES = (
    "EXACT_IDENTITY_NOT_IN_STOCK",
    "NO_SUITABLE_STOCK",
)


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


class LabTargetHypothesisVersion(LabRecord):
    __tablename__ = "lab_target_hypothesis_versions"
    __table_args__ = (
        UniqueConstraint(
            "target_id", "version_number", name="uq_lab_target_version"
        ),
        UniqueConstraint(
            "content_sha256", name="uq_lab_target_version_content_sha256"
        ),
        CheckConstraint(
            "version_number >= 1", name="ck_lab_target_version_positive"
        ),
    )

    target_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    product_key: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_target_hypothesis_versions.id", ondelete="RESTRICT")
    )
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    provenance_activity_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    uncertainty_summary_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_sha256: Mapped[str | None] = mapped_column(String(64))


class LabTargetLine(LabRecord):
    __tablename__ = "lab_target_lines"
    __table_args__ = (
        UniqueConstraint(
            "target_hypothesis_version_id",
            "position",
            name="uq_lab_target_line_position",
        ),
        UniqueConstraint(
            "target_hypothesis_version_id",
            "line_id",
            name="uq_lab_target_line_identity",
        ),
        UniqueConstraint(
            "id",
            "target_hypothesis_version_id",
            name="uq_lab_target_line_id_version",
        ),
        CheckConstraint(
            "position >= 1 AND target_raw_quantity >= 0 "
            "AND target_active_quantity >= 0 "
            "AND target_active_quantity <= target_raw_quantity",
            name="ck_lab_target_line_quantities",
        ),
        CheckConstraint(
            "presence_probability >= 0 AND presence_probability <= 1 "
            "AND concentration_fraction >= 0 AND concentration_fraction <= 1",
            name="ck_lab_target_line_fractions",
        ),
    )

    line_id: Mapped[str] = mapped_column(String(255), nullable=False)
    target_hypothesis_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_target_hypothesis_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    target_identity: Mapped[str] = mapped_column(String(255), nullable=False)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    grade: Mapped[str] = mapped_column(String(100), nullable=False)
    presence_probability: Mapped[float] = mapped_column(Float, nullable=False)
    target_raw_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    target_active_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False)
    concentration_fraction: Mapped[float] = mapped_column(Float, nullable=False)
    concentration_basis: Mapped[str] = mapped_column(String(80), nullable=False)
    functional_roles_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    uncertainty_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )


class LabTargetEvidenceLink(LabRecord):
    __tablename__ = "lab_target_evidence_links"
    __table_args__ = (
        UniqueConstraint(
            "target_hypothesis_version_id",
            "target_line_id",
            "evidence_record_id",
            name="uq_lab_target_evidence_link",
        ),
        ForeignKeyConstraint(
            ["target_line_id", "target_hypothesis_version_id"],
            [
                "lab_target_lines.id",
                "lab_target_lines.target_hypothesis_version_id",
            ],
            name="fk_lab_target_evidence_line_version",
            ondelete="RESTRICT",
        ),
    )

    target_hypothesis_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_target_hypothesis_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    target_line_id: Mapped[str | None] = mapped_column(String(36))
    evidence_record_id: Mapped[str] = mapped_column(
        ForeignKey("lab_evidence_records.id", ondelete="RESTRICT"), nullable=False
    )


class LabAcceptedTargetVersion(LabRecord):
    __tablename__ = "lab_accepted_target_versions"
    __table_args__ = (
        UniqueConstraint(
            "target_hypothesis_version_id",
            name="uq_lab_accepted_target_version",
        ),
        UniqueConstraint(
            "accepted_target_id",
            "version_number",
            name="uq_lab_accepted_target_identity",
        ),
        UniqueConstraint(
            "id",
            "target_hypothesis_version_id",
            name="uq_lab_accepted_target_id_target",
        ),
        CheckConstraint(
            "version_number >= 1", name="ck_lab_accepted_target_version_positive"
        ),
    )

    accepted_target_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    target_hypothesis_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_target_hypothesis_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    parent_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_accepted_target_versions.id", ondelete="RESTRICT")
    )
    reviewer: Mapped[str] = mapped_column(String(255), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_sha256: Mapped[str | None] = mapped_column(String(64))


class LabFormulaVersionEdge(LabRecord):
    __tablename__ = "lab_formula_version_edges"
    __table_args__ = (
        UniqueConstraint(
            "child_version_id",
            "parent_version_id",
            name="uq_lab_formula_version_edge",
        ),
        CheckConstraint(
            "child_version_id <> parent_version_id",
            name="ck_lab_formula_version_edge_not_self",
        ),
    )

    child_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_formula_versions.id", ondelete="RESTRICT"), nullable=False
    )
    parent_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_formula_versions.id", ondelete="RESTRICT"), nullable=False
    )
    relationship_kind: Mapped[str] = mapped_column(String(80), nullable=False)
    change_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class LabInventoryMappingVersion(LabRecord):
    __tablename__ = "lab_inventory_mapping_versions"
    __table_args__ = (
        UniqueConstraint(
            "mapping_id", "version_number", name="uq_lab_mapping_version"
        ),
        CheckConstraint(
            "version_number >= 1", name="ck_lab_mapping_version_positive"
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_lab_mapping_confidence",
        ),
        CheckConstraint(
            "("
            "stock_solution_id IS NOT NULL AND inventory_status NOT IN "
            f"({_quoted(UNAVAILABLE_INVENTORY_STATUSES)})"
            ") OR ("
            "stock_solution_id IS NULL AND inventory_status IN "
            f"({_quoted(UNAVAILABLE_INVENTORY_STATUSES)})"
            ")",
            name="ck_lab_mapping_stock_status",
        ),
    )

    mapping_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_inventory_mapping_versions.id", ondelete="RESTRICT")
    )
    target_line_id: Mapped[str] = mapped_column(
        ForeignKey("lab_target_lines.id", ondelete="RESTRICT"), nullable=False
    )
    stock_solution_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_stock_solutions.id", ondelete="RESTRICT")
    )
    target_identity: Mapped[str] = mapped_column(String(255), nullable=False)
    build_identity: Mapped[str] = mapped_column(String(255), nullable=False)
    identity_status: Mapped[str] = mapped_column(String(80), nullable=False)
    inventory_status: Mapped[str] = mapped_column(String(80), nullable=False)
    substitution_class: Mapped[str] = mapped_column(String(80), nullable=False)
    preserved_functions_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    lost_functions_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_sha256: Mapped[str | None] = mapped_column(String(64))


class LabInventoryMappingEvidenceLink(LabRecord):
    __tablename__ = "lab_inventory_mapping_evidence_links"
    __table_args__ = (
        UniqueConstraint(
            "inventory_mapping_version_id",
            "evidence_record_id",
            name="uq_lab_mapping_evidence_link",
        ),
    )

    inventory_mapping_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_inventory_mapping_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    evidence_record_id: Mapped[str] = mapped_column(
        ForeignKey("lab_evidence_records.id", ondelete="RESTRICT"), nullable=False
    )


class LabBuildPlanVersion(LabRecord):
    __tablename__ = "lab_build_plan_versions"
    __table_args__ = (
        UniqueConstraint(
            "plan_id", "version_number", name="uq_lab_build_plan_version"
        ),
        UniqueConstraint(
            "content_sha256", name="uq_lab_build_plan_content_sha256"
        ),
        CheckConstraint(
            "version_number >= 1", name="ck_lab_build_plan_version_positive"
        ),
        CheckConstraint(
            f"status IN ({_quoted(BUILD_PLAN_STATUSES)})",
            name="ck_lab_build_plan_status",
        ),
        ForeignKeyConstraint(
            ["accepted_target_version_id", "target_hypothesis_version_id"],
            [
                "lab_accepted_target_versions.id",
                "lab_accepted_target_versions.target_hypothesis_version_id",
            ],
            name="fk_lab_build_plan_acceptance_target",
            ondelete="RESTRICT",
        ),
    )

    plan_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    target_hypothesis_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_target_hypothesis_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    accepted_target_version_id: Mapped[str] = mapped_column(
        String(36), nullable=False
    )
    parent_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_build_plan_versions.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    reviewer: Mapped[str | None] = mapped_column(String(255))
    reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(timezone=True))
    provenance_activity_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    inventory_snapshot_ref: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_sha256: Mapped[str | None] = mapped_column(String(64))
    uncertainty_summary_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default=text("'{}'"), nullable=False
    )
    rationale: Mapped[str] = mapped_column(Text, nullable=False)


class LabBuildPlanLine(LabRecord):
    __tablename__ = "lab_build_plan_lines"
    __table_args__ = (
        UniqueConstraint(
            "build_plan_version_id",
            "position",
            name="uq_lab_build_plan_line_position",
        ),
        UniqueConstraint(
            "build_plan_version_id",
            "line_id",
            name="uq_lab_build_plan_line_identity",
        ),
        UniqueConstraint(
            "id",
            "build_plan_version_id",
            name="uq_lab_build_plan_line_id_version",
        ),
        CheckConstraint(
            "position >= 1 AND planned_raw_quantity >= 0 "
            "AND planned_active_quantity >= 0 "
            "AND planned_active_quantity <= planned_raw_quantity "
            "AND resolution > 0 AND expected_transfer_loss >= 0",
            name="ck_lab_build_plan_line_quantities",
        ),
        CheckConstraint(
            "concentration_fraction >= 0 AND concentration_fraction <= 1",
            name="ck_lab_build_plan_line_fraction",
        ),
    )

    line_id: Mapped[str] = mapped_column(String(255), nullable=False)
    build_plan_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_build_plan_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    target_line_id: Mapped[str] = mapped_column(
        ForeignKey("lab_target_lines.id", ondelete="RESTRICT"), nullable=False
    )
    target_identity: Mapped[str] = mapped_column(String(255), nullable=False)
    inventory_mapping_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_inventory_mapping_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    stock_solution_id: Mapped[str] = mapped_column(
        ForeignKey("lab_stock_solutions.id", ondelete="RESTRICT"), nullable=False
    )
    planned_raw_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    planned_active_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False)
    concentration_fraction: Mapped[float] = mapped_column(Float, nullable=False)
    concentration_basis: Mapped[str] = mapped_column(String(80), nullable=False)
    density_g_ml: Mapped[float | None] = mapped_column(Float)
    density_source: Mapped[str | None] = mapped_column(Text)
    standard_uncertainty: Mapped[float | None] = mapped_column(Float)
    measurement_method: Mapped[str] = mapped_column(String(100), nullable=False)
    resolution: Mapped[float] = mapped_column(Float, nullable=False)
    expected_transfer_loss: Mapped[float] = mapped_column(Float, nullable=False)
    substitution_class: Mapped[str] = mapped_column(String(80), nullable=False)
    preserved_functions_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    lost_functions_json: Mapped[list] = mapped_column(
        JSON, default=list, server_default=text("'[]'"), nullable=False
    )
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    reservation_state: Mapped[str] = mapped_column(String(40), nullable=False)
    execution_state: Mapped[str] = mapped_column(String(40), nullable=False)


class LabBuildPlanEvidenceLink(LabRecord):
    __tablename__ = "lab_build_plan_evidence_links"
    __table_args__ = (
        UniqueConstraint(
            "build_plan_version_id",
            "build_plan_line_id",
            "evidence_record_id",
            name="uq_lab_build_plan_evidence_link",
        ),
        ForeignKeyConstraint(
            ["build_plan_line_id", "build_plan_version_id"],
            [
                "lab_build_plan_lines.id",
                "lab_build_plan_lines.build_plan_version_id",
            ],
            name="fk_lab_build_evidence_line_version",
            ondelete="RESTRICT",
        ),
    )

    build_plan_version_id: Mapped[str] = mapped_column(
        ForeignKey("lab_build_plan_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    build_plan_line_id: Mapped[str | None] = mapped_column(String(36))
    evidence_record_id: Mapped[str] = mapped_column(
        ForeignKey("lab_evidence_records.id", ondelete="RESTRICT"), nullable=False
    )


class LabInventoryReservationEvent(LabRecord):
    __tablename__ = "lab_inventory_reservation_events"
    __table_args__ = (
        UniqueConstraint(
            "reservation_id", "sequence", name="uq_lab_reservation_sequence"
        ),
        UniqueConstraint(
            "idempotency_key", name="uq_lab_reservation_idempotency"
        ),
        UniqueConstraint(
            "id", "reservation_id", name="uq_lab_reservation_event_identity"
        ),
        CheckConstraint(
            "sequence >= 1", name="ck_lab_reservation_sequence"
        ),
        CheckConstraint(
            "reserved_mass_g > 0", name="ck_lab_reservation_mass"
        ),
        CheckConstraint(
            f"state IN ({_quoted(RESERVATION_STATES)})",
            name="ck_lab_reservation_state",
        ),
        ForeignKeyConstraint(
            ["build_plan_line_id", "build_plan_version_id"],
            [
                "lab_build_plan_lines.id",
                "lab_build_plan_lines.build_plan_version_id",
            ],
            name="fk_lab_reservation_line_version",
            ondelete="RESTRICT",
        ),
    )

    reservation_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_event_id: Mapped[str | None] = mapped_column(
        ForeignKey("lab_inventory_reservation_events.id", ondelete="RESTRICT")
    )
    build_plan_version_id: Mapped[str] = mapped_column(String(36), nullable=False)
    build_plan_line_id: Mapped[str] = mapped_column(String(36), nullable=False)
    stock_solution_id: Mapped[str] = mapped_column(
        ForeignKey("lab_stock_solutions.id", ondelete="RESTRICT"), nullable=False
    )
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    reserved_mass_g: Mapped[float] = mapped_column(Float, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    command_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)


PLANNING_TABLE_NAMES = {
    "lab_target_hypothesis_versions",
    "lab_target_lines",
    "lab_target_evidence_links",
    "lab_accepted_target_versions",
    "lab_formula_version_edges",
    "lab_inventory_mapping_versions",
    "lab_inventory_mapping_evidence_links",
    "lab_build_plan_versions",
    "lab_build_plan_lines",
    "lab_build_plan_evidence_links",
    "lab_inventory_reservation_events",
}


__all__ = [
    "BUILD_PLAN_STATUSES",
    "LabAcceptedTargetVersion",
    "LabBuildPlanEvidenceLink",
    "LabBuildPlanLine",
    "LabBuildPlanVersion",
    "LabFormulaVersionEdge",
    "LabInventoryMappingEvidenceLink",
    "LabInventoryMappingVersion",
    "LabInventoryReservationEvent",
    "LabTargetEvidenceLink",
    "LabTargetHypothesisVersion",
    "LabTargetLine",
    "PLANNING_TABLE_NAMES",
    "RESERVATION_STATES",
    "UNAVAILABLE_INVENTORY_STATUSES",
]
