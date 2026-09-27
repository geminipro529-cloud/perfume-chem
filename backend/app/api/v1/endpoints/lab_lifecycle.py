"""Thin versioned routes for canonical execution and science authority."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import APIRouter, Body, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.lab_lifecycle import (
    AnalyticalResultCreate,
    AnalyticalResultResponse,
    BottleActionCommitCreate,
    BottleActionCommitResponse,
    BottleActionConfirmationCreate,
    BottleActionConfirmationResponse,
    BottleActionMeasurementCreate,
    BottleActionMeasurementResponse,
    BottleActionProposalCreate,
    BottleActionProposalResponse,
    BottleReplayResponse,
    ClaimAuthorityReviewCreate,
    ClaimAuthorityReviewResponse,
    RegulatoryAssessmentCreate,
    RegulatoryAssessmentResponse,
    SensoryResultCreate,
    SensoryResultResponse,
)
from app.services.lab_claims import (
    ClaimAuthorityConflictError,
    ClaimAuthorityError,
    ClaimAuthorityEvaluationInput,
    ClaimAuthoritySupportInput,
)
from app.services.lab_execution import (
    BottleActionConfirmationInput,
    BottleActionMeasurementInput,
    BottleActionProposalInput,
    ExecutionConflictError,
    ExecutionDomainError,
    bottle_state_payload,
)
from app.services.lab_science import (
    AnalyticalRunInput,
    RegulatoryAssessmentInput,
    ScienceAuthorityConflictError,
    ScienceAuthorityError,
)
from app.services.lab_service import LabService

router = APIRouter()
ResponsePayload = dict[str, Any] | JSONResponse


def _error_response(error: Exception) -> JSONResponse:
    if isinstance(
        error,
        (ExecutionDomainError, ScienceAuthorityError, ClaimAuthorityError),
    ):
        code = error.code
        message = str(error)
        if code.endswith("_NOT_FOUND"):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(
            error,
            (
                ExecutionConflictError,
                ScienceAuthorityConflictError,
                ClaimAuthorityConflictError,
            ),
        ):
            status_code = status.HTTP_409_CONFLICT
        else:
            status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(error, KeyError):
        code = "LAB_RECORD_NOT_FOUND"
        message = str(error.args[0]) if error.args else "Lab record not found."
        status_code = status.HTTP_404_NOT_FOUND
    else:
        code = "INVALID_LAB_COMMAND"
        message = str(error)
        status_code = status.HTTP_400_BAD_REQUEST
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


async def _run(
    operation: Callable[[], Awaitable[Any]],
    serializer: Callable[[Any], dict[str, Any]],
) -> ResponsePayload:
    try:
        return serializer(await operation())
    except (
        ExecutionDomainError,
        ScienceAuthorityError,
        ClaimAuthorityError,
        KeyError,
        ValueError,
    ) as error:
        return _error_response(error)


def _proposal_record(record: Any) -> dict[str, Any]:
    return {
        "id": record.id,
        "schema_version": record.schema_version,
        "reservation_id": record.reservation_id,
        "reservation_event_id": record.reservation_event_id,
        "bottle_id": record.bottle_id,
        "action_type": record.action_type,
        "stock_solution_id": record.stock_solution_id,
        "planned_mass_g": record.planned_mass_g,
        "expected_sequence": record.expected_sequence,
        "idempotency_key": record.idempotency_key,
        "actor": record.actor,
        "rationale": record.rationale,
        "content_sha256": record.content_sha256,
        "created_at": record.created_at,
    }


def _confirmation_record(record: Any) -> dict[str, Any]:
    return {
        "id": record.id,
        "proposal_id": record.proposal_id,
        "decision": record.decision,
        "confirmer_pseudonym": record.confirmer_pseudonym,
        "confirmed_at": record.confirmed_at,
        "rationale": record.rationale,
        "content_sha256": record.content_sha256,
        "created_at": record.created_at,
    }


def _measurement_record(record: Any) -> dict[str, Any]:
    return {
        "id": record.id,
        "bottle_event_id": record.bottle_event_id,
        "proposal_id": record.proposal_id,
        "quantity_kind": record.quantity_kind,
        "value": record.value,
        "unit": record.unit,
        "standard_uncertainty": record.standard_uncertainty,
        "method": record.method,
        "measured_at": record.measured_at,
        "actor": record.actor,
        "created_at": record.created_at,
    }


def _commit_record(record: Any) -> dict[str, Any]:
    return {
        "id": record.id,
        "proposal_id": record.proposal_id,
        "bottle_event_id": record.bottle_event_id,
        "fulfilled_reservation_event_id": (
            record.fulfilled_reservation_event_id
        ),
        "actor": record.actor,
        "rationale": record.rationale,
        "before_state": dict(record.before_state_json),
        "after_state": dict(record.after_state_json),
        "state_diff": dict(record.state_diff_json),
        "content_sha256": record.content_sha256,
        "created_at": record.created_at,
    }


def _analytical_record(record: Any) -> dict[str, Any]:
    return {
        "id": record.id,
        "run_id": record.run_id,
        "method_version_id": record.method_version_id,
        "run_kind": record.run_kind,
        "status": record.status,
        "instrument_identifier": record.instrument_identifier,
        "acquired_at": record.acquired_at,
        "parameters": dict(record.parameters_json),
        "deviations": list(record.deviations_json),
        "processing_version": record.processing_version,
        "experiment_id": record.experiment_id,
        "sample_id": record.sample_id,
        "bottle_id": record.bottle_id,
        "formula_version_id": record.formula_version_id,
        "build_plan_version_id": record.build_plan_version_id,
        "content_sha256": record.content_sha256,
        "created_at": record.created_at,
    }


def _sensory_record(record: Any) -> dict[str, Any]:
    return {
        "id": record.id,
        "application_id": record.application_id,
        "elapsed_seconds": record.elapsed_seconds,
        "observations": dict(record.observations_json),
        "created_at": record.created_at,
    }


def _regulatory_record(record: Any) -> dict[str, Any]:
    return {
        "id": record.id,
        "assessment_id": record.assessment_id,
        "version_number": record.version_number,
        "schema_version": record.schema_version,
        "subject_type": record.subject_type,
        "subject_id": record.subject_id,
        "parent_version_id": record.parent_version_id,
        "standard_identifier": record.standard_identifier,
        "standard_amendment": record.standard_amendment,
        "standard_state": record.standard_state,
        "source_evidence_record_id": record.source_evidence_record_id,
        "jurisdiction": record.jurisdiction,
        "product_category": record.product_category,
        "concentration_basis": record.concentration_basis,
        "finished_product_concentration": (
            record.finished_product_concentration
        ),
        "effective_date": record.effective_date,
        "evaluated_at": record.evaluated_at,
        "result_state": record.result_state,
        "assumptions": list(record.assumptions_json),
        "unresolved": list(record.unresolved_json),
        "permitted_wording": record.permitted_wording,
        "content_sha256": record.content_sha256,
        "parent_sha256": record.parent_sha256,
        "created_at": record.created_at,
    }


def _claim_authority_record(record: Any) -> dict[str, Any]:
    return {
        "id": record.id,
        "authority_id": record.authority_id,
        "version_number": record.version_number,
        "parent_version_id": record.parent_version_id,
        "legacy_claim_assessment_version_id": (
            record.legacy_claim_assessment_version_id
        ),
        "schema_version": record.schema_version,
        "policy_version": record.policy_version,
        "policy_sha256": record.policy_sha256,
        "policy": dict(record.policy_json),
        "claim_type": record.claim_type,
        "subject_type": record.subject_type,
        "subject_id": record.subject_id,
        "claim_payload": dict(record.claim_payload_json),
        "identity_scope": dict(record.identity_scope_json),
        "identity_scope_sha256": record.identity_scope_sha256,
        "condition_scope": dict(record.condition_scope_json),
        "condition_scope_sha256": record.condition_scope_sha256,
        "claim_scope_sha256": record.claim_scope_sha256,
        "decision": record.decision,
        "dimension_results": dict(record.dimension_results_json),
        "supporting_observations": list(record.supporting_observations_json),
        "conflicts": list(record.conflicts_json),
        "missing_requirements": list(record.missing_requirements_json),
        "source_references": list(record.source_references_json),
        "uncertainty": dict(record.uncertainty_json),
        "permitted_wording": record.permitted_wording,
        "forbidden_wording": record.forbidden_wording,
        "blocker_count": record.blocker_count,
        "conflict_count": record.conflict_count,
        "missing_requirement_count": record.missing_requirement_count,
        "critical_unknown_count": record.critical_unknown_count,
        "support_count": record.support_count,
        "source_reference_count": record.source_reference_count,
        "upstream_hashes": dict(record.upstream_hashes_json),
        "reviewer_pseudonym": record.reviewer_pseudonym,
        "reviewed_at": record.reviewed_at,
        "content_sha256": record.content_sha256,
        "parent_sha256": record.parent_sha256,
        "authority_scope": "SCIENTIFIC_CLAIM_ONLY",
        "release_authority": False,
        "safety_authority": False,
        "compounding_authority": False,
    }


def _claim_authority_command(
    request: ClaimAuthorityReviewCreate,
) -> ClaimAuthorityEvaluationInput:
    return ClaimAuthorityEvaluationInput(
        legacy_claim_assessment_version_id=(
            request.legacy_claim_assessment_version_id
        ),
        claim_payload=dict(request.claim_payload),
        identity_scope=dict(request.identity_scope),
        condition_scope=dict(request.condition_scope),
        supports=tuple(
            ClaimAuthoritySupportInput(
                support_kind=support.support_kind,
                record_id=support.record_id,
                role=support.role,
            )
            for support in request.supports
        ),
        reviewer_pseudonym=request.reviewer_pseudonym,
        reviewed_at=request.reviewed_at,
    )


@router.post(
    "/actions",
    status_code=status.HTTP_201_CREATED,
    response_model=BottleActionProposalResponse,
)
async def propose_action(
    request: BottleActionProposalCreate,
    session: AsyncSession = Depends(get_db),
) -> ResponsePayload:
    service = LabService(session)
    return await _run(
        lambda: service.propose_bottle_action(
            BottleActionProposalInput(**request.model_dump())
        ),
        _proposal_record,
    )


@router.post(
    "/actions/{proposal_id}/confirmations",
    status_code=status.HTTP_201_CREATED,
    response_model=BottleActionConfirmationResponse,
)
async def confirm_action(
    proposal_id: str,
    request: BottleActionConfirmationCreate,
    session: AsyncSession = Depends(get_db),
) -> ResponsePayload:
    service = LabService(session)
    return await _run(
        lambda: service.confirm_bottle_action(
            proposal_id,
            BottleActionConfirmationInput(**request.model_dump()),
        ),
        _confirmation_record,
    )


@router.post(
    "/actions/{proposal_id}/measurements",
    status_code=status.HTTP_201_CREATED,
    response_model=BottleActionMeasurementResponse,
)
async def measure_action(
    proposal_id: str,
    request: BottleActionMeasurementCreate,
    session: AsyncSession = Depends(get_db),
) -> ResponsePayload:
    service = LabService(session)
    return await _run(
        lambda: service.record_bottle_action_measurement(
            proposal_id,
            BottleActionMeasurementInput(**request.model_dump()),
        ),
        _measurement_record,
    )


@router.post(
    "/actions/{proposal_id}/commit",
    status_code=status.HTTP_201_CREATED,
    response_model=BottleActionCommitResponse,
)
async def commit_action(
    proposal_id: str,
    request: BottleActionCommitCreate,
    session: AsyncSession = Depends(get_db),
) -> ResponsePayload:
    service = LabService(session)
    return await _run(
        lambda: service.commit_bottle_action(
            proposal_id,
            **request.model_dump(),
        ),
        _commit_record,
    )


@router.get("/actions/{proposal_id}/diff", response_model=None)
async def action_diff(
    proposal_id: str,
    session: AsyncSession = Depends(get_db),
) -> ResponsePayload:
    service = LabService(session)
    return await _run(
        lambda: service.bottle_action_diff(proposal_id),
        lambda record: dict(record),
    )


@router.get(
    "/bottles/{bottle_id}/replay",
    response_model=BottleReplayResponse,
)
async def replay_bottle(
    bottle_id: str,
    session: AsyncSession = Depends(get_db),
) -> ResponsePayload:
    service = LabService(session)
    return await _run(
        lambda: service.reconstruct_bottle(bottle_id),
        bottle_state_payload,
    )


@router.post(
    "/analytical-results",
    status_code=status.HTTP_201_CREATED,
    response_model=AnalyticalResultResponse,
)
async def record_analytical_result(
    request: AnalyticalResultCreate,
    session: AsyncSession = Depends(get_db),
) -> ResponsePayload:
    service = LabService(session)
    return await _run(
        lambda: service.record_analytical_run(
            AnalyticalRunInput(**request.model_dump())
        ),
        _analytical_record,
    )


@router.post(
    "/sensory-results",
    status_code=status.HTTP_201_CREATED,
    response_model=SensoryResultResponse,
)
async def record_sensory_result(
    request: SensoryResultCreate,
    session: AsyncSession = Depends(get_db),
) -> ResponsePayload:
    service = LabService(session)
    return await _run(
        lambda: service.record_observation(**request.model_dump()),
        _sensory_record,
    )


@router.post(
    "/regulatory-assessments",
    status_code=status.HTTP_201_CREATED,
    response_model=RegulatoryAssessmentResponse,
)
async def create_regulatory_assessment(
    request: RegulatoryAssessmentCreate,
    session: AsyncSession = Depends(get_db),
) -> ResponsePayload:
    service = LabService(session)
    return await _run(
        lambda: service.create_regulatory_assessment_version(
            RegulatoryAssessmentInput(**request.model_dump())
        ),
        _regulatory_record,
    )


@router.post(
    "/release-reviews",
    status_code=status.HTTP_410_GONE,
)
async def create_release_review(
    request: dict[str, Any] | None = Body(default=None),
) -> JSONResponse:
    del request
    return JSONResponse(
        status_code=status.HTTP_410_GONE,
        content={
            "error": {
                "code": "LEGACY_RELEASE_REVIEW_AUTHORITY_RETIRED",
                "message": (
                    "Caller-controlled release reviews are retired; use "
                    "POST /api/v1/lab/v2/claim-authority-reviews."
                ),
            }
        },
    )


@router.post(
    "/claim-authority-reviews",
    status_code=status.HTTP_201_CREATED,
    response_model=ClaimAuthorityReviewResponse,
)
async def create_claim_authority_review(
    request: ClaimAuthorityReviewCreate,
    session: AsyncSession = Depends(get_db),
) -> ResponsePayload:
    service = LabService(session)
    return await _run(
        lambda: service.create_claim_authority_version(
            _claim_authority_command(request),
            parent_version_id=request.parent_version_id,
        ),
        _claim_authority_record,
    )


__all__ = ["router"]
