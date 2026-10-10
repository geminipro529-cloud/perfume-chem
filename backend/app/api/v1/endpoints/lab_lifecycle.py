"""Thin versioned routes for canonical execution and science authority."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from decimal import Decimal
from typing import Any, TypeAlias, cast

from engine.inventory_baskets import (
    BasketError,
    BasketLogBusyError,
    BasketLogCorruptError,
    basket_list,
    confirmed_baskets,
    load_basket_seed,
    record_basket_choice,
    stock_basket_fields,
)
from engine.inventory_completions import (
    InventoryCompletionConflictError,
    InventoryCompletionError,
    authority_disagreement,
    effective_design_ready,
    inventory_completion_requirements,
    record_inventory_completion,
)
from engine.inventory_dilutions import (
    PREPARED_DILUTION_AUTHORITY,
    PREPARED_DILUTION_PARENT_CHANGED,
    PREPARED_DILUTION_PARENT_HELD,
    PreparedDilutionConflictError,
    PreparedDilutionError,
    dilution_parent_ready,
    record_prepared_dilution,
)
from engine.personal_inventory import (
    DESIGN_ONLY_AUTHORITY,
    LIVE_TEXT_AUTHORITY,
    PersonalInventoryConflictError,
    PersonalInventoryError,
    materialize_personal_inventory,
    personal_inventory_identity_key,
    record_personal_inventory_addition,
)
from engine.research.formula_design import design_inventory_formula
from fastapi import APIRouter, Body, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_db
from app.schemas.lab_lifecycle import (
    AnalyticalResultCreate,
    AnalyticalResultResponse,
    BottleActionCommitCreate,
    BottleActionCommitResponse,
    BottleActionConfirmationCreate,
    BottleActionConfirmationResponse,
    BottleActionEvaluationCreate,
    BottleActionEvaluationResponse,
    BottleActionMeasurementCreate,
    BottleActionMeasurementResponse,
    BottleActionProposalCreate,
    BottleActionProposalResponse,
    BottleReplayResponse,
    ClaimAuthorityReviewCreate,
    ClaimAuthorityReviewResponse,
    FormulaDesignChatCreate,
    FormulaTextParseCreate,
    InventoryCompletionCreate,
    PersonalInventoryAdditionCreate,
    PreparedDilutionCreate,
    QuickBottleEvaluationCreate,
    QuickBottleEvaluationResponse,
    RegulatoryAssessmentCreate,
    RegulatoryAssessmentResponse,
    SensoryResultCreate,
    SensoryResultResponse,
    StockBasketChoiceCreate,
)
from app.services.formula_import import FormulaAnalysisLibrary
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
from app.services.scent_curve import ScentCurveRequest, compute_scent_curve

router = APIRouter()
ResponsePayload: TypeAlias = dict[str, Any] | JSONResponse


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


@router.get("/workbench/formula-library")
async def list_workbench_formula_library() -> dict[str, Any]:
    """List project formula files without importing or mutating them."""

    return {
        "schema_version": "workbench-formula-library-v1",
        "sources": FormulaAnalysisLibrary().list_sources(),
        "inventory_modified": False,
        "compounding_authority": False,
    }


@router.get("/workbench/formula-source", response_model=None)
async def read_workbench_formula_source(source_path: str) -> ResponsePayload:
    """Parse one selected formula as a read-only design-analysis source."""

    try:
        return FormulaAnalysisLibrary().load_source(source_path)
    except ValueError as error:
        return _error_response(error)


@router.post("/workbench/formula-text", response_model=None)
async def parse_workbench_formula_text(request: FormulaTextParseCreate) -> ResponsePayload:
    """Parse a pasted formula table read-only, for the bench sheet."""

    try:
        return FormulaAnalysisLibrary().parse_pasted(request.text, request.name)
    except ValueError as error:
        return _error_response(error)


def _inventory_decimal(value: float) -> str:
    rendered = format(value, ".12f").rstrip("0").rstrip(".")
    return rendered or "0"


def _inventory_source_class(authority: str) -> str:
    if authority == DESIGN_ONLY_AUTHORITY:
        return "PERSONAL_ADDITION"
    if authority == LIVE_TEXT_AUTHORITY:
        return "LIVE_INVENTORY_TEXT"
    if authority == PREPARED_DILUTION_AUTHORITY:
        return "PREPARED_DILUTION"
    return "GOVERNED_STOCK"


_PREPARED_HOLD_TEXT = {
    PREPARED_DILUTION_PARENT_HELD: (
        "Not counted at the gate: its parent bottle is held. Resolve the parent bottle first."
    ),
    PREPARED_DILUTION_PARENT_CHANGED: (
        "Not counted at the gate: the parent bottle's details changed after this dilution "
        "was recorded. Record the dilution again from the bottle as it is now."
    ),
}


def _gate_hold_text(stock: Any) -> str | None:
    """Plain words for why a prepared dilution is held at the gate, else None."""

    if stock.authority != PREPARED_DILUTION_AUTHORITY or stock.execution_ready:
        return None
    holds = str(stock.execution_hold_reason).split("|")
    for hold in (PREPARED_DILUTION_PARENT_CHANGED, PREPARED_DILUTION_PARENT_HELD):
        if hold in holds:
            return _PREPARED_HOLD_TEXT[hold]
    return None


def _workbench_inventory_payload(materialized: Any) -> dict[str, Any]:
    stocks = []
    basket_log_error: str | None = None
    try:
        confirmed = confirmed_baskets()
    except BasketLogCorruptError as error:
        # A damaged log must not break the Lab page: show seed values only.
        confirmed = {}
        basket_log_error = str(error)
    seed = load_basket_seed()
    for stock in materialized.stocks:
        design_ready = effective_design_ready(stock)
        missing_fields = list(inventory_completion_requirements(stock))
        normalized_identity = personal_inventory_identity_key(stock)
        stocks.append(
            {
                "stock_id": stock.stock_id,
                "material": stock.name,
                "identity_name": stock.identity_name or stock.name,
                "normalized_identity": normalized_identity,
                **stock_basket_fields(
                    normalized_identity, confirmed=confirmed, seed=seed
                ),
                "stock_label": stock.raw_name or stock.name,
                "fraction_decimal": _inventory_decimal(stock.dilution),
                "fraction_percent_decimal": _inventory_decimal(stock.dilution * 100),
                "fraction_basis": stock.fraction_basis,
                "carrier": stock.carrier or None,
                "physical_form": stock.physical_form or None,
                "homogeneity": stock.homogeneity or None,
                "category": stock.category,
                "status": stock.status,
                "design_ready": design_ready,
                "design_hold_reason": stock.design_hold_reason or None,
                "missing_fields": missing_fields,
                "completion_available": (
                    stock.status.casefold() == "owned"
                    and stock.stock_id in materialized.canonical_stock_ids
                    and stock.authority != PREPARED_DILUTION_AUTHORITY
                ),
                "dilution_available": (
                    stock.status.casefold() == "owned"
                    and stock.stock_id in materialized.canonical_stock_ids
                    and dilution_parent_ready(stock)
                ),
                "completion_event_sha256": stock.completion_event_sha256 or None,
                "completion_source_ref": stock.completion_source_ref or None,
                # RULE 0: the Stock page entry wins; say what the workbook said.
                "authority_disagreement": authority_disagreement(stock),
                "execution_ready": stock.execution_ready,
                "execution_hold_reason": stock.execution_hold_reason or None,
                "gate_hold_text": _gate_hold_text(stock),
                "authority": stock.authority,
                "source_class": _inventory_source_class(stock.authority),
                "source_rows": list(stock.source_rows),
                "source_ref": stock.source_ref,
            }
        )
    payload: dict[str, Any] = {
        "schema_version": "workbench-current-inventory-v3",
        "authority": "PERSONAL_DESIGN_INVENTORY_PROJECTION_READ_ONLY",
        "completion_authority": "DIRECT_USER_CONFIRMATION_FOR_PERSONAL_DESIGN_ONLY",
        "display_source": (
            "governed stocks, every owned inventory.txt row, personal completion "
            "receipts, and append-only personal additions"
        ),
        "snapshot_sha256": materialized.snapshot_sha256,
        "overlay_sha256": materialized.overlay_sha256,
        "completion_sha256": materialized.completion_sha256 or None,
        "inventory_text_sha256": materialized.inventory_text_sha256,
        "addition_log_sha256": materialized.addition_log_sha256 or None,
        "canonical_effective_inventory_sha256": (
            materialized.canonical_effective_inventory_sha256
        ),
        "effective_inventory_sha256": materialized.effective_inventory_sha256,
        "source_workbook_sha256": materialized.source_workbook_sha256,
        "counts": {
            "stocks": len(stocks),
            "unique_identities": len(
                {stock["identity_name"].casefold() for stock in stocks}
            ),
            "design_ready": sum(stock["design_ready"] for stock in stocks),
            "details_incomplete": sum(not stock["design_ready"] for stock in stocks),
            "execution_ready": sum(stock["execution_ready"] for stock in stocks),
            "governed_stocks": sum(
                stock["source_class"] == "GOVERNED_STOCK" for stock in stocks
            ),
            "live_inventory_text": sum(
                stock["source_class"] == "LIVE_INVENTORY_TEXT" for stock in stocks
            ),
            "personal_additions": sum(
                stock["source_class"] == "PERSONAL_ADDITION" for stock in stocks
            ),
            "prepared_dilutions": sum(
                stock["source_class"] == "PREPARED_DILUTION" for stock in stocks
            ),
            "requirements": len(materialized.requirements),
        },
        "stocks": stocks,
        "baskets": basket_list(),
        "inventory_modified": False,
        "compounding_authority": False,
    }
    if basket_log_error is not None:
        payload["basket_log_error"] = basket_log_error
    return payload


@router.get("/workbench/current-inventory")
async def read_workbench_current_inventory() -> dict[str, Any]:
    """Expose the complete personal-design inventory without copying it to the DB."""

    return _workbench_inventory_payload(materialize_personal_inventory())


@router.post("/workbench/current-inventory/complete", response_model=None)
async def complete_workbench_inventory(
    request: InventoryCompletionCreate,
) -> ResponsePayload:
    """Persist explicit stock facts without granting physical action authority."""

    try:
        fraction_decimal = (
            format(Decimal(request.fraction_percent_decimal) / Decimal("100"), "f")
            if request.fraction_percent_decimal is not None
            else None
        )
        receipt, materialized = record_inventory_completion(
            stock_id=request.stock_id,
            expected_effective_inventory_sha256=(
                request.expected_effective_inventory_sha256
            ),
            idempotency_key=request.idempotency_key,
            fraction_decimal=fraction_decimal,
            fraction_basis=request.fraction_basis,
            carrier=request.carrier,
            physical_form=request.physical_form,
            possession_confirmed=request.possession_confirmed,
            homogeneity=request.homogeneity,
            final_fraction_known=request.final_fraction_known,
            source_kind=request.source_kind,
            user_note=request.user_note,
        )
        updated = next(
            stock for stock in materialized.stocks if stock.stock_id == request.stock_id
        )
        return {
            "schema_version": "personal-inventory-completion-result-v1",
            "status": (
                "PERSONAL_DESIGN_DETAILS_COMPLETE"
                if effective_design_ready(updated)
                else "INVENTORY_DETAILS_STILL_INCOMPLETE"
            ),
            "receipt": receipt,
            "updated_stock_id": updated.stock_id,
            "design_ready": effective_design_ready(updated),
            "missing_fields": list(inventory_completion_requirements(updated)),
            "inventory": _workbench_inventory_payload(
                materialize_personal_inventory(canonical=materialized)
            ),
            "inventory_details_modified": True,
            "inventory_quantity_modified": False,
            "release_authority": False,
            "safety_authority": False,
            "compounding_authority": False,
            "evidence_admission_authorized": False,
        }
    except InventoryCompletionConflictError as error:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": {"code": error.code, "message": str(error)}},
        )
    except InventoryCompletionError as error:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": {"code": error.code, "message": str(error)}},
        )


@router.post("/workbench/current-inventory/dilute", response_model=None)
async def dilute_workbench_inventory(
    request: PreparedDilutionCreate,
) -> ResponsePayload:
    """Record a dilution prepared from an owned bottle as a new gate stock."""

    try:
        event, materialized = record_prepared_dilution(
            parent_stock_id=request.parent_stock_id,
            expected_effective_inventory_sha256=(
                request.expected_effective_inventory_sha256
            ),
            idempotency_key=request.idempotency_key,
            fraction_decimal=format(
                Decimal(request.fraction_percent_decimal) / Decimal("100"), "f"
            ),
            fraction_basis=request.fraction_basis,
            carrier=request.carrier,
            amount_made_g=request.amount_made_g or "",
            prepared_on=(
                request.prepared_on.isoformat() if request.prepared_on else ""
            ),
            user_note=request.user_note,
        )
        prepared = next(
            (
                stock
                for stock in materialized.stocks
                if stock.completion_event_sha256 == event["event_sha256"]
            ),
            None,
        )
        return {
            "schema_version": "prepared-dilution-result-v1",
            "status": "PREPARED_DILUTION_RECORDED",
            "receipt": event,
            "prepared_stock_id": prepared.stock_id if prepared else None,
            "inventory": _workbench_inventory_payload(
                materialize_personal_inventory(canonical=materialized)
            ),
            "inventory_details_modified": True,
            "inventory_quantity_modified": False,
            "release_authority": False,
            "safety_authority": False,
            "compounding_authority": False,
            "evidence_admission_authorized": False,
        }
    except PreparedDilutionConflictError as error:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": {"code": error.code, "message": str(error)}},
        )
    except PreparedDilutionError as error:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": {"code": error.code, "message": str(error)}},
        )


@router.post("/workbench/current-inventory/basket", response_model=None)
async def set_workbench_inventory_basket(
    request: StockBasketChoiceCreate,
) -> ResponsePayload:
    """Record which basket Kenny keeps a material in (Lab page display only)."""

    stock = next(
        (
            item
            for item in materialize_personal_inventory().stocks
            if personal_inventory_identity_key(item) == request.normalized_identity
        ),
        None,
    )
    if stock is None:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "BASKET_IDENTITY_NOT_IN_INVENTORY",
                    "message": "normalized_identity is not in the current inventory",
                }
            },
        )
    try:
        # In a worker thread: waiting on a held basket-log lock must not stall other requests.
        event = await run_in_threadpool(
            record_basket_choice,
            normalized_identity=request.normalized_identity,
            identity_name=stock.identity_name or stock.name,
            basket=request.basket,
        )
    except BasketLogBusyError as error:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": {"code": error.code, "message": str(error)}},
        )
    except BasketLogCorruptError as error:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": {"code": error.code, "message": str(error)}},
        )
    except BasketError as error:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": error.code, "message": str(error)}},
        )
    return {
        "normalized_identity": request.normalized_identity,
        "basket": event["basket"],
        "basket_status": "confirmed",
    }


@router.post("/workbench/current-inventory/add", response_model=None)
async def add_workbench_inventory_material(
    request: PersonalInventoryAdditionCreate,
) -> ResponsePayload:
    """Record a missing owned stock for personal design without action authority."""

    try:
        receipt, projection = record_personal_inventory_addition(
            expected_design_inventory_sha256=request.expected_design_inventory_sha256,
            idempotency_key=request.idempotency_key,
            identity_name=request.identity_name,
            category=request.category,
            fraction_decimal=format(
                Decimal(request.fraction_percent_decimal) / Decimal("100"), "f"
            ),
            fraction_basis=request.fraction_basis,
            carrier=request.carrier,
            physical_form=request.physical_form,
            possession_confirmed=request.possession_confirmed,
            homogeneity=request.homogeneity,
            source_kind=request.source_kind,
            supplier_name=request.supplier_name,
            supplier_sku=request.supplier_sku,
            user_note=request.user_note,
        )
        added_stock = next(
            stock
            for stock in projection.stocks
            if stock.completion_event_sha256 == receipt["event_sha256"]
        )
        return {
            "schema_version": "personal-inventory-addition-result-v1",
            "status": "PERSONAL_INVENTORY_MATERIAL_ADDED",
            "receipt": receipt,
            "added_stock_id": added_stock.stock_id,
            "inventory": _workbench_inventory_payload(projection),
            "inventory_details_modified": True,
            "inventory_quantity_modified": False,
            "release_authority": False,
            "safety_authority": False,
            "compounding_authority": False,
            "evidence_admission_authorized": False,
        }
    except PersonalInventoryConflictError as error:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": {"code": error.code, "message": str(error)}},
        )
    except PersonalInventoryError as error:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": {"code": error.code, "message": str(error)}},
        )


@router.post("/workbench/formula-chat", response_model=None)
async def formulate_from_conversation(
    request: FormulaDesignChatCreate,
) -> ResponsePayload:
    """Create a read-only inventory-grounded draft from one conversational turn."""

    try:
        return cast(
            dict[str, Any],
            design_inventory_formula(
                idea=request.message,
                formula_name=request.formula_name,
                liquid_concentrate_ul_decimal=request.liquid_concentrate_ul_decimal,
                max_materials=request.max_materials,
                must_preserve=request.must_preserve,
                must_avoid=request.must_avoid,
                previous_stock_ids=request.previous_stock_ids,
                conversation_context=request.conversation_context,
                execution_strategy=request.execution_strategy,
                appeal_mode=request.appeal_mode,
                comparison_evidence=request.comparison_evidence,
                active_bottle_id=request.active_bottle_id,
                design_mode=request.design_mode,
                variant_count=request.variant_count,
            ),
        )
    except ValueError as error:
        return _error_response(error)


@router.post("/workbench/scent-curve", response_model=None)
async def scent_curve_for_rows(request: ScentCurveRequest) -> dict[str, Any]:
    """Screening time curve (modelled detectable share) for a drafted formula."""

    return cast(dict[str, Any], await run_in_threadpool(compute_scent_curve, request.rows))


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


def _evaluation_record(record: Any) -> dict[str, Any]:
    payload = dict(record.payload_json)
    return {
        "id": record.id,
        "bottle_id": record.bottle_id,
        "stream_sequence": record.stream_sequence,
        "event_type": record.event_type,
        "proposal_id": payload["proposal_id"],
        "action_commit_id": payload["action_commit_id"],
        "addition_bottle_event_id": payload["addition_bottle_event_id"],
        "evaluated_at": payload["evaluated_at"],
        "waited_seconds": payload["waited_seconds"],
        "reaction": payload["reaction"],
        "decision": payload["decision"],
        "evidence_scope": payload["evidence_scope"],
        "controlled_causal_evidence": payload["controlled_causal_evidence"],
        "population_generalization_authorized": payload[
            "population_generalization_authorized"
        ],
        "release_authority": payload["release_authority"],
        "safety_authority": payload["safety_authority"],
        "compounding_authority": payload["compounding_authority"],
        "evidence_admission_authorized": payload[
            "evidence_admission_authorized"
        ],
        "created_at": record.created_at,
    }


def _quick_evaluation_record(record: Any) -> dict[str, Any]:
    payload = dict(record.payload_json)
    return {
        "id": record.id,
        "bottle_id": record.bottle_id,
        "stream_sequence": record.stream_sequence,
        "event_type": record.event_type,
        "addition_event_ids": list(payload["addition_event_ids"]),
        "goal_analysis_sha256": payload["goal_analysis_sha256"],
        "hypothesis_id": payload["hypothesis_id"],
        "hypothesis_variant": payload["hypothesis_variant"],
        "evaluated_at": payload["evaluated_at"],
        "waited_seconds": payload["waited_seconds"],
        "reaction": payload["reaction"],
        "decision": payload["decision"],
        "evidence_scope": payload["evidence_scope"],
        "controlled_causal_evidence": payload["controlled_causal_evidence"],
        "population_generalization_authorized": payload[
            "population_generalization_authorized"
        ],
        "release_authority": payload["release_authority"],
        "safety_authority": payload["safety_authority"],
        "compounding_authority": payload["compounding_authority"],
        "evidence_admission_authorized": payload[
            "evidence_admission_authorized"
        ],
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


@router.post(
    "/actions/{proposal_id}/evaluations",
    status_code=status.HTTP_201_CREATED,
    response_model=BottleActionEvaluationResponse,
)
async def evaluate_action(
    proposal_id: str,
    request: BottleActionEvaluationCreate,
    session: AsyncSession = Depends(get_db),
) -> ResponsePayload:
    service = LabService(session)
    return await _run(
        lambda: service.record_bottle_action_evaluation(
            proposal_id=proposal_id,
            **request.model_dump(),
        ),
        _evaluation_record,
    )


@router.post(
    "/bottles/{bottle_id}/quick-evaluations",
    status_code=status.HTTP_201_CREATED,
    response_model=QuickBottleEvaluationResponse,
)
async def record_quick_bottle_evaluation(
    bottle_id: str,
    request: QuickBottleEvaluationCreate,
    session: AsyncSession = Depends(get_db),
) -> ResponsePayload:
    service = LabService(session)
    return await _run(
        lambda: service.record_quick_bottle_evaluation(
            bottle_id=bottle_id,
            **request.model_dump(),
        ),
        _quick_evaluation_record,
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
