"""Integration tests for API endpoints"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test root endpoint"""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check endpoint"""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_calculate_dilution(client: AsyncClient):
    """Test dilution calculation endpoint"""
    payload = {
        "concentrate_volume": 10.0,
        "concentrate_percent": 100.0,
        "target_percent": 10.0,
        "solvent": "ethanol"
    }
    
    response = await client.post("/api/v1/formulas/calculate-dilution", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["total_volume"] == 100.0
    assert data["solvent_to_add"] == 90.0


@pytest.mark.asyncio
async def test_drops_to_ml(client: AsyncClient):
    """Test drops to ml conversion"""
    response = await client.get("/api/v1/formulas/drops-to-ml/20")
    assert response.status_code == 200
    
    data = response.json()
    assert data["drops"] == 20
    assert data["milliliters"] == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_analyze_formula(client: AsyncClient, sample_formula):
    """Test formula analysis endpoint"""
    response = await client.post("/api/v1/formulas/analyze-formula", json=sample_formula)
    assert response.status_code == 200
    
    data = response.json()
    assert "note_distribution" in data
    assert "estimated_longevity_hours" in data
    assert "estimated_sillage" in data
