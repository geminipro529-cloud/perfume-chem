from datetime import datetime, timezone

import pytest

from app.services.lab_execution import (
    BottleActionConfirmationInput,
    BottleActionMeasurementInput,
    BottleActionProposalInput,
    ExecutionConflictError,
)
from app.services.lab_service import InsufficientStockError
from tests.a2_planning_fixtures import _approved_plan


async def _reserved_action_fixture(db_session):
    service, approved, line, stock = await _approved_plan(db_session)
    reservation = await service.reserve_inventory(
        build_plan_version_id=approved.id,
        build_plan_line_id=line.id,
        stock_solution_id=stock.id,
        reserved_mass_g=1.0,
        idempotency_key="execution-reservation",
        actor="planner",
        rationale="Reserve the approved build line",
    )
    bottle = await service.create_bottle("A2 execution bottle")
    proposal = await service.propose_bottle_action(
        BottleActionProposalInput(
            schema_version="a2-bottle-action-v1",
            reservation_id=reservation.reservation_id,
            bottle_id=bottle.id,
            action_type="ADD_STOCK",
            planned_mass_g=1.0,
            expected_sequence=1,
            idempotency_key="execution-proposal",
            actor="operator",
            rationale="Execute the reserved line",
        )
    )
    return service, reservation, bottle, proposal, stock


@pytest.mark.asyncio
async def test_confirmed_measured_action_commits_atomically_and_replays(
    db_session,
):
    service, reservation, bottle, proposal, stock = (
        await _reserved_action_fixture(db_session)
    )

    with pytest.raises(ExecutionConflictError) as unconfirmed:
        await service.commit_bottle_action(
            proposal.id,
            actor="operator",
            rationale="Premature commit",
        )
    assert unconfirmed.value.code == "ACTION_NOT_CONFIRMED"

    confirmation = await service.confirm_bottle_action(
        proposal.id,
        BottleActionConfirmationInput(
            decision="CONFIRMED",
            confirmer_pseudonym="human-operator-1",
            confirmed_at=datetime(2026, 7, 30, 3, 0, tzinfo=timezone.utc),
            rationale="Bottle, stock, and balance verified",
        ),
    )
    assert confirmation.decision == "CONFIRMED"

    with pytest.raises(ExecutionConflictError) as unmeasured:
        await service.commit_bottle_action(
            proposal.id,
            actor="operator",
            rationale="Still premature",
        )
    assert unmeasured.value.code == "ACTION_MEASUREMENT_REQUIRED"

    measurement = await service.record_bottle_action_measurement(
        proposal.id,
        BottleActionMeasurementInput(
            quantity_kind="mass",
            value=1.0,
            unit="g",
            standard_uncertainty=0.002,
            method="gravimetric",
            measured_at=datetime(2026, 7, 30, 3, 1, tzinfo=timezone.utc),
            actor="human-operator-1",
        ),
    )
    assert measurement.proposal_id == proposal.id
    assert measurement.bottle_event_id is None

    commit = await service.commit_bottle_action(
        proposal.id,
        actor="operator",
        rationale="Confirmed gravimetric addition",
    )
    replay = await service.reconstruct_bottle(bottle.id)
    diff = await service.bottle_action_diff(proposal.id)
    latest_reservation = await service.repository.latest_reservation_event(
        reservation.reservation_id
    )

    assert commit.proposal_id == proposal.id
    assert replay.stream_sequence == 2
    assert replay.total_mass_g == pytest.approx(1.0)
    assert replay.stock_masses_g == {stock.id: pytest.approx(1.0)}
    assert diff["from_sequence"] == 1
    assert diff["to_sequence"] == 2
    assert diff["total_mass_delta_g"] == pytest.approx(1.0)
    assert diff["stock_mass_deltas_g"] == {stock.id: pytest.approx(1.0)}
    assert diff["line_delta"]["completion_tolerance_g"] == pytest.approx(0.001)
    assert diff["line_delta"]["completion_delta_g"] == pytest.approx(0.0)
    assert latest_reservation is not None
    assert latest_reservation.state == "FULFILLED"

    replayed_commit = await service.commit_bottle_action(
        proposal.id,
        actor="operator",
        rationale="Confirmed gravimetric addition",
    )
    assert replayed_commit.id == commit.id
    assert (await service.reconstruct_bottle(bottle.id)).stream_sequence == 2


@pytest.mark.asyncio
async def test_undermeasurement_does_not_fulfill_entire_reservation(db_session):
    service, reservation, bottle, proposal, stock = (
        await _reserved_action_fixture(db_session)
    )
    await service.confirm_bottle_action(
        proposal.id,
        BottleActionConfirmationInput(
            decision="CONFIRMED",
            confirmer_pseudonym="human-operator-1",
            confirmed_at=datetime(2026, 7, 30, 3, 0, tzinfo=timezone.utc),
            rationale="Bottle, stock, and balance verified",
        ),
    )
    await service.record_bottle_action_measurement(
        proposal.id,
        BottleActionMeasurementInput(
            quantity_kind="mass",
            value=0.98,
            unit="g",
            standard_uncertainty=0.002,
            method="gravimetric",
            measured_at=datetime(2026, 7, 30, 3, 1, tzinfo=timezone.utc),
            actor="human-operator-1",
        ),
    )
    stock_before = await service.repository.stock_balance_g(stock.id)

    with pytest.raises(ExecutionConflictError) as outside_tolerance:
        await service.commit_bottle_action(
            proposal.id,
            actor="operator",
            rationale="Must not silently fulfill a partial dose",
        )

    assert outside_tolerance.value.code == (
        "MEASUREMENT_OUTSIDE_COMPLETION_TOLERANCE"
    )
    latest_reservation = await service.repository.latest_reservation_event(
        reservation.reservation_id
    )
    assert latest_reservation is not None
    assert latest_reservation.state == "RESERVED"
    assert (await service.reconstruct_bottle(bottle.id)).stream_sequence == 1
    assert await service.repository.stock_balance_g(stock.id) == pytest.approx(
        stock_before
    )


@pytest.mark.asyncio
async def test_freeform_bottle_cannot_enter_planned_execution(db_session):
    service, approved, line, stock = await _approved_plan(db_session)
    reservation = await service.reserve_inventory(
        build_plan_version_id=approved.id,
        build_plan_line_id=line.id,
        stock_solution_id=stock.id,
        reserved_mass_g=1.0,
        idempotency_key="quarantine-reservation",
        actor="planner",
        rationale="Reserve the approved build line",
    )
    bottle = await service.create_bottle("Freeform quarantine bottle")
    physical_balance = await service.repository.stock_balance_g(stock.id)
    unreserved_balance = await service.available_stock_g(stock.id)
    assert physical_balance - unreserved_balance == pytest.approx(1.0)
    with pytest.raises(InsufficientStockError):
        await service.add_stock_to_bottle(
            bottle_id=bottle.id,
            stock_solution_id=stock.id,
            mass_g=unreserved_balance + 0.5,
            expected_sequence=1,
            command_id="freeform-cannot-consume-reserved-stock",
            actor="operator",
        )
    direct_event = await service.add_stock_to_bottle(
        bottle_id=bottle.id,
        stock_solution_id=stock.id,
        mass_g=0.1,
        expected_sequence=1,
        command_id="freeform-before-planned",
        actor="operator",
    )
    assert direct_event.payload_json["execution_scope"] == (
        "FREEFORM_UNBOUND_QUARANTINE"
    )
    assert direct_event.payload_json["build_plan_fulfillment_authority"] is False

    with pytest.raises(ExecutionConflictError) as quarantined:
        await service.propose_bottle_action(
            BottleActionProposalInput(
                schema_version="a2-bottle-action-v1",
                reservation_id=reservation.reservation_id,
                bottle_id=bottle.id,
                action_type="ADD_STOCK",
                planned_mass_g=1.0,
                expected_sequence=2,
                idempotency_key="planned-after-freeform",
                actor="operator",
                rationale="Must not reinterpret freeform work as planned execution",
            )
        )

    assert quarantined.value.code == "BOTTLE_FREEFORM_QUARANTINED"
    latest_reservation = await service.repository.latest_reservation_event(
        reservation.reservation_id
    )
    assert latest_reservation is not None
    assert latest_reservation.state == "RESERVED"


@pytest.mark.asyncio
async def test_proposal_requires_active_matching_reservation_and_fresh_stream(
    db_session,
):
    service, reservation, bottle, proposal, _stock = (
        await _reserved_action_fixture(db_session)
    )
    assert proposal.reservation_id == reservation.reservation_id

    await service.transition_reservation(
        reservation.reservation_id,
        "RELEASED",
        idempotency_key="execution-release",
        actor="planner",
        rationale="Cancel the build",
    )
    with pytest.raises(ExecutionConflictError) as inactive:
        await service.propose_bottle_action(
            BottleActionProposalInput(
                schema_version="a2-bottle-action-v1",
                reservation_id=reservation.reservation_id,
                bottle_id=bottle.id,
                action_type="ADD_STOCK",
                planned_mass_g=1.0,
                expected_sequence=1,
                idempotency_key="execution-after-release",
                actor="operator",
                rationale="Must fail closed",
            )
        )
    assert inactive.value.code == "RESERVATION_NOT_ACTIVE"
