"""Canonical local-first laboratory endpoints."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from engine.bottle_addition import BottleSnapshot, PipetteProfile, StockSolution
from engine.intervention_hypotheses import InterventionHypothesisRequest
from engine.intervention_trial import InterventionTrialRequest
from engine.interventions import (
    VERSIONED_FINISHED_PRODUCT_SAFETY,
    BriefConstraints,
    CandidateAddition,
    InterventionRequest,
    InventoryStock,
)
from engine.inventory_parser import parse_inventory
from engine.name_utils import normalize_name
from engine.safety_assessment import SafetyAssessmentStatus
from engine.workbench import PerfumeWorkbench
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.v1.endpoints.formulas import _to_workbench_request
from app.models.lab import (
    LabBottle,
    LabExperiment,
    LabFormula,
    LabFormulaVersion,
    LabMaterial,
    LabMaterialAlias,
    LabStockSolution,
)
from app.schemas.lab import (
    AliasCreate,
    ApplicationCreate,
    AssistantPacketCreate,
    BackupCreate,
    BottleAdditionCreate,
    BottleCloseCreate,
    BottleCompensationCreate,
    BottleCreate,
    BottleTransferCreate,
    ExperimentCreate,
    FormulaVersionCreate,
    InterventionCreate,
    InterventionHypothesisCreate,
    InterventionTrialPlanCreate,
    LabFormulaCreate,
    MaterialCreate,
    ObservationCreate,
    OutcomeCreate,
    PairwiseComparisonCreate,
    PredictionCreate,
    RestoreSnapshotCreate,
    SampleCreate,
    StockCreate,
    StockPreparationFinalizeCreate,
    StockUpdateRemaining,
)
from app.schemas.perfume import FormulaCreate
from app.services.backup_service import (
    BackupService,
    RestoreSafetyError,
    backup_service_for_database_url,
)
from app.services.engine_job_compatibility import (
    enqueue_formula_analysis_compatibility,
)
from app.services.lab_assistant import AssistantRequest, build_assistant_packet
from app.services.lab_export import ImportConflictError, LabExportService
from app.services.lab_service import (
    FormulaComponentInput,
    LabService,
    LabTransactionError,
)
from app.services.validation_pipeline import attach_validation, validate_formula

router = APIRouter()
workbench = PerfumeWorkbench()


@router.get("/dashboard")
async def dashboard(session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    models = {
        "materials": LabMaterial,
        "stocks": LabStockSolution,
        "formulas": LabFormula,
        "bottles": LabBottle,
        "experiments": LabExperiment,
    }
    counts = {
        name: int(await session.scalar(select(func.count()).select_from(model)) or 0)
        for name, model in models.items()
    }
    return {
        "counts": counts,
        "warnings": [
            "Regulatory results remain unverified without versioned category and constituent evidence.",
            "Preference models remain not_validated until held-out baseline gates pass.",
        ],
    }


@router.get("/materials")
async def list_materials(session: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    rows = (
        await session.execute(select(LabMaterial).order_by(LabMaterial.canonical_name))
    ).scalars()
    return [_record(row, "canonical_name", "cas_number") for row in rows]


@router.post("/materials", status_code=status.HTTP_201_CREATED)
async def create_material(
    request: MaterialCreate, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    row = await _service_call(LabService(session).create_material(request.canonical_name))
    return _record(row, "canonical_name", "cas_number")


@router.get("/materials/{material_id}")
async def get_material(material_id: str, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    row = await _service_call(LabService(session).repository.get_material(material_id))
    return _record(row, "canonical_name", "cas_number")


@router.get("/materials/resolve/{name}")
async def resolve_material(name: str, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    # Try exact match on canonical_name first
    result = (
        await session.execute(select(LabMaterial).where(LabMaterial.canonical_name == name))
    ).scalar_one_or_none()
    if result is not None:
        return _record(result, "canonical_name", "cas_number")
    # Try alias resolution
    alias_row = (
        await session.execute(
            select(LabMaterialAlias).where(
                LabMaterialAlias.normalized_alias == name.lower().strip()
            )
        )
    ).scalar_one_or_none()
    if alias_row is not None:
        material = await _service_call(
            LabService(session).repository.get_material(alias_row.material_id)
        )
        return _record(material, "canonical_name", "cas_number")
    raise HTTPException(status_code=404, detail=f"Material not found: {name}")


@router.post("/materials/{material_id}/aliases", status_code=status.HTTP_201_CREATED)
async def add_material_alias(
    material_id: str,
    request: AliasCreate,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    alias = await _service_call(
        LabService(session).create_material_alias(
            material_id,
            request.alias,
        )
    )
    return _record(alias, "alias", "normalized_alias", "material_id")


@router.get("/stocks")
async def list_stocks(session: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    rows = (
        await session.execute(select(LabStockSolution).order_by(LabStockSolution.created_at))
    ).scalars()
    return [
        _record(
            row,
            "material_id",
            "active_fraction",
            "fraction_basis",
            "initial_mass_g",
            "density_g_ml",
        )
        for row in rows
    ]


@router.post("/stocks", status_code=status.HTTP_201_CREATED)
async def create_stock(
    request: StockCreate, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    row = await _service_call(LabService(session).create_stock_solution(**request.model_dump()))
    return _record(
        row,
        "material_id",
        "active_fraction",
        "fraction_basis",
        "initial_mass_g",
        "density_g_ml",
    )


@router.get("/bottles")
async def list_bottles(session: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    rows = (await session.execute(select(LabBottle).order_by(LabBottle.created_at))).scalars()
    return [_record(row, "label", "status", "batch_id") for row in rows]


@router.post("/bottles", status_code=status.HTTP_201_CREATED)
async def create_bottle(
    request: BottleCreate, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    row = await _service_call(
        LabService(session).create_bottle(request.label, initial_mass_g=request.initial_mass_g)
    )
    return _record(row, "label", "status", "batch_id")


@router.get("/bottles/{bottle_id}")
async def bottle_state(bottle_id: str, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    state_row = await _service_call(LabService(session).reconstruct_bottle(bottle_id))
    return asdict(state_row)


@router.post("/bottles/{bottle_id}/additions", status_code=status.HTTP_201_CREATED)
async def add_to_bottle(
    bottle_id: str,
    request: BottleAdditionCreate,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    payload = request.model_dump(exclude={"role"})
    operation = (
        LabService(session).add_solvent_to_bottle
        if request.role == "solvent"
        else LabService(session).add_stock_to_bottle
    )
    row = await _service_call(
        operation(bottle_id=bottle_id, **payload)
    )
    record = _record(row, "bottle_id", "stream_sequence", "event_type", "transaction_id")
    record["execution_scope"] = row.payload_json.get(
        "execution_scope",
        "LEGACY_FREEFORM_UNBOUND_QUARANTINE",
    )
    record["formula_execution_authority"] = bool(
        row.payload_json.get("formula_execution_authority", False)
    )
    record["build_plan_fulfillment_authority"] = bool(
        row.payload_json.get("build_plan_fulfillment_authority", False)
    )
    return record


@router.post("/bottles/{bottle_id}/close", status_code=status.HTTP_201_CREATED)
async def close_bottle(
    bottle_id: str,
    request: BottleCloseCreate,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    row = await _service_call(
        LabService(session).close_bottle(
            bottle_id=bottle_id,
            **request.model_dump(),
        )
    )
    return _record(
        row,
        "bottle_id",
        "stream_sequence",
        "event_type",
        "transaction_id",
    )


@router.post("/transfers", status_code=status.HTTP_201_CREATED)
async def transfer(
    request: BottleTransferCreate, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    source, destination = await _service_call(
        LabService(session).transfer_between_bottles(**request.model_dump())
    )
    return {
        "source_event": _record(source, "bottle_id", "stream_sequence", "transaction_id"),
        "destination_event": _record(destination, "bottle_id", "stream_sequence", "transaction_id"),
    }


@router.post("/compensations", status_code=status.HTTP_201_CREATED)
async def compensate(
    request: BottleCompensationCreate, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    row = await _service_call(LabService(session).compensate_bottle_event(**request.model_dump()))
    return _record(row, "bottle_id", "stream_sequence", "correction_of_event_id")


@router.get("/formulas")
async def list_formulas(session: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    rows = (await session.execute(select(LabFormula).order_by(LabFormula.created_at))).scalars()
    return [_record(row, "name") for row in rows]


@router.post("/formulas", status_code=status.HTTP_201_CREATED)
async def create_formula(
    request: LabFormulaCreate, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    row = await _service_call(LabService(session).create_formula(request.name))
    return _record(row, "name")


@router.post("/formulas/{formula_id}/versions", status_code=status.HTTP_201_CREATED)
async def create_formula_version(
    formula_id: str,
    request: FormulaVersionCreate,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    payload = request.model_dump(exclude={"components"})
    components = tuple(
        FormulaComponentInput(**component.model_dump())
        for component in request.components
    )
    row = await _service_call(
        LabService(session).add_formula_version(
            formula_id,
            **payload,
            components=components,
        )
    )
    return await _formula_version_record(row, session)


@router.get("/experiments")
async def list_experiments(session: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    rows = (
        await session.execute(select(LabExperiment).order_by(LabExperiment.created_at))
    ).scalars()
    return [_record(row, "name", "status", "protocol_json") for row in rows]


@router.post("/experiments", status_code=status.HTTP_201_CREATED)
async def create_experiment(
    request: ExperimentCreate, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    row = await _service_call(
        LabService(session).create_experiment(
            request.name, protocol=request.protocol, status=request.status
        )
    )
    return _record(row, "name", "status", "protocol_json")


@router.post("/experiments/{experiment_id}/samples", status_code=status.HTTP_201_CREATED)
async def add_sample(
    experiment_id: str,
    request: SampleCreate,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    row = await _service_call(
        LabService(session).add_experiment_sample(
            experiment_id=experiment_id, **request.model_dump()
        )
    )
    return _record(row, "experiment_id", "bottle_id", "blind_code")


@router.post("/applications", status_code=status.HTTP_201_CREATED)
async def record_application(
    request: ApplicationCreate, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    row = await _service_call(LabService(session).record_application(**request.model_dump()))
    return _record(row, "sample_id", "applied_at", "dose_json", "context_json")


@router.post("/applications/{application_id}/observations", status_code=status.HTTP_201_CREATED)
async def record_observation(
    application_id: str,
    request: ObservationCreate,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    row = await _service_call(
        LabService(session).record_observation(
            application_id=application_id, **request.model_dump()
        )
    )
    return _record(row, "application_id", "elapsed_seconds", "observations_json")


@router.post("/comparisons", status_code=status.HTTP_201_CREATED)
async def record_comparison(
    request: PairwiseComparisonCreate, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    row = await _service_call(
        LabService(session).record_pairwise_comparison(**request.model_dump())
    )
    return _record(row, "experiment_id", "left_sample_id", "right_sample_id", "preferred_sample_id")


@router.post("/predictions", status_code=status.HTTP_201_CREATED)
async def record_prediction(
    request: PredictionCreate, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    row = await _service_call(LabService(session).record_prediction(**request.model_dump()))
    return _record(row, "experiment_id", "sample_id", "model_key", "model_version", "status")


@router.post("/outcomes", status_code=status.HTTP_201_CREATED)
async def record_outcome(
    request: OutcomeCreate, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    row = await _service_call(LabService(session).record_outcome(**request.model_dump()))
    return _record(row, "experiment_id", "prediction_id", "outcome_json")


@router.post("/analysis")
async def analyze(
    request: FormulaCreate,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    percentages: dict[str, float] = {}
    for ingredient in request.ingredients:
        percentages[ingredient.name] = (
            percentages.get(ingredient.name, 0.0) + ingredient.percentage
        )
    validation = await enqueue_formula_analysis_compatibility(
        session,
        validate_formula(percentages),
        percentages,
        scope="lab.analysis",
        formula_name=request.name,
    )
    try:
        payload = cast(
            dict[str, Any],
            workbench.analyze(_to_workbench_request(request)).as_dict(),
        )
        return attach_validation(payload, validation)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/interventions")
async def interventions(request: InterventionCreate) -> dict[str, Any]:
    result = workbench.rank_interventions(
        InterventionRequest(
            batch_mass_g=request.batch_mass_g,
            brief=BriefConstraints(**request.brief.model_dump()),
            inventory={
                row.material: InventoryStock(**row.model_dump()) for row in request.inventory
            },
            candidates=tuple(
                CandidateAddition(
                    **row.model_dump(exclude={"safety_status"}),
                    safety_status=SafetyAssessmentStatus(row.safety_status),
                )
                for row in request.candidates
            ),
        )
    )
    return {
        "ranked": [asdict(row) for row in result.ranked],
        "rejected": [asdict(row) for row in result.rejected],
        "evidence": result.evidence.as_dict(),
        "safety_authority": {
            "client_declared_status_authoritative": False,
            "required_authority": VERSIONED_FINISHED_PRODUCT_SAFETY,
            "formula_state_binding_required": True,
            "achieved_dose_coverage_required": True,
            "public_request_can_authorize_skin_use": False,
        },
    }


@router.post("/intervention-hypotheses")
async def intervention_hypotheses(
    request: InterventionHypothesisCreate,
) -> dict[str, object]:
    inventory = parse_inventory(
        unique=True,
        include_solvents=False,
        include_unavailable=False,
    )
    try:
        result = workbench.generate_intervention_hypotheses(
            InterventionHypothesisRequest(
                **request.model_dump(),
                available_materials=tuple(item.name for item in inventory),
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return cast(dict[str, object], result.as_dict())


@router.post("/intervention-trials/plan")
async def intervention_trial_plan(
    request: InterventionTrialPlanCreate,
) -> dict[str, object]:
    inventory = parse_inventory(
        unique=True,
        include_solvents=False,
        include_unavailable=False,
    )
    available = {normalize_name(item.name): item.name for item in inventory}
    material = available.get(normalize_name(request.material))
    if material is None:
        raise HTTPException(
            status_code=400,
            detail=f"material is not in the available inventory: {request.material}",
        )
    try:
        result = workbench.plan_intervention_trial(
            InterventionTrialRequest(
                brief_name=request.brief_name,
                material=material,
                bottle=BottleSnapshot(
                    total_mass_g=request.bottle_total_mass_g,
                    active_material_mass_g=request.current_material_active_mass_g,
                ),
                stock=StockSolution(
                    active_mass_fraction=request.stock_active_mass_fraction,
                    density_g_ml=request.stock_density_g_ml,
                ),
                target_active_ppm_w_w=request.target_active_ppm_w_w,
                threshold_matrix=request.threshold_matrix,
                pipette=(
                    PipetteProfile(**request.pipette.model_dump())
                    if request.pipette is not None
                    else None
                ),
                evaluation_attribute=request.evaluation_attribute,
                evaluation_times_seconds=request.evaluation_times_seconds,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return cast(dict[str, object], result.as_dict())


@router.post("/assistant")
async def assistant(request: AssistantPacketCreate) -> dict[str, Any]:
    return build_assistant_packet(AssistantRequest(**request.model_dump())).as_dict()


@router.get("/export")
async def export_workspace(session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await LabExportService(session).export_workspace()


@router.post("/import")
async def import_workspace(
    packet: dict[str, Any], session: AsyncSession = Depends(get_db)
) -> dict[str, int]:
    try:
        return (await LabExportService(session).import_workspace(packet)).as_dict()
    except ImportConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/backups", status_code=status.HTTP_201_CREATED)
async def create_backup(
    request: BackupCreate, session: AsyncSession = Depends(get_db)
) -> dict[str, object]:
    try:
        return _backup_service(session).create_backup(request.label).as_dict()
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/backups/validate")
async def validate_backup(
    request: RestoreSnapshotCreate, session: AsyncSession = Depends(get_db)
) -> dict[str, object]:
    try:
        return _backup_service(session).validate_restore(Path(request.snapshot_path)).as_dict()
    except RestoreSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/restores/stage", status_code=status.HTTP_201_CREATED)
async def stage_restore(
    request: RestoreSnapshotCreate, session: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    try:
        staged = _backup_service(session).stage_restore(Path(request.snapshot_path))
    except RestoreSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    # The server never replaces its own open database; the launcher does it.
    return {
        **staged.as_dict(),
        "message": (
            "Validated. Stop the app, then run: python run_api_server.py "
            f"--restore {staged.source_snapshot_path.name}"
        ),
    }


@router.post("/stocks/preparations/finalize", status_code=status.HTTP_201_CREATED)
async def finalize_stock_preparation(
    request: StockPreparationFinalizeCreate,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    row = await _service_call(
        LabService(session).finalize_stock_preparation(**request.model_dump())
    )
    return _record(
        row,
        "material_id",
        "supplier",
        "lot_number",
        "active_fraction",
        "active_fraction_decimal_text",
        "fraction_basis",
        "density_g_ml",
        "solvent_name",
        "initial_mass_g",
        "remaining_mass_g",
        "source_json",
    )


@router.get("/stocks/{stock_id}")
async def get_stock(stock_id: str, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    service = LabService(session)
    row = await _service_call(service.repository.get_stock(stock_id))
    payload = _record(
        row,
        "material_id",
        "supplier",
        "lot_number",
        "active_fraction",
        "active_fraction_decimal_text",
        "fraction_basis",
        "initial_mass_g",
        "density_g_ml",
        "solvent_name",
        "remaining_mass_g",
        "source_json",
    )
    payload["remaining_mass_g"] = await _service_call(service.stock_balance_g(stock_id))
    return payload


@router.patch("/stocks/{stock_id}/remaining")
async def update_stock_remaining(
    stock_id: str,
    request: StockUpdateRemaining,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    service = LabService(session)
    stock = await _service_call(
        service.reconcile_stock_balance(stock_id, request.remaining_mass_g)
    )
    payload = _record(
        stock,
        "material_id",
        "active_fraction",
        "initial_mass_g",
        "remaining_mass_g",
    )
    payload["remaining_mass_g"] = await _service_call(service.stock_balance_g(stock_id))
    return payload


@router.get("/formulas/{formula_id}")
async def get_formula(formula_id: str, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    service = LabService(session)
    formula = await service.repository.get_formula(formula_id)
    if formula is None:
        raise HTTPException(status_code=404, detail=f"Formula not found: {formula_id}")
    latest = (
        await session.execute(
            select(LabFormulaVersion)
            .where(LabFormulaVersion.formula_id == formula_id)
            .order_by(LabFormulaVersion.version_number.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    payload = _record(formula, "name")
    payload["latest_version"] = latest.version_number if latest else None
    return payload


@router.get("/formulas/{formula_id}/versions")
async def list_formula_versions(
    formula_id: str, session: AsyncSession = Depends(get_db)
) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            select(LabFormulaVersion)
            .where(LabFormulaVersion.formula_id == formula_id)
            .order_by(LabFormulaVersion.version_number)
        )
    ).scalars()
    return [await _formula_version_record(row, session) for row in rows]


@router.get("/formulas/{formula_id}/versions/{version_number}")
async def get_formula_version(
    formula_id: str, version_number: int, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    row = (
        await session.execute(
            select(LabFormulaVersion).where(
                LabFormulaVersion.formula_id == formula_id,
                LabFormulaVersion.version_number == version_number,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=404, detail=f"Version {version_number} not found for formula {formula_id}"
        )
    return await _formula_version_record(row, session)


async def _formula_version_record(
    row: LabFormulaVersion,
    session: AsyncSession,
) -> dict[str, Any]:
    components = await LabService(session).repository.formula_components(row.id)
    payload = _record(
        row,
        "formula_id",
        "version_number",
        "brief_json",
        "constraints_json",
        "concentration_fraction",
        "concentration_basis",
        "source_json",
    )
    payload["composition_status"] = "recorded" if components else "missing"
    payload["components"] = [
        _record(
            component,
            "stock_solution_id",
            "position",
            "requested_mass_g",
            "requested_volume_ul",
            "role",
            "unit",
        )
        for component in components
    ]
    return payload


async def _service_call(awaitable):
    try:
        return await awaitable
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LabTransactionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _record(record, *fields: str) -> dict[str, Any]:
    payload: dict[str, Any] = {"id": record.id}
    created_at = getattr(record, "created_at", None)
    if created_at is not None:
        payload["created_at"] = created_at.isoformat()
    for field in fields:
        value = getattr(record, field)
        payload[field] = value.isoformat() if isinstance(value, datetime) else value
    return payload


def _backup_service(session: AsyncSession) -> BackupService:
    bind = session.get_bind()
    url = bind.engine.url if isinstance(bind, Connection) else bind.url
    try:
        return backup_service_for_database_url(url)
    except RestoreSafetyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
