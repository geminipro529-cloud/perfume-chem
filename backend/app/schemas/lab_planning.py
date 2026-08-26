"""Strict versioned API contracts for the A2 canonical planning core."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
)

NonBlank = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
FiniteNonnegative = Annotated[
    float,
    Field(ge=0, allow_inf_nan=False),
]
FinitePositive = Annotated[
    float,
    Field(gt=0, allow_inf_nan=False),
]
Fraction = Annotated[
    float,
    Field(ge=0, le=1, allow_inf_nan=False),
]


class PlanningRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TargetLineCreate(PlanningRequest):
    line_id: NonBlank
    target_identity: NonBlank
    source_name: NonBlank
    grade: NonBlank
    presence_probability: Fraction
    target_raw_quantity: FiniteNonnegative
    target_active_quantity: FiniteNonnegative
    unit: NonBlank
    concentration_fraction: Fraction
    concentration_basis: NonBlank
    functional_roles: tuple[NonBlank, ...]
    evidence_links: tuple[NonBlank, ...] = Field(min_length=1)
    uncertainty: dict


class TargetHypothesisCreate(PlanningRequest):
    product_key: NonBlank
    schema_version: NonBlank
    author: NonBlank
    provenance_activity: dict
    uncertainty_summary: dict
    rationale: NonBlank
    lines: tuple[TargetLineCreate, ...] = Field(min_length=1)


class TargetAcceptCreate(PlanningRequest):
    reviewer: NonBlank
    rationale: NonBlank


class FormulaParentCreate(PlanningRequest):
    parent_version_id: NonBlank
    relationship_kind: NonBlank
    change: dict
    rationale: NonBlank


class InventoryMappingCreate(PlanningRequest):
    target_line_id: NonBlank
    stock_solution_id: NonBlank | None = None
    target_identity: NonBlank
    build_identity: NonBlank
    identity_status: NonBlank
    inventory_status: NonBlank
    substitution_class: NonBlank
    preserved_functions: tuple[NonBlank, ...]
    lost_functions: tuple[NonBlank, ...]
    confidence: Fraction
    rationale: NonBlank
    evidence_links: tuple[NonBlank, ...] = Field(min_length=1)


class BuildPlanLineCreate(PlanningRequest):
    line_id: NonBlank
    target_line_id: NonBlank
    target_identity: NonBlank
    inventory_mapping_version_id: NonBlank
    stock_solution_id: NonBlank
    planned_raw_quantity: FiniteNonnegative
    planned_active_quantity: FiniteNonnegative
    unit: NonBlank
    concentration_fraction: Fraction
    concentration_basis: NonBlank
    density_g_ml: FinitePositive | None = None
    density_source: NonBlank | None = None
    standard_uncertainty: FiniteNonnegative | None = None
    measurement_method: NonBlank
    resolution: FinitePositive
    expected_transfer_loss: FiniteNonnegative
    substitution_class: NonBlank
    preserved_functions: tuple[NonBlank, ...]
    lost_functions: tuple[NonBlank, ...]
    rationale: NonBlank
    evidence_links: tuple[NonBlank, ...] = Field(min_length=1)


class BuildPlanCreate(PlanningRequest):
    target_hypothesis_version_id: NonBlank
    accepted_target_version_id: NonBlank
    schema_version: NonBlank
    author: NonBlank
    inventory_snapshot_ref: NonBlank
    uncertainty_summary: dict
    rationale: NonBlank
    lines: tuple[BuildPlanLineCreate, ...] = Field(min_length=1)


class BuildPlanTransitionCreate(PlanningRequest):
    next_status: Literal[
        "DRAFT",
        "UNDER_REVIEW",
        "APPROVED",
        "RESERVED",
        "EXECUTING",
        "CLOSED",
        "SUPERSEDED",
        "CANCELLED",
    ]
    actor: NonBlank
    rationale: NonBlank


class ReservationCreate(PlanningRequest):
    build_plan_version_id: NonBlank
    build_plan_line_id: NonBlank
    stock_solution_id: NonBlank
    reserved_mass_g: FinitePositive
    idempotency_key: NonBlank
    actor: NonBlank
    rationale: NonBlank


class ReservationTransitionCreate(PlanningRequest):
    next_state: Literal["RELEASED", "FULFILLED", "CANCELLED"]
    idempotency_key: NonBlank
    actor: NonBlank
    rationale: NonBlank


class PlanningResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TargetLineResponse(PlanningResponse):
    id: str
    line_id: str
    position: int
    target_identity: str
    source_name: str
    grade: str
    presence_probability: float
    target_raw_quantity: float
    target_active_quantity: float
    unit: str
    concentration_fraction: float
    concentration_basis: str
    functional_roles: list[str]
    uncertainty: dict
    created_at: datetime


class TargetHypothesisResponse(PlanningResponse):
    id: str
    target_id: str
    version_number: int
    schema_version: str
    product_key: str
    parent_version_id: str | None
    author: str
    provenance_activity: dict
    uncertainty_summary: dict
    rationale: str
    content_sha256: str
    parent_sha256: str | None
    created_at: datetime
    lines: list[TargetLineResponse]


class AcceptedTargetResponse(PlanningResponse):
    id: str
    accepted_target_id: str
    version_number: int
    target_hypothesis_version_id: str
    parent_version_id: str | None
    reviewer: str
    rationale: str
    content_sha256: str
    parent_sha256: str | None
    created_at: datetime


class FormulaVersionEdgeResponse(PlanningResponse):
    id: str
    child_version_id: str
    parent_version_id: str
    relationship_kind: str
    change: dict
    rationale: str
    content_sha256: str
    created_at: datetime


class InventoryMappingResponse(PlanningResponse):
    id: str
    mapping_id: str
    version_number: int
    parent_version_id: str | None
    target_line_id: str
    stock_solution_id: str | None
    target_identity: str
    build_identity: str
    identity_status: str
    inventory_status: str
    substitution_class: str
    preserved_functions: list[str]
    lost_functions: list[str]
    confidence: float
    rationale: str
    content_sha256: str
    parent_sha256: str | None
    created_at: datetime


class BuildPlanLineResponse(PlanningResponse):
    id: str
    line_id: str
    position: int
    target_line_id: str
    target_identity: str
    inventory_mapping_version_id: str
    stock_solution_id: str
    planned_raw_quantity: float
    planned_active_quantity: float
    unit: str
    concentration_fraction: float
    concentration_basis: str
    density_g_ml: float | None
    density_source: str | None
    standard_uncertainty: float | None
    measurement_method: str
    resolution: float
    expected_transfer_loss: float
    substitution_class: str
    preserved_functions: list[str]
    lost_functions: list[str]
    rationale: str
    reservation_state: str
    execution_state: str
    created_at: datetime


class BuildPlanResponse(PlanningResponse):
    id: str
    plan_id: str
    version_number: int
    schema_version: str
    target_hypothesis_version_id: str
    accepted_target_version_id: str
    parent_version_id: str | None
    status: str
    author: str
    reviewer: str | None
    reviewed_at: AwareDatetime | None
    provenance_activity: dict
    inventory_snapshot_ref: str
    content_sha256: str
    parent_sha256: str | None
    uncertainty_summary: dict
    rationale: str
    created_at: datetime
    lines: list[BuildPlanLineResponse]


class ReservationResponse(PlanningResponse):
    id: str
    reservation_id: str
    sequence: int
    parent_event_id: str | None
    build_plan_version_id: str
    build_plan_line_id: str
    stock_solution_id: str
    state: str
    reserved_mass_g: float
    idempotency_key: str
    command_sha256: str
    actor: str
    rationale: str
    created_at: datetime


__all__ = [name for name in globals() if name.endswith(("Create", "Response"))]
