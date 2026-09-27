"""Test configuration and fixtures"""

import asyncio
import os
import shutil
import tempfile
import warnings
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.main import app
from app.models.base import Base

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTEST_TEMP_ROOT = REPO_ROOT / "output" / "pytest-temp-backend"
PYTEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
os.environ["TEMP"] = str(PYTEST_TEMP_ROOT)
os.environ["TMP"] = str(PYTEST_TEMP_ROOT)
tempfile.tempdir = str(PYTEST_TEMP_ROOT)

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_perfume_chem.db"
_SESSION_SCRATCH = None


@pytest.fixture(scope="session", autouse=True)
def managed_test_scratch(tmp_path_factory):
    """Let pytest retain failed scratch and discard successful-session scratch."""
    global _SESSION_SCRATCH
    session_temp = tmp_path_factory.getbasetemp()
    _SESSION_SCRATCH = session_temp
    previous = {key: os.environ.get(key) for key in ("TEMP", "TMP")}
    previous_tempdir = tempfile.tempdir
    os.environ["TEMP"] = os.environ["TMP"] = str(session_temp)
    tempfile.tempdir = str(session_temp)
    try:
        yield
    finally:
        tempfile.tempdir = previous_tempdir
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    """Only a wholly successful session may discard its owned scratch directory."""
    if exitstatus != 0 or _SESSION_SCRATCH is None:
        return
    scratch = _SESSION_SCRATCH.resolve()
    if scratch != _SESSION_SCRATCH.absolute():
        return
    if scratch == PYTEST_TEMP_ROOT.resolve() or not scratch.is_relative_to(
        PYTEST_TEMP_ROOT.resolve()
    ):
        return
    try:
        shutil.rmtree(scratch)
    except OSError as exc:
        warnings.warn(
            pytest.PytestWarning(f"Test scratch retained at {scratch}: {exc}"), stacklevel=1
        )


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def test_engine():
    """Create test database engine"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.connect() as conn:
        await conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        await conn.run_sync(Base.metadata.drop_all)
        await conn.commit()
        await conn.exec_driver_sql("PRAGMA foreign_keys=ON")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.connect() as conn:
        await conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        await conn.run_sync(Base.metadata.drop_all)
        await conn.commit()

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for tests"""
    async_session = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Create test client"""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_ingredient():
    """Sample ingredient data"""
    return {
        "name": "Linalool",
        "cas_number": "78-70-6",
        "odor_description": "floral, woody, lavender",
        "volatility": "top-heart",
        "ifra_max_level": 100.0,
        "allergen": True,
    }


@pytest.fixture
def sample_formula():
    """Sample formula data"""
    return {
        "name": "Test Eau de Parfum",
        "version": "1.0",
        "concentration_percent": 15.0,
        "ingredients": [
            {"name": "Linalool", "percentage": 10.0, "role": "heart", "volatility": "top-heart"},
            {"name": "Iso E Super", "percentage": 8.0, "role": "base", "volatility": "base"},
            {"name": "Ethanol", "percentage": 80.0, "role": "solvent", "volatility": "top"},
            {"name": "Water", "percentage": 2.0, "role": "solvent", "volatility": "top"},
        ],
    }
