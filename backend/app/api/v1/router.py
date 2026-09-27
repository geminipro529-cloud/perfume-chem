"""API v1 router aggregation"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    ai,
    engine_jobs,
    enhancements,
    external_validation,
    formulas,
    knowledge,
    lab,
    lab_lifecycle,
    lab_planning,
    lab_reporting,
    mixer,
    optimizer,
    outcomes,
    physical_lineage,
    reference,
)

api_router = APIRouter()

api_router.include_router(
    engine_jobs.router,
    prefix="/lab/v2",
    tags=["laboratory-engine-jobs"],
)

api_router.include_router(
    external_validation.router,
    prefix="/lab/v2",
    tags=["laboratory-external-validation"],
)

api_router.include_router(
    physical_lineage.router,
    prefix="/lab/v2",
    tags=["laboratory-physical-lineage"],
)

api_router.include_router(
    lab_reporting.router,
    prefix="/lab/science",
    tags=["laboratory-science"],
)

api_router.include_router(
    lab_planning.router,
    prefix="/lab/v2",
    tags=["laboratory-planning"],
)

api_router.include_router(
    lab_lifecycle.router,
    prefix="/lab/v2",
    tags=["laboratory-lifecycle"],
)

api_router.include_router(
    lab.router,
    prefix="/lab",
    tags=["laboratory"],
)

api_router.include_router(
    formulas.router,
    prefix="/formulas",
    tags=["formulas"]
)

api_router.include_router(
    ai.router,
    prefix="/ai",
    tags=["ai"]
)

api_router.include_router(
    reference.router,
    tags=["reference_data"]
)

api_router.include_router(
    optimizer.router,
    prefix="/optimizer",
    tags=["optimizer"]
)

api_router.include_router(
    mixer.router,
    prefix="/mixer",
    tags=["mixer"]
)

api_router.include_router(
    knowledge.router,
    prefix="/knowledge",
    tags=["knowledge"]
)

api_router.include_router(
    outcomes.router,
    prefix="/feedback",
    tags=["feedback"]
)

api_router.include_router(
    enhancements.router,
    prefix="/enhance",
    tags=["enhancements"]
)
