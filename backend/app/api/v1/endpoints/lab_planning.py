"""Thin versioned routes for the canonical A2 planning service."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.lab_planning import (
    AcceptedTargetResponse,
    BuildPlanCreate,
    BuildPlanResponse,
    BuildPlanTransitionCreate,
    FormulaParentCreate,
    FormulaVersionEdgeResponse,
    InventoryMappingCreate,
    InventoryMappingResponse,
    ReservationCreate,
    ReservationResponse,
    ReservationTransitionCreate,
    TargetAcceptCreate,
    TargetHypothesisCreate,
    TargetHypothesisResponse,
)
from app.services.lab_planning import (
    BuildPlanInput,
    BuildPlanLineInput,
    InventoryMappingInput,
    PlanningConflictError,
    PlanningDomainError,
    TargetHypothesisInput,
    TargetLineInput,
)
from app.services.lab_service import LabService

router = APIRouter()
ResponsePayload = dict[str, Any] | JSONResponse


def _error_status(error: PlanningDomainError) -> int:
    if error.code.endswith("_NOT_FOUND"):
        return status.HTTP_404_NOT_FOUND
    if isinstance(error, PlanningConflictError):
        return status.HTTP_409_CONFLICT
    return status.HTTP_400_BAD_REQUEST


async def _run(
    operation: Callable[[], Awaitable[Any]],
    serializer: Callable[
        [Any],
        dict[str, Any] | Awaitable[dict[str, Any]],
    ],
) -> ResponsePayload:
    try:
        record = await operation()
        payload = serializer(record)
        if inspect.isawaitable(payload):
            return await payload
        return payload
    except PlanningDomainError as error:
        return JSONResponse(
            status_code=_error_status(error),
            content={
                "error": {
                    "code": error.code,
                    "message": str(error),
                }
            },
        )


def _target_command(request: TargetHypothesisCreate) -> TargetHypothesisInput:
    return TargetHypothesisInput(
        product_key=request.product_key,
        schema_version=request.schema_version,
        author=request.author,
        provenance_activity=dict(request.provenance_activity),
        uncertainty_summary=dict(request.uncertainty_summary),
        rationale=request.rationale,
        lines=tuple(
            TargetLineInput(
                line_id=line.line_id,
                target_identity=line.target_identity,
                source_name=line.source_name,
                grade=line.grade,
                presence_probability=line.presence_probability,
                target_raw_quantity=line.target_raw_quantity,
                target_active_quantity=line.target_active_quantity,
                unit=line.unit,
                concentration_fraction=line.concentration_fraction,
                concentration_basis=line.concentration_basis,
                functional_roles=tuple(line.functional_roles),
                evidence_links=tuple(line.evidence_links),
                uncertainty=dict(line.uncertainty),
            )
            for line in request.lines
        ),
    )


def _mapping_command(
    request: InventoryMappingCreate,
) -> InventoryMappingInput:
    return InventoryMappingInput(
        target_line_id=request.target_line_id,
        stock_solution_id=request.stock_solution_id,
        target_identity=request.target_identity,
        build_identity=request.build_identity,
        identity_status=request.identity_status,
        inventory_status=request.inventory_status,
        substitution_class=request.substitution_class,
        preserved_functions=tuple(request.preserved_functions),
        lost_functions=tuple(request.lost_functions),
        confidence=request.confidence,
        rationale=request.rationale,
        evidence_links=tuple(request.evidence_links),
    )


def _build_plan_command(request: BuildPlanCreate) -> BuildPlanInput:
    return BuildPlanInput(
        target_hypothesis_version_id=request.target_hypothesis_version_id,
        accepted_target_version_id=request.accepted_target_version_id,
        schema_version=request.schema_version,
        author=request.author,
        inventory_snapshot_ref=request.inventory_snapshot_ref,
        uncertainty_summary=dict(request.uncertainty_summary),
        rationale=request.rationale,
        lines=tuple(
            BuildPlanLineInput(
                line_id=line.line_id,
                target_line_id=line.target_line_id,
                target_identity=line.target_identity,
                inventory_mapping_version_id=(
                    line.inventory_mapping_version_id
                ),
                stock_solution_id=line.stock_solution_id,
                planned_raw_quantity=line.planned_raw_quantity,
                planned_active_quantity=line.planned_active_quantity,
                unit=line.unit,
                concentration_fraction=line.concentration_fraction,
                concentration_basis=line.concentration_basis,
                density_g_ml=line.density_g_ml,
                density_source=line.density_source,
                standard_uncertainty=line.standard_uncertainty,
                measurement_method=line.measurement_method,
                resolution=line.resolution,
                expected_transfer_loss=line.expected_transfer_loss,
                substitution_class=line.substitution_class,
                preserved_functions=tuple(line.preserved_functions),
                lost_functions=tuple(line.lost_functions),
                rationale=line.rationale,
                evidence_links=tuple(line.evidence_links),
            )
            for line in request.lines
        ),
    )


def _target_line_record(line: Any) -> dict[str, Any]:
    return {
        "id": line.id,
        "line_id": line.line_id,
        "position": line.position,
        "target_identity": line.target_identity,
        "source_name": line.source_name,
        "grade": line.grade,
        "presence_probability": line.presence_probability,
        "target_raw_quantity": line.target_raw_quantity,
        "target_active_quantity": line.target_active_quantity,
        "unit": line.unit,
        "concentration_fraction": line.concentration_fraction,
        "concentration_basis": line.concentration_basis,
        "functional_roles": list(line.functional_roles_json),
        "uncertainty": dict(line.uncertainty_json),
        "created_at": line.created_at,
    }


async def _target_record(
    target: Any,
    service: LabService,
) -> dict[str, Any]:
    lines = await service.repository.target_lines(target.id)
    return {
        "id": target.id,
        "target_id": target.target_id,
        "version_number": target.version_number,
        "schema_version": target.schema_version,
        "product_key": target.product_key,
        "parent_version_id": target.parent_version_id,
        "author": target.author,
        "provenance_activity": dict(target.provenance_activity_json),
        "uncertainty_summary": dict(target.uncertainty_summary_json),
        "rationale": target.rationale,
        "content_sha256": target.content_sha256,
        "parent_sha256": target.parent_sha256,
        "created_at": target.created_at,
        "lines": [_target_line_record(line) for line in lines],
    }


def _acceptance_record(record: Any) -> dict[str, Any]:
    return {
        "id": record.id,
        "accepted_target_id": record.accepted_target_id,
        "version_number": record.version_number,
        "target_hypothesis_version_id": record.target_hypothesis_version_id,
        "parent_version_id": record.parent_version_id,
        "reviewer": record.reviewer,
        "rationale": record.rationale,
        "content_sha256": record.content_sha256,
        "parent_sha256": record.parent_sha256,
        "created_at": record.created_at,
    }


def _formula_edge_record(record: Any) -> dict[str, Any]:
    return {
        "id": record.id,
        "child_version_id": record.child_version_id,
        "parent_version_id": record.parent_version_id,
        "relationship_kind": record.relationship_kind,
        "change": dict(record.change_json),
        "rationale": record.rationale,
        "content_sha256": record.content_sha256,
        "created_at": record.created_at,
    }


def _mapping_record(record: Any) -> dict[str, Any]:
    return {
        "id": record.id,
        "mapping_id": record.mapping_id,
        "version_number": record.version_number,
        "parent_version_id": record.parent_version_id,
        "target_line_id": record.target_line_id,
        "stock_solution_id": record.stock_solution_id,
        "target_identity": record.target_identity,
        "build_identity": record.build_identity,
        "identity_status": record.identity_status,
        "inventory_status": record.inventory_status,
        "substitution_class": record.substitution_class,
        "preserved_functions": list(record.preserved_functions_json),
        "lost_functions": list(record.lost_functions_json),
        "confidence": record.confidence,
        "rationale": record.rationale,
        "content_sha256": record.content_sha256,
        "parent_sha256": record.parent_sha256,
        "created_at": record.created_at,
    }


def _build_line_record(line: Any) -> dict[str, Any]:
    return {
        "id": line.id,
        "line_id": line.line_id,
        "position": line.position,
        "target_line_id": line.target_line_id,
        "target_identity": line.target_identity,
        "inventory_mapping_version_id": line.inventory_mapping_version_id,
        "stock_solution_id": line.stock_solution_id,
        "planned_raw_quantity": line.planned_raw_quantity,
        "planned_active_quantity": line.planned_active_quantity,
        "unit": line.unit,
        "concentration_fraction": line.concentration_fraction,
        "concentration_basis": line.concentration_basis,
        "density_g_ml": line.density_g_ml,
        "density_source": line.density_source,
        "standard_uncertainty": line.standard_uncertainty,
        "measurement_method": line.measurement_method,
        "resolution": line.resolution,
        "expected_transfer_loss": line.expected_transfer_loss,
        "substitution_class": line.substitution_class,
        "preserved_functions": list(line.preserved_functions_json),
        "lost_functions": list(line.lost_functions_json),
        "rationale": line.rationale,
        "reservation_state": line.reservation_state,
        "execution_state": line.execution_state,
        "created_at": line.created_at,
    }


async def _build_plan_record(
    plan: Any,
    service: LabService,
) -> dict[str, Any]:
    lines = await service.repository.build_plan_lines(plan.id)
    return {
        "id": plan.id,
        "plan_id": plan.plan_id,
        "version_number": plan.version_number,
        "schema_version": plan.schema_version,
        "target_hypothesis_version_id": plan.target_hypothesis_version_id,
        "accepted_target_version_id": plan.accepted_target_version_id,
        "parent_version_id": plan.parent_version_id,
        "status": plan.status,
        "author": plan.author,
        "reviewer": plan.reviewer,
        "reviewed_at": plan.reviewed_at,
        "provenance_activity": dict(plan.provenance_activity_json),
        "inventory_snapshot_ref": plan.inventory_snapshot_ref,
        "content_sha256": plan.content_sha256,
        "parent_sha256": plan.parent_sha256,
        "uncertainty_summary": dict(plan.uncertainty_summary_json),
        "rationale": plan.rationale,
        "created_at": plan.created_at,
        "lines": [_build_line_record(line) for line in lines],
    }


def _reservation_record(record: Any) -> dict[str, Any]:
    return {
        "id": record.id,
        "reservation_id": record.reservation_id,
        "sequence": record.sequence,
        "parent_event_id": record.parent_event_id,
        "build_plan_version_id": record.build_plan_version_id,
        "build_plan_line_id": record.build_plan_line_id,
        "stock_solution_id": record.stock_solution_id,
        "state": record.state,
        "reserved_mass_g": record.reserved_mass_g,
        "idempotency_key": record.idempotency_key,
        "command_sha256": record.command_sha256,
        "actor": record.actor,
        "rationale": record.rationale,
        "created_at": record.created_at,
    }


async def _require_target(service: LabService, version_id: str) -> Any:
    target = await service.repository.get_target_version(version_id)
    if target is None:
        raise PlanningConflictError(
            "TARGET_NOT_FOUND",
            f"Target version not found: {version_id}.",
        )
    return target


async def _require_build_plan(service: LabService, version_id: str) -> Any:
    plan = await service.repository.get_build_plan_version(version_id)
    if plan is None:
        raise PlanningConflictError(
            "BUILD_PLAN_NOT_FOUND",
            f"Build plan version not found: {version_id}.",
        )
    return plan


@router.post(
    "/targets",
    status_code=status.HTTP_201_CREATED,
    response_model=TargetHypothesisResponse,
)
async def create_target(
    request: TargetHypothesisCreate,
    session: AsyncSession = Depends(get_db),
) -> ResponsePayload:
    service = LabService(session)
    return await _run(
        lambda: service.create_target_hypothesis(_target_command(request)),
        lambda target: _target_record(target, service),
    )


@router.get(
    "/targets/{version_id}",
    response_model=TargetHypothesisResponse,
)
async def get_target(
    version_id: str,
    session: AsyncSession = Depends(get_db),
) -> ResponsePayload:
    service = LabService(session)
    return await _run(
        lambda: _require_target(service, version_id),
        lambda target: _target_record(target, service),
    )


@router.post(
    "/targets/{version_id}/accept",
    status_code=status.HTTP_201_CREATED,
    response_model=AcceptedTargetResponse,
)
async def accept_target(
    version_id: str,
    request: TargetAcceptCreate,
    session: AsyncSession = Depends(get_db),
) -> ResponsePayload:
    service = LabService(session)
    return await _run(
        lambda: service.accept_target(
            version_id,
            reviewer=request.reviewer,
            rationale=request.rationale,
        ),
        _acceptance_record,
    )


@router.post(
    "/formula-versions/{child_id}/parents",
    status_code=status.HTTP_201_CREATED,
    response_model=FormulaVersionEdgeResponse,
)
async def add_formula_parent(
    child_id: str,
    request: FormulaParentCreate,
    session: AsyncSession = Depends(get_db),
) -> ResponsePayload:
    service = LabService(session)
    return await _run(
        lambda: service.link_formula_version(
            child_id,
            request.parent_version_id,
            relationship_kind=request.relationship_kind,
            change=request.change,
            rationale=request.rationale,
        ),
        _formula_edge_record,
    )


@router.post(
    "/inventory-mappings",
    status_code=status.HTTP_201_CREATED,
    response_model=InventoryMappingResponse,
)
async def create_inventory_mapping(
    request: InventoryMappingCreate,
    session: AsyncSession = Depends(get_db),
) -> ResponsePayload:
    service = LabService(session)
    return await _run(
        lambda: service.create_inventory_mapping(_mapping_command(request)),
        _mapping_record,
    )


@router.post(
    "/build-plans",
    status_code=status.HTTP_201_CREATED,
    response_model=BuildPlanResponse,
)
async def create_build_plan(
    request: BuildPlanCreate,
    session: AsyncSession = Depends(get_db),
) -> ResponsePayload:
    service = LabService(session)
    return await _run(
        lambda: service.create_build_plan(_build_plan_command(request)),
        lambda plan: _build_plan_record(plan, service),
    )


@router.get(
    "/build-plans/{version_id}",
    response_model=BuildPlanResponse,
)
async def get_build_plan(
    version_id: str,
    session: AsyncSession = Depends(get_db),
) -> ResponsePayload:
    service = LabService(session)
    return await _run(
        lambda: _require_build_plan(service, version_id),
        lambda plan: _build_plan_record(plan, service),
    )


@router.post(
    "/build-plans/{version_id}/transitions",
    status_code=status.HTTP_201_CREATED,
    response_model=BuildPlanResponse,
)
async def transition_build_plan(
    version_id: str,
    request: BuildPlanTransitionCreate,
    session: AsyncSession = Depends(get_db),
) -> ResponsePayload:
    service = LabService(session)
    return await _run(
        lambda: service.transition_build_plan(
            version_id,
            next_status=request.next_status,
            actor=request.actor,
            rationale=request.rationale,
        ),
        lambda plan: _build_plan_record(plan, service),
    )


@router.post(
    "/reservations",
    status_code=status.HTTP_201_CREATED,
    response_model=ReservationResponse,
)
async def reserve_inventory(
    request: ReservationCreate,
    session: AsyncSession = Depends(get_db),
) -> ResponsePayload:
    service = LabService(session)
    return await _run(
        lambda: service.reserve_inventory(**request.model_dump()),
        _reservation_record,
    )


@router.post(
    "/reservations/{reservation_id}/transitions",
    status_code=status.HTTP_201_CREATED,
    response_model=ReservationResponse,
)
async def transition_reservation(
    reservation_id: str,
    request: ReservationTransitionCreate,
    session: AsyncSession = Depends(get_db),
) -> ResponsePayload:
    service = LabService(session)
    return await _run(
        lambda: service.transition_reservation(
            reservation_id,
            **request.model_dump(),
        ),
        _reservation_record,
    )


__all__ = ["router"]
