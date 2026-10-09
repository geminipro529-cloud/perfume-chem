"""Integration tests for API endpoints"""

import json
from pathlib import Path

import pytest
from httpx import AsyncClient

PROJECT_ROOT = Path(__file__).resolve().parents[3]
GOLDEN_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "golden_formula_cases.json"


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
async def test_golden_explicit_solvent_case_exercises_api_adapter(client: AsyncClient):
    fixture = json.loads(GOLDEN_FIXTURE.read_text(encoding="utf-8"))
    case = next(case for case in fixture["api_cases"] if case["id"] == "explicit_solvent")

    response = await client.post(
        "/api/v1/formulas/analyze-formula", json=case["request"]
    )

    assert response.status_code == 200
    data = response.json()
    assert data["formula_state"]["total_raw_ul"] == pytest.approx(
        case["expected_total_raw_ul"]
    )
    assert [row["name"] for row in data["material_oav_table"]] == case[
        "expected_aromatic_materials"
    ]
    assert any("finished-product" in item for item in data["assumptions"])
    assert data["mixture_state"]["matrix_supplied"] is True
    assert data["mixture_state"]["complete"] is True  # Hedione and Iso E Super now have sourced densities
    assert data["mixture_state"]["matrix_moles"] > 0
    assert data["formula_state"]["matrix_source"] == "explicit"
    assert not any("solvent rows are excluded" in item for item in data["assumptions"])


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
                "standard_uncertainty_ul": 1.0,
                "systematic_standard_uncertainty_ul": 0.5,
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["exact_stock_mass_g"] == pytest.approx(0.30612244898)
    assert data["rounded_stock_volume_ul"] == 305.0
    assert data["staged_additions_ul"] == [155.0, 150.0]
    assert data["pipette_standard_uncertainty_ul"] == pytest.approx(3**0.5)
    assert data["resulting_active_mass_fraction_standard_uncertainty"] > 0
    assert data["evidence"]["stock_mass_arithmetic"]["classification"] == "EXACT"
    assert data["evidence"]["uncertainty_propagation"]["classification"] == (
        "LITERATURE_DERIVED"
    )


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


@pytest.mark.asyncio
async def test_mixer_legacy_sequence_exposes_non_authoritative_contract(
    client: AsyncClient,
):
    response = await client.post(
        "/api/v1/mixer/sequence",
        json={"ingredients": {"Hedione": 50.0, "Iso E Super": 50.0}},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["compounding_authority"] == "LEGACY_OLFACTIVE_PHASE_SUGGESTION"
    assert data["authority_blockers"] == [
        "RAW_UL_ROWS_AND_EXPLICIT_BASKET_ASSIGNMENTS_REQUIRED"
    ]
    assert data["ordering_contract"] == "LEGACY_NOTE_PHASE_CLP_MW"
    assert data["mixing_timing"]["optimized_rest_minutes"] == 0


@pytest.mark.asyncio
async def test_mixer_structured_sequence_preserves_physical_rows_and_receipt(
    client: AsyncClient,
):
    response = await client.post(
        "/api/v1/mixer/sequence",
        json={
            "name": "Basket API",
            "rows": [
                {
                    "row_id": "hedione-lot-a",
                    "material": "Hedione",
                    "physical_stock_label": "Hedione lot A neat",
                    "raw_ul": 100.0,
                    "basket": 7,
                    "operation": "DIRECT_ADD",
                },
                {
                    "row_id": "iso-e-lot-b",
                    "material": "Iso E Super",
                    "physical_stock_label": "Iso E Super lot B neat",
                    "raw_ul": 200.0,
                    "basket": 3,
                    "operation": "DIRECT_ADD",
                },
            ],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["compounding_authority"] == "WITHHELD"
    assert (
        "VERIFIED_PHYSICAL_AUTHORITY_RECEIPTS_REQUIRED"
        in data["authority_blockers"]
    )
    assert [step["row_id"] for step in data["steps"]] == [
        "iso-e-lot-b",
        "hedione-lot-a",
    ]
    assert data["steps"][0]["physical_stock_label"] == "Iso E Super lot B neat"
    assert data["steps"][0]["raw_ul"] == 200.0
    assert data["raw_total_ul"] == data["ordered_raw_total_ul"] == 300.0
    assert len(data["basket_checkpoints"]) == 17
    assert data["elapsed_time_scope"]["automatic_phase_rest_minutes"] == 0


@pytest.mark.asyncio
async def test_mixer_structured_instructions_expose_raw_ul_and_authority(
    client: AsyncClient,
):
    response = await client.post(
        "/api/v1/mixer/instructions",
        json={
            "name": "Prepared trace",
            "rows": [
                {
                    "row_id": "trace-row",
                    "material": "Hedione",
                    "physical_stock_label": "Hedione trace dilution lot A",
                    "prepared_dilution_id": "PD-HED-001",
                    "raw_ul": 5.0,
                    "basket": 7,
                    "operation": "DIRECT_ADD",
                }
            ],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["compounding_authority"] == "WITHHELD"
    assert (
        "VERIFIED_PHYSICAL_AUTHORITY_RECEIPTS_REQUIRED"
        in data["authority_blockers"]
    )
    assert data["total_pct"] is None
    assert data["raw_total_ul"] == data["ordered_raw_total_ul"] == 5.0
    assert "5 µL raw stock" in data["full_text"]
    assert "PD-HED-001" in data["full_text"]
    assert data["full_text"].count("Final concentrate homogenization") == 1


@pytest.mark.asyncio
async def test_mixer_missing_basket_returns_withheld_not_inferred(client: AsyncClient):
    response = await client.post(
        "/api/v1/mixer/sequence",
        json={
            "rows": [
                {
                    "row_id": "unassigned",
                    "material": "Hedione",
                    "raw_ul": 100.0,
                    "basket": None,
                    "operation": "DIRECT_ADD",
                }
            ]
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["compounding_authority"] == "WITHHELD"
    assert data["authority_blockers"] == [
        "VERIFIED_PHYSICAL_AUTHORITY_RECEIPTS_REQUIRED",
        "UNASSIGNED_BASKET:unassigned",
    ]
    assert data["raw_total_ul"] == data["ordered_raw_total_ul"] == 100.0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"ingredients": {"Hedione": 100.0}, "rows": [
            {"row_id": "one", "material": "Hedione", "raw_ul": 100.0, "basket": 7}
        ]},
        {"rows": [
            {"row_id": "dup", "material": "Hedione", "raw_ul": 50.0, "basket": 7},
            {"row_id": "dup", "material": "Iso E Super", "raw_ul": 50.0, "basket": 3},
        ]},
        {"rows": [
            {"row_id": "bad", "material": "Hedione", "raw_ul": 100.0, "basket": 18}
        ]},
        {"rows": [
            {"row_id": "bad", "material": "Hedione", "raw_ul": 0.0, "basket": 7}
        ]},
        {"rows": [
            {
                "row_id": "bad",
                "material": "Hedione",
                "raw_ul": 100.0,
                "basket": 7,
                "operation": "MAYBE",
            }
        ]},
    ],
)
async def test_mixer_rejects_malformed_input_contract(
    client: AsyncClient,
    payload: dict,
):
    response = await client.post("/api/v1/mixer/sequence", json=payload)

    assert response.status_code == 422
