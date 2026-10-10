"""Main FastAPI application"""

import ipaddress
import math
import time
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from engine.inventory_completions import completion_log_path
from engine.personal_inventory import addition_log_path
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import db_bootstrap
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.core.request_guard import LocalRequestGuard
from app.core.tracing import setup_tracing
from app.services import app_lock as app_lock_module
from app.services import engine_worker_process, personal_liking

settings = get_settings()
logger = get_logger(__name__)
STATIC_DIR = Path(__file__).resolve().parent / "static"

# ── Simple request rate limiter (per-client, sliding window) ──
_REQUEST_WINDOW = 60  # seconds
_MAX_REQUESTS = 120  # per window, for clients other than this PC
_MAX_REQUESTS_LOOPBACK = 600  # per window, for the page on this PC
_client_requests: dict[str, deque] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    # While the app runs it holds an OS lock beside the database; the
    # stopped-server restore command refuses to run while it is held.
    app_lock = _hold_database_lock()
    try:
        _carry_over_personal_records()
        try:
            alembic_cfg = db_bootstrap.build_alembic_config(
                Path(__file__).resolve().parent.parent / "alembic.ini",
                settings.DATABASE_URL,
            )
            snapshot = db_bootstrap.upgrade_database(alembic_cfg)
            if snapshot is not None:
                logger.info(
                    "Database migration applied. Schema fingerprint: %s",
                    snapshot.schema_fingerprint_sha256,
                )
            else:
                logger.info("Database schema checked; no pre-upgrade snapshot was needed.")
        except Exception:
            logger.exception("Database migration failed; application startup aborted.")
            raise

        await personal_liking.refit_at_startup()

        # Engine jobs run only in a separate worker process.  Start one here so every
        # launch path (plain uvicorn included) gets one; deployments that run their
        # own worker set PERFUME_ENGINE_WORKER_AUTOSTART=0.
        # The supervisor replaces a worker that dies so leased jobs still fail closed.
        worker = (
            engine_worker_process.EngineWorkerSupervisor()
            if engine_worker_process.engine_worker_autostart_enabled()
            else None
        )
        if worker is not None:
            worker.start()
        try:
            yield
        finally:
            # Shutdown
            logger.info("Shutting down application")
            if worker is not None:
                await worker.stop()
    finally:
        if app_lock is not None:
            app_lock.release()


def _carry_over_personal_records() -> None:
    """Resolve the personal stock record paths once at start.

    Older versions kept these records in output/.  Resolving the default paths
    copies any record found only there into data/user/, so it is in place
    before anything reads it.
    """

    try:
        addition_log_path()
        completion_log_path()
    except Exception as error:
        logger.exception("Personal stock records could not be copied; startup aborted.")
        raise RuntimeError(
            f"Your stock records could not be copied into data/user/ ({error}). "
            "Fix the problem, then start the app again."
        ) from error


def _hold_database_lock() -> app_lock_module.AppLock | None:
    database = app_lock_module.sqlite_database_path(settings.DATABASE_URL)
    if database is None:
        return None
    lock_path = app_lock_module.lock_path_for(database)
    held = app_lock_module.try_acquire(lock_path)
    if held is None:
        raise RuntimeError(
            f"Another copy of the app, or a database restore, is using {database} "
            f"(it holds {lock_path}). Stop it, then start the app again."
        )
    return held


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered perfume chemistry and formulation API",
    lifespan=lifespan,
)

# Initialize tracing before middleware so FastAPIInstrumentor wraps all routes
setup_tracing(app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)


def _json_safe(value: Any) -> Any:
    """Turn NaN/Infinity (which JSON cannot carry) into text so a 422 can be sent."""
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Same 422 body as FastAPI's default, but safe when the refused input was NaN/Infinity."""
    return JSONResponse(
        status_code=422, content={"detail": jsonable_encoder(_json_safe(exc.errors()))}
    )


def _is_loopback(host: str) -> bool:
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Gate 0 — Global request rate limiter (sliding window per client IP)."""
    path = request.url.path
    if path == "/app" or path == "/static" or path.startswith("/static/"):
        return await call_next(request)  # the page's own files are never limited
    client_ip = request.client.host if request.client else "unknown"
    limit = _MAX_REQUESTS_LOOPBACK if _is_loopback(client_ip) else _MAX_REQUESTS
    now = time.time()

    window = _client_requests.setdefault(client_ip, deque())
    # Expire old entries
    cutoff = now - _REQUEST_WINDOW
    while window and window[0] < cutoff:
        window.popleft()

    if len(window) >= limit:
        return JSONResponse(
            status_code=429,
            content={
                "detail": f"Rate limit exceeded. Max {limit} requests per {_REQUEST_WINDOW}s."
            },
        )

    window.append(now)
    response = await call_next(request)
    return response


# Added last so it runs first: a refused request never reaches the rate limiter
# (so a hostile page cannot use up this PC's budget) or any route.
app.add_middleware(
    LocalRequestGuard,
    bind_host=settings.API_BIND_HOST,
    extra_hosts=settings.TRUSTED_HOSTS,
    cors_origins=settings.CORS_ORIGINS,
)


# Include routers
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/app", response_class=FileResponse)
async def laboratory_app():
    """Serve the dependency-free local laboratory interface."""
    return STATIC_DIR / "index.html"


@app.get("/")
async def root():
    """Root endpoint"""
    return {"name": settings.APP_NAME, "version": settings.APP_VERSION, "status": "running"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": settings.APP_VERSION}
