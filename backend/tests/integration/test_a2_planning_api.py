import pytest

from app.services.lab_service import LabService


async def _api_authority_fixture(db_session):
    service = LabService(db_session)
    evidence = await service.record_evidence(
        claim_key="api:a2-planning",
        classification="EXACT",
        source_locator="test://api-a2-planning",
        source_version="1",
        method="bounded API fixture",
        assumptions=(),
        limitations=(),
        payload_sha256=None,
    )
    material = await service.create_material("API Jasmine Absolute")
    stock = await service.create_stock_solution(
        material_id=material.id,
        active_fraction=0.1,
        fraction_basis="mass_fraction",
        initial_mass_g=10.0,
        density_g_ml=1.0,
    )
    formula = await service.create_formula("API A2 lineage")
    parent = await service.add_formula_version(
        formula.id,
        brief={"name": "parent"},
        constraints={},
        components=(),
    )
    child = await service.add_formula_version(
        formula.id,
        brief={"name": "child"},
        constraints={},
        components=(),
    )
    return evidence, stock, parent, child


def _target_payload(evidence_id: str) -> dict:
    return {
        "product_key": "reference:api-jasmine",
        "schema_version": "a2-target-v1",
        "author": "Sol",
        "provenance_activity": {"activity": "api-test"},
        "uncertainty_summary": {"basis": "bounded-test"},
        "rationale": "API documentary target",
        "lines": [
            {
                "line_id": "api-target-line-jasmine",
                "target_identity": "API Jasmine Absolute",
                "source_name": "API reference",
                "grade": "absolute",
                "presence_probability": 0.95,
                "target_raw_quantity": 1.0,
                "target_active_quantity": 0.1,
                "unit": "g",
                "concentration_fraction": 0.1,
                "concentration_basis": "mass_fraction",
                "functional_roles": ["heart", "diffusion"],
                "evidence_links": [evidence_id],
                "uncertainty": {"standard_uncertainty_g": 0.01},
            }
        ],
    }


@pytest.mark.asyncio
async def test_a2_planning_api_exposes_thin_versioned_workflow(
    client,
    db_session,
):
    evidence, stock, parent, child = await _api_authority_fixture(db_session)

    target_response = await client.post(
        "/api/v1/lab/v2/targets",
        json=_target_payload(evidence.id),
    )
    assert target_response.status_code == 201
    target = target_response.json()
    assert target["version_number"] == 1
    assert len(target["content_sha256"]) == 64
    target_line = target["lines"][0]

    target_get = await client.get(
        f"/api/v1/lab/v2/targets/{target['id']}"
    )
    assert target_get.status_code == 200
    assert target_get.json() == target

    acceptance_response = await client.post(
        f"/api/v1/lab/v2/targets/{target['id']}/accept",
        json={
            "reviewer": "Sol",
            "rationale": "API evidence gate passed",
        },
    )
    assert acceptance_response.status_code == 201
    acceptance = acceptance_response.json()
    assert acceptance["target_hypothesis_version_id"] == target["id"]

    lineage_response = await client.post(
        f"/api/v1/lab/v2/formula-versions/{child.id}/parents",
        json={
            "parent_version_id": parent.id,
            "relationship_kind": "DERIVED_FROM",
            "change": {"kind": "REBALANCE"},
            "rationale": "API immutable revision",
        },
    )
    assert lineage_response.status_code == 201
    assert lineage_response.json()["parent_version_id"] == parent.id

    mapping_response = await client.post(
        "/api/v1/lab/v2/inventory-mappings",
        json={
            "target_line_id": target_line["id"],
            "stock_solution_id": stock.id,
            "target_identity": "API Jasmine Absolute",
            "build_identity": "API Jasmine Absolute",
            "identity_status": "EXACT",
            "inventory_status": "EXACT_LOT_AVAILABLE",
            "substitution_class": "EXACT",
            "preserved_functions": ["heart", "diffusion"],
            "lost_functions": [],
            "confidence": 1.0,
            "rationale": "Exact API lot",
            "evidence_links": [evidence.id],
        },
    )
    assert mapping_response.status_code == 201
    mapping = mapping_response.json()

    plan_response = await client.post(
        "/api/v1/lab/v2/build-plans",
        json={
            "target_hypothesis_version_id": target["id"],
            "accepted_target_version_id": acceptance["id"],
            "schema_version": "a2-build-plan-v1",
            "author": "Sol",
            "inventory_snapshot_ref": "inventory-sha256:api-fixture",
            "uncertainty_summary": {"basis": "bounded-test"},
            "rationale": "Executable API plan",
            "lines": [
                {
                    "line_id": "api-build-line-jasmine",
                    "target_line_id": target_line["id"],
                    "target_identity": "API Jasmine Absolute",
                    "inventory_mapping_version_id": mapping["id"],
                    "stock_solution_id": stock.id,
                    "planned_raw_quantity": 1.0,
                    "planned_active_quantity": 0.1,
                    "unit": "g",
                    "concentration_fraction": 0.1,
                    "concentration_basis": "mass_fraction",
                    "density_g_ml": 1.0,
                    "density_source": "lot record",
                    "standard_uncertainty": 0.01,
                    "measurement_method": "gravimetric",
                    "resolution": 0.001,
                    "expected_transfer_loss": 0.01,
                    "substitution_class": "EXACT",
                    "preserved_functions": ["heart", "diffusion"],
                    "lost_functions": [],
                    "rationale": "Exact API lot",
                    "evidence_links": [evidence.id],
                }
            ],
        },
    )
    assert plan_response.status_code == 201
    draft = plan_response.json()
    assert draft["status"] == "DRAFT"

    invalid = await client.post(
        f"/api/v1/lab/v2/build-plans/{draft['id']}/transitions",
        json={
            "next_status": "APPROVED",
            "actor": "Sol",
            "rationale": "Invalid transition",
        },
    )
    assert invalid.status_code == 409
    assert invalid.json() == {
        "error": {
            "code": "INVALID_BUILD_PLAN_TRANSITION",
            "message": "Build plan cannot transition from DRAFT to APPROVED.",
        }
    }

    review_response = await client.post(
        f"/api/v1/lab/v2/build-plans/{draft['id']}/transitions",
        json={
            "next_status": "UNDER_REVIEW",
            "actor": "Sol",
            "rationale": "API review",
        },
    )
    assert review_response.status_code == 201
    review = review_response.json()
    approved_response = await client.post(
        f"/api/v1/lab/v2/build-plans/{review['id']}/transitions",
        json={
            "next_status": "APPROVED",
            "actor": "Sol",
            "rationale": "API approval",
        },
    )
    assert approved_response.status_code == 201
    approved = approved_response.json()
    approved_get = await client.get(
        f"/api/v1/lab/v2/build-plans/{approved['id']}"
    )
    assert approved_get.status_code == 200
    assert approved_get.json() == approved

    reservation_response = await client.post(
        "/api/v1/lab/v2/reservations",
        json={
            "build_plan_version_id": approved["id"],
            "build_plan_line_id": approved["lines"][0]["id"],
            "stock_solution_id": stock.id,
            "reserved_mass_g": 1.0,
            "idempotency_key": "api-reservation",
            "actor": "Sol",
            "rationale": "API approved build",
        },
    )
    assert reservation_response.status_code == 201
    reservation = reservation_response.json()
    assert reservation["state"] == "RESERVED"

    release_response = await client.post(
        "/api/v1/lab/v2/reservations/"
        f"{reservation['reservation_id']}/transitions",
        json={
            "next_state": "RELEASED",
            "idempotency_key": "api-reservation-release",
            "actor": "Sol",
            "rationale": "API build cancelled",
        },
    )
    assert release_response.status_code == 201
    assert release_response.json()["state"] == "RELEASED"


@pytest.mark.asyncio
async def test_a2_planning_api_returns_stable_not_found_and_strict_shape(
    client,
):
    missing = await client.get("/api/v1/lab/v2/targets/missing-target")
    assert missing.status_code == 404
    assert missing.json() == {
        "error": {
            "code": "TARGET_NOT_FOUND",
            "message": "Target version not found: missing-target.",
        }
    }

    invalid = await client.post(
        "/api/v1/lab/v2/targets",
        json={
            **_target_payload("missing-evidence"),
            "unexpected_authority": True,
        },
    )
    assert invalid.status_code == 422
