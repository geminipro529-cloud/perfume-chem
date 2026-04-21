"""Test configuration and fixtures"""

import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.base import Base
from app.api.deps import get_db

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_perfume_chem.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for tests"""
    async_session = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Create test client"""
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as client:
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
        "allergen": True
    }


@pytest.fixture
def sample_formula():
    """Sample formula data"""
    return {
        "name": "Test Eau de Parfum",
        "version": "1.0",
        "concentration_percent": 15.0,
        "ingredients": [
            {
                "name": "Linalool",
                "percentage": 10.0,
                "role": "heart",
                "volatility": "top-heart"
            },
            {
                "name": "Iso E Super",
                "percentage": 8.0,
                "role": "base",
                "volatility": "base"
            },
            {
                "name": "Ethanol",
                "percentage": 80.0,
                "role": "solvent",
                "volatility": "top"
            },
            {
                "name": "Water",
                "percentage": 2.0,
                "role": "solvent",
                "volatility": "top"
            }
        ]
    }
