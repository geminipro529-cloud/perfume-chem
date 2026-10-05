"""A committed evolving-bottle delta accepts one replay-safe personal reaction."""

from __future__ import annotations

import pytest

from tests.a2_planning_fixtures import _approved_plan


@pytest.mark.asyncio
async def test_evolving_bottle_evaluation_is_linked_idempotent_and_noncausal(
    client,
    db_session,
) -> None:
    service, approved, line, stock = await _approved_plan(db_session)
    reservation = await service.reserve_inventory(
        build_plan_version_id=approved.id,
        build_plan_line_id=line.id,
        stock_solution_id=stock.id,
        reserved_mass_g=1.0,
        idempotency_key="evaluation-reservation",
        actor="personal-research-user",
        rationale="Reserve one evolving-bottle delta",
    )
    bottle = await service.create_bottle("Evolving bottle evaluation")
    proposed = await client.post(
        "/api/v1/lab/v2/actions",
        json={
            "schema_version": "evolving-bottle-action-v1",
            "reservation_id": reservation.reservation_id,
            "bottle_id": bottle.id,
            "action_type": "ADD_STOCK",
            "planned_mass_g": 1.0,
            "expected_sequence": 1,
            "idempotency_key": "evaluation-proposal",
            "actor": "personal-research-user",
            "rationale": "One small additive delta",
        },
    )
    assert proposed.status_code == 201
    proposal_id = proposed.json()["id"]
    confirmed = await client.post(
        f"/api/v1/lab/v2/actions/{proposal_id}/confirmations",
        json={
            "decision": "CONFIRMED",
            "confirmer_pseudonym": "personal-research-user",
            "confirmed_at": "2026-09-28T12:00:00+07:00",
            "rationale": "I chose this delta",
        },
    )
    assert confirmed.status_code == 201
    measured = await client.post(
        f"/api/v1/lab/v2/actions/{proposal_id}/measurements",
        json={
            "quantity_kind": "mass",
            "value": 1.0,
            "unit": "g",
            "standard_uncertainty": None,
            "method": "personal explicit measurement",
            "measured_at": "2026-09-28T12:01:00+07:00",
            "actor": "personal-research-user",
        },
    )
    assert measured.status_code == 201
    committed = await client.post(
        f"/api/v1/lab/v2/actions/{proposal_id}/commit",
        json={
            "actor": "personal-research-user",
            "rationale": "Actual amount confirmed",
        },
    )
    assert committed.status_code == 201

    request = {
        "schema_version": "evolving-bottle-evaluation-v1",
        "bottle_id": bottle.id,
        "expected_sequence": 2,
        "command_id": "evaluation-after-1800-seconds",
        "actor": "personal-research-user",
        "evaluated_at": "2026-09-28T12:31:00+07:00",
        "waited_seconds": 1800,
        "reaction": "Lavender is clearer; the dry amber remains.",
        "decision": "CONTINUE",
    }
    first = await client.post(
        f"/api/v1/lab/v2/actions/{proposal_id}/evaluations",
        json=request,
    )
    assert first.status_code == 201
    result = first.json()
    assert result["event_type"] == "EVALUATE"
    assert result["action_commit_id"] == committed.json()["id"]
    assert result["addition_bottle_event_id"] == committed.json()["bottle_event_id"]
    assert result["evidence_scope"] == "SEQUENTIAL_PERSONAL_OBSERVATION"
    assert result["controlled_causal_evidence"] is False
    assert result["population_generalization_authorized"] is False
    assert result["release_authority"] is False
    assert result["safety_authority"] is False
    assert result["compounding_authority"] is False
    assert result["evidence_admission_authorized"] is False

    replay = await client.post(
        f"/api/v1/lab/v2/actions/{proposal_id}/evaluations",
        json=request,
    )
    assert replay.status_code == 201
    assert replay.json()["id"] == result["id"]

    bottle_replay = await client.get(
        f"/api/v1/lab/v2/bottles/{bottle.id}/replay"
    )
    assert bottle_replay.status_code == 200
    assert bottle_replay.json()["stream_sequence"] == 3
    assert bottle_replay.json()["total_mass_g"] == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_quick_personal_delta_reaction_is_exactly_linked_and_replay_safe(
    client,
) -> None:
    material = await client.post(
        "/api/v1/lab/materials",
        json={"canonical_name": "Quick Workbench Lavender"},
    )
    assert material.status_code == 201
    stock = await client.post(
        "/api/v1/lab/stocks",
        json={
            "material_id": material.json()["id"],
            "active_fraction": 1.0,
            "fraction_basis": "mass_fraction",
            "initial_mass_g": 5.0,
            "density_g_ml": 0.9,
        },
    )
    assert stock.status_code == 201
    bottle = await client.post(
        "/api/v1/lab/bottles",
        json={"label": "Quick evolving bottle", "initial_mass_g": 0},
    )
    assert bottle.status_code == 201

    analysis_sha256 = "a" * 64
    addition = await client.post(
        f"/api/v1/lab/bottles/{bottle.json()['id']}/additions",
        json={
            "stock_solution_id": stock.json()["id"],
            "mass_g": "0.075",
            "measured_volume_ul": "83.333333",
            "volume_measurement_method": "user_recorded_transfer",
            "expected_sequence": 1,
            "command_id": "quick-workbench-addition",
            "actor": "personal-workbench",
            "role": "material",
            "goal_analysis_sha256": analysis_sha256,
            "hypothesis_id": "direct-lavender",
            "hypothesis_variant": "low_variant",
        },
    )
    assert addition.status_code == 201
    assert addition.json()["execution_scope"] == "FREEFORM_UNBOUND_QUARANTINE"

    request = {
        "schema_version": "quick-bottle-evaluation-v1",
        "addition_event_ids": [addition.json()["id"]],
        "goal_analysis_sha256": analysis_sha256,
        "hypothesis_id": "direct-lavender",
        "hypothesis_variant": "low_variant",
        "expected_sequence": 2,
        "command_id": "quick-workbench-reaction",
        "actor": "personal-workbench",
        "evaluated_at": "2026-09-28T12:30:00+07:00",
        "waited_seconds": 1800,
        "reaction": "Lavender is clearer and the dry amber remains.",
        "decision": "CONTINUE",
    }
    recorded = await client.post(
        f"/api/v1/lab/v2/bottles/{bottle.json()['id']}/quick-evaluations",
        json=request,
    )
    assert recorded.status_code == 201
    result = recorded.json()
    assert result["event_type"] == "EVALUATE_PERSONAL_DELTA"
    assert result["addition_event_ids"] == [addition.json()["id"]]
    assert result["goal_analysis_sha256"] == analysis_sha256
    assert result["evidence_scope"] == "SEQUENTIAL_PERSONAL_OBSERVATION"
    assert result["controlled_causal_evidence"] is False
    assert result["population_generalization_authorized"] is False
    assert result["release_authority"] is False
    assert result["safety_authority"] is False
    assert result["compounding_authority"] is False
    assert result["evidence_admission_authorized"] is False

    replay = await client.post(
        f"/api/v1/lab/v2/bottles/{bottle.json()['id']}/quick-evaluations",
        json=request,
    )
    assert replay.status_code == 201
    assert replay.json()["id"] == result["id"]

    bottle_state = await client.get(
        f"/api/v1/lab/v2/bottles/{bottle.json()['id']}/replay"
    )
    assert bottle_state.status_code == 200
    assert bottle_state.json()["stream_sequence"] == 3
    assert bottle_state.json()["total_mass_g"] == pytest.approx(0.075)
