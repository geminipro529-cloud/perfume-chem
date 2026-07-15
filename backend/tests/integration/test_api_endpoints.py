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
async def test_analyze_formula_uses_canonical_workbench(client: AsyncClient, sample_formula):
    response = await client.post("/api/v1/formulas/analyze-formula", json=sample_formula)
    assert response.status_code == 200

    data = response.json()
    assert data["analysis_engine"] == "engine.workbench.PerfumeWorkbench"
    assert data["formula_state"]["batch_volume_ml"] == 100.0
    assert data["formula_state"]["total_raw_ul"] == 18000.0
    assert len(data["material_oav_table"]) == 2
    assert data["evidence"]["headspace"]["classification"] == "HEURISTIC"
    assert data["estimated_longevity_hours"] is None
    assert data["estimated_sillage"] is None
    assert any("finished-product" in item for item in data["assumptions"])


@pytest.mark.asyncio
async def test_analyze_formula_uses_concentrate_basis_without_solvent_rows(
    client: AsyncClient,
):
    response = await client.post(
        "/api/v1/formulas/analyze-formula",
        json={
            "name": "Concentrate basis",
            "total_volume_ml": 50.0,
            "concentration_percent": 20.0,
            "ingredients": [
                {"name": "Hedione", "percentage": 60.0},
                {"name": "Iso E Super", "percentage": 40.0},
            ],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["formula_state"]["batch_volume_ml"] == 50.0
    assert data["formula_state"]["total_raw_ul"] == 10000.0
    assert any("concentrate composition" in item for item in data["assumptions"])


@pytest.mark.asyncio
async def test_calculate_addition_returns_exact_mass_and_pipette_plan(client: AsyncClient):
    response = await client.post(
        "/api/v1/formulas/calculate-addition",
        json={
            "bottle": {
                "total_mass_g": 30.0,
                "active_material_mass_g": 0.03,
            },
            "stock": {
                "active_mass_fraction": 0.10,
                "density_g_ml": 1.0,
            },
            "target_active_mass_fraction": 0.002,
            "pipette": {
                "minimum_ul": 10.0,
                "increment_ul": 5.0,
                "maximum_single_step_ul": 200.0,
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["exact_stock_mass_g"] == pytest.approx(0.30612244898)
    assert data["rounded_stock_volume_ul"] == 305.0
    assert data["staged_additions_ul"] == [155.0, 150.0]
    assert data["evidence"]["classification"] == "EXACT"


@pytest.mark.asyncio
async def test_calculate_addition_rejects_target_below_current_fraction(client: AsyncClient):
    response = await client.post(
        "/api/v1/formulas/calculate-addition",
        json={
            "bottle": {
                "total_mass_g": 10.0,
                "active_material_mass_g": 0.2,
            },
            "stock": {
                "active_mass_fraction": 0.10,
                "density_g_ml": 1.0,
            },
            "target_active_mass_fraction": 0.01,
        },
    )

    assert response.status_code == 400
    assert "below current" in response.json()["detail"]
