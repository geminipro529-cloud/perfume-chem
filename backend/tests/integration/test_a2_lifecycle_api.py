from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from app.models.lab_science import LabClaimAssessmentVersion
from app.services.lab_service import LabService
from tests.a2_planning_fixtures import _approved_plan
from tests.unit.test_a2_science_service import (
    _evidence,
    _formula_version,
    _method_input,
)


@pytest.mark.asyncio
async def test_versioned_execution_api_exposes_confirm_measure_commit_replay_diff(
    client,
    db_session,
):
    service, approved, line, stock = await _approved_plan(db_session)
    reservation = await service.reserve_inventory(
        build_plan_version_id=approved.id,
        build_plan_line_id=line.id,
        stock_solution_id=stock.id,
        reserved_mass_g=1.0,
        idempotency_key="api-execution-reservation",
        actor="planner",
        rationale="Reserve approved API line",
    )
    bottle = await service.create_bottle("A2 API execution")

    proposed = await client.post(
        "/api/v1/lab/v2/actions",
        json={
            "schema_version": "a2-bottle-action-v1",
            "reservation_id": reservation.reservation_id,
            "bottle_id": bottle.id,
            "action_type": "ADD_STOCK",
            "planned_mass_g": 1.0,
            "expected_sequence": 1,
            "idempotency_key": "api-execution-proposal",
            "actor": "operator",
            "rationale": "Execute approved API line",
        },
    )
    assert proposed.status_code == 201
    proposal = proposed.json()
    assert proposal["stock_solution_id"] == stock.id

    premature = await client.post(
        f"/api/v1/lab/v2/actions/{proposal['id']}/commit",
        json={"actor": "operator", "rationale": "Premature"},
    )
    assert premature.status_code == 409
    assert premature.json()["error"]["code"] == "ACTION_NOT_CONFIRMED"

    confirmed = await client.post(
        f"/api/v1/lab/v2/actions/{proposal['id']}/confirmations",
        json={
            "decision": "CONFIRMED",
            "confirmer_pseudonym": "human-operator-api",
            "confirmed_at": "2026-07-30T03:00:00Z",
            "rationale": "Physical setup verified",
        },
    )
    assert confirmed.status_code == 201
    assert confirmed.json()["decision"] == "CONFIRMED"

    measured = await client.post(
        f"/api/v1/lab/v2/actions/{proposal['id']}/measurements",
        json={
            "quantity_kind": "mass",
            "value": 1.0,
            "unit": "g",
            "standard_uncertainty": 0.002,
            "method": "gravimetric",
            "measured_at": "2026-07-30T03:01:00Z",
            "actor": "human-operator-api",
        },
    )
    assert measured.status_code == 201
    assert measured.json()["value"] == pytest.approx(1.0)

    committed = await client.post(
        f"/api/v1/lab/v2/actions/{proposal['id']}/commit",
        json={
            "actor": "operator",
            "rationale": "Confirmed gravimetric API addition",
        },
    )
    assert committed.status_code == 201
    assert committed.json()["state_diff"]["total_mass_delta_g"] == pytest.approx(
        1.0
    )

    replay = await client.get(
        f"/api/v1/lab/v2/bottles/{bottle.id}/replay"
    )
    assert replay.status_code == 200
    assert replay.json()["stream_sequence"] == 2
    assert replay.json()["total_mass_g"] == pytest.approx(1.0)

    diff = await client.get(
        f"/api/v1/lab/v2/actions/{proposal['id']}/diff"
    )
    assert diff.status_code == 200
    assert diff.json() == committed.json()["state_diff"]


@pytest.mark.asyncio
async def test_versioned_science_api_retires_caller_controlled_release_review(
    client,
    db_session,
):
    service = LabService(db_session)
    evidence = await _evidence(service, "api-science")
    formula_version = await _formula_version(service)
    method = await service.create_analytical_method_version(
        _method_input(evidence.id)
    )
    bottle = await service.create_bottle("A2 science API bottle")
    experiment = await service.create_experiment(
        "A2 science API sensory",
        protocol={"blind": True},
    )
    sample = await service.add_experiment_sample(
        experiment_id=experiment.id,
        bottle_id=bottle.id,
        blind_code="API-001",
    )
    application = await service.record_application(
        sample_id=sample.id,
        applied_at=datetime(2026, 7, 30, 4, 0, tzinfo=timezone.utc),
        dose={"mass_mg": 1.0},
        context={"substrate": "blotter"},
    )

    analytical = await client.post(
        "/api/v1/lab/v2/analytical-results",
        json={
            "method_version_id": method.id,
            "run_kind": "GCMS",
            "status": "QC_ACCEPTED",
            "instrument_identifier": "instrument:pseudonymous-api",
            "acquired_at": "2026-07-30T04:01:00Z",
            "parameters": {"injection": "split"},
            "deviations": [],
            "processing_version": "processor-v1",
            "formula_version_id": formula_version.id,
        },
    )
    assert analytical.status_code == 201
    assert analytical.json()["formula_version_id"] == formula_version.id

    sensory = await client.post(
        "/api/v1/lab/v2/sensory-results",
        json={
            "application_id": application.id,
            "elapsed_seconds": 60.0,
            "observations": {
                "descriptor": "floral",
                "intensity": 0.6,
            },
        },
    )
    assert sensory.status_code == 201
    assert sensory.json()["application_id"] == application.id

    regulatory = await client.post(
        "/api/v1/lab/v2/regulatory-assessments",
        json={
            "schema_version": "a2-regulatory-v1",
            "subject_type": "FORMULA_VERSION",
            "subject_id": formula_version.id,
            "standard_identifier": "test-standard",
            "standard_amendment": "2026-01",
            "standard_state": "CURRENT",
            "source_evidence_record_id": evidence.id,
            "jurisdiction": "TEST",
            "product_category": "fine-fragrance",
            "concentration_basis": "mass_fraction",
            "finished_product_concentration": 0.2,
            "effective_date": "2026-01-01",
            "evaluated_at": "2026-07-30T04:02:00Z",
            "result_state": "PASS",
            "assumptions": [],
            "unresolved": [],
            "permitted_wording": "Passes the named test standard state",
        },
    )
    assert regulatory.status_code == 201
    assert regulatory.json()["result_state"] == "PASS"

    before = await db_session.scalar(
        select(func.count()).select_from(LabClaimAssessmentVersion)
    )
    review = await client.post(
        "/api/v1/lab/v2/release-reviews",
        json={
            "schema_version": "a2-release-review-v1",
            "claim_type": "RELEASE_REVIEW",
            "subject_type": "FORMULA_VERSION",
            "subject_id": formula_version.id,
            "policy_version": "policy-v1",
            "decision": "ADVISORY_ONLY",
            "authority": {"scope": "software-fixture"},
            "missing_evidence": ["held-out sensory validation"],
            "conflicts": [],
            "permitted_wording": "Software workflow verified only",
            "forbidden_wording": "Scientifically released",
            "human_review_state": "PENDING",
            "reviewer_pseudonym": None,
            "reviewed_at": None,
            "evidence_links": [
                {
                    "evidence_record_id": evidence.id,
                    "role": "SUPPORTING",
                }
            ],
        },
    )
    assert review.status_code == 410
    assert review.json()["error"]["code"] == (
        "LEGACY_RELEASE_REVIEW_AUTHORITY_RETIRED"
    )
    after = await db_session.scalar(
        select(func.count()).select_from(LabClaimAssessmentVersion)
    )
    assert after == before
