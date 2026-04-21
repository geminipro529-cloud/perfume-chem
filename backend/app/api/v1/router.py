"""API v1 router aggregation"""

from fastapi import APIRouter
from app.api.v1.endpoints import formulas, ai, reference, optimizer, mixer, knowledge, outcomes, enhancements

api_router = APIRouter()

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
