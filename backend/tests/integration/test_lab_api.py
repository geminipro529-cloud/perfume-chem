import pytest


@pytest.mark.asyncio
async def test_lab_api_runs_material_bottle_formula_and_experiment_workflow(client):
    material_response = await client.post(
        "/api/v1/lab/materials",
        json={"canonical_name": "API Iris Material"},
    )
    assert material_response.status_code == 201
    material_id = material_response.json()["id"]

    stock_response = await client.post(
        "/api/v1/lab/stocks",
        json={
            "material_id": material_id,
            "active_fraction": 0.3,
            "fraction_basis": "mass_fraction",
            "initial_mass_g": 5.0,
            "density_g_ml": 0.98,
        },
    )
    assert stock_response.status_code == 201
    stock_id = stock_response.json()["id"]

    bottle_response = await client.post(
        "/api/v1/lab/bottles",
        json={"label": "API trial", "initial_mass_g": 1.0},
    )
    assert bottle_response.status_code == 201
    bottle_id = bottle_response.json()["id"]
    addition_response = await client.post(
        f"/api/v1/lab/bottles/{bottle_id}/additions",
        json={
            "stock_solution_id": stock_id,
            "mass_g": 0.5,
            "expected_sequence": 1,
            "command_id": "api-addition-1",
        },
    )
    assert addition_response.status_code == 201
    state_response = await client.get(f"/api/v1/lab/bottles/{bottle_id}")
    assert state_response.status_code == 200
    assert state_response.json()["stream_sequence"] == 2
    assert state_response.json()["total_mass_g"] == 1.5

    formula_response = await client.post(
        "/api/v1/lab/formulas", json={"name": "API Iris Cathedral"}
    )
    formula_id = formula_response.json()["id"]
    version_response = await client.post(
        f"/api/v1/lab/formulas/{formula_id}/versions",
        json={
            "brief": {"identity": "iris and incense"},
            "constraints": {"must_preserve": ["iris"]},
            "concentration_fraction": 0.2,
            "concentration_basis": "mass_fraction",
        },
    )
    assert version_response.status_code == 201
    assert version_response.json()["version_number"] == 1

    experiment_response = await client.post(
        "/api/v1/lab/experiments",
        json={"name": "API wear trial", "protocol": {"times_s": [0, 1800]}},
    )
    experiment_id = experiment_response.json()["id"]
    sample_response = await client.post(
        f"/api/v1/lab/experiments/{experiment_id}/samples",
        json={"bottle_id": bottle_id, "blind_code": "Q4"},
    )
    sample_id = sample_response.json()["id"]
    application_response = await client.post(
        "/api/v1/lab/applications",
        json={
            "sample_id": sample_id,
            "applied_at": "2026-07-16T08:00:00Z",
            "dose": {"mass_mg": 20.0},
            "context": {"substrate": "blotter"},
        },
    )
    application_id = application_response.json()["id"]
    observation_response = await client.post(
        f"/api/v1/lab/applications/{application_id}/observations",
        json={"elapsed_seconds": 1800, "observations": {"iris_intensity": 7}},
    )
    assert observation_response.status_code == 201

    dashboard = await client.get("/api/v1/lab/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["counts"]["materials"] >= 1
    assert dashboard.json()["counts"]["bottles"] >= 1
    assert dashboard.json()["counts"]["experiments"] >= 1

    exported = await client.get("/api/v1/lab/export")
    assert exported.status_code == 200
    assert exported.json()["format_revision"] == "lab-export-v1"
    imported = await client.post("/api/v1/lab/import", json=exported.json())
    assert imported.status_code == 200
    assert imported.json()["inserted"] == 0
    assert imported.json()["skipped"] > 0


@pytest.mark.asyncio
async def test_lab_api_exposes_analysis_interventions_and_stable_assistant(client):
    analysis = await client.post(
        "/api/v1/lab/analysis",
        json={
            "name": "API analysis",
            "total_volume_ml": 10.0,
            "concentration_percent": 20.0,
            "ingredients": [
                {
                    "name": "Hedione",
                    "percentage": 100.0,
                    "stock_active_fraction": 1.0,
                    "stock_fraction_basis": "volume_fraction",
                }
            ],
        },
    )
    assert analysis.status_code == 200
    assert analysis.json()["analysis_engine"] == "engine.workbench.PerfumeWorkbench"

    interventions = await client.post(
        "/api/v1/lab/interventions",
        json={
            "batch_mass_g": 10.0,
            "brief": {
                "name": "Iris Cathedral",
                "required_character_tags": ["iris", "incense"],
                "maximum_active_addition_ppm_w_w": 500.0,
            },
            "inventory": [
                {
                    "material": "Alpha Irone",
                    "available_stock_mass_mg": 100.0,
                    "active_mass_fraction": 0.1,
                    "minimum_measurable_stock_mass_mg": 1.0,
                    "dispensing_increment_mg": 1.0,
                }
            ],
            "candidates": [
                {
                    "material": "Alpha Irone",
                    "requested_active_ppm_w_w": 100.0,
                    "predicted_oav_delta": 10.0,
                    "desired_effects": {"iris": 1.0},
                    "preserved_character_tags": ["iris", "incense"],
                    "safety_status": "pass",
                }
            ],
        },
    )
    assert interventions.status_code == 200
    assert interventions.json()["ranked"][0]["material"] == "Alpha Irone"
    assert interventions.json()["evidence"]["classification"] == "HEURISTIC"

    request = {
        "intent": "bottle_status",
        "subject_id": "stable-bottle",
        "facts": {"total_mass_g": 1.2},
    }
    first = await client.post("/api/v1/lab/assistant", json=request)
    second = await client.post("/api/v1/lab/assistant", json=request)
    assert first.status_code == 200
    assert first.json() == second.json()
    assert len(first.json()["payload_sha256"]) == 64
