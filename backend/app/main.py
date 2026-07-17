"""Main FastAPI application"""

import time
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import db_bootstrap
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.core.tracing import setup_tracing

settings = get_settings()
logger = get_logger(__name__)
STATIC_DIR = Path(__file__).resolve().parent / "static"

# ── Simple request rate limiter (per-client, sliding window) ──
_REQUEST_WINDOW = 60  # seconds
_MAX_REQUESTS = 120  # per window
_client_requests: dict[str, deque] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")

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
            logger.info("Database migration applied without a file snapshot.")
    except Exception:
        logger.exception("Database migration failed; application startup aborted.")
        raise

    yield

    # Shutdown
    logger.info("Shutting down application")


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


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Gate 0 — Global request rate limiter (sliding window per client IP)."""
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()

    window = _client_requests.setdefault(client_ip, deque())
    # Expire old entries
    cutoff = now - _REQUEST_WINDOW
    while window and window[0] < cutoff:
        window.popleft()

    if len(window) >= _MAX_REQUESTS:
        return JSONResponse(
            status_code=429,
            content={
                "detail": f"Rate limit exceeded. Max {_MAX_REQUESTS} requests per {_REQUEST_WINDOW}s."
            },
        )

    window.append(now)
    response = await call_next(request)
    return response


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
