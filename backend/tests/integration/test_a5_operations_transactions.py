from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.lab import (
    LabBottleEvent,
    LabBottleEventEffect,
    LabInventoryMovement,
)
from app.services.lab_execution import (
    BottleActionConfirmationInput,
    BottleActionMeasurementInput,
    BottleActionProposalInput,
)
from app.services.lab_service import LabService, LabTransactionError
from tests.a2_planning_fixtures import _approved_plan


@pytest.mark.asyncio
async def test_a5_consumption_movement_records_complete_audit_fields(db_session):
    service = LabService(db_session)
    material = await service.create_material("A5 material")
    stock = await service.create_stock_solution(
        material_id=material.id,
        active_fraction=0.25,
        fraction_basis="mass_fraction",
        initial_mass_g=5.0,
    )
    bottle = await service.create_bottle("A5 bottle")

    event = await service.add_stock_to_bottle(
        bottle_id=bottle.id,
        stock_solution_id=stock.id,
        mass_g=1.0,
        expected_sequence=1,
        command_id="a5-consumption",
        standard_uncertainty=0.002,
        actor="human-operator",
    )
    movement = (
        await db_session.execute(
            select(LabInventoryMovement).where(
                LabInventoryMovement.bottle_event_id == event.id
            )
        )
    ).scalar_one()

    assert event.event_type == "ADD_MATERIAL"
    assert movement.movement_type == "CONSUMPTION"
    assert movement.raw_quantity == pytest.approx(1.0)
    assert movement.active_quantity == pytest.approx(0.25)
    assert movement.unit == "g"
    assert movement.basis == "mass"
    assert movement.balance_before == pytest.approx(5.0)
    assert movement.balance_after == pytest.approx(4.0)
    assert movement.standard_uncertainty == pytest.approx(0.002)
    assert movement.actor == "human-operator"
    assert movement.transaction_id == event.transaction_id
    assert movement.idempotency_key


@pytest.mark.asyncio
async def test_a5_solvent_addition_replays_separately_from_odorant_mass(
    db_session,
):
    service = LabService(db_session)
    material = await service.create_material("Ethanol")
    stock = await service.create_stock_solution(
        material_id=material.id,
        active_fraction=1.0,
        fraction_basis="mass_fraction",
        initial_mass_g=5.0,
        solvent_name="ethanol",
    )
    bottle = await service.create_bottle("A5 solvent bottle")

    event = await service.add_solvent_to_bottle(
        bottle_id=bottle.id,
        stock_solution_id=stock.id,
        mass_g=1.5,
        expected_sequence=1,
        command_id="a5-solvent",
        actor="operator",
    )
    replay = await service.reconstruct_bottle(bottle.id)

    assert event.event_type == "ADD_SOLVENT"
    assert replay.total_mass_g == pytest.approx(1.5)
    assert replay.solvent_mass_g == pytest.approx(1.5)


@pytest.mark.asyncio
async def test_a5_reservation_and_release_append_zero_delta_movements(db_session):
    service, approved, line, stock = await _approved_plan(db_session)

    reserved = await service.reserve_inventory(
        build_plan_version_id=approved.id,
        build_plan_line_id=line.id,
        stock_solution_id=stock.id,
        reserved_mass_g=1.0,
        idempotency_key="a5-reservation",
        actor="planner",
        rationale="Reserve A5 line",
    )
    released = await service.transition_reservation(
        reserved.reservation_id,
        "RELEASED",
        idempotency_key="a5-reservation-release",
        actor="planner",
        rationale="Release A5 line",
    )
    movements = list(
        (
            await db_session.execute(
                select(LabInventoryMovement)
                .where(
                    LabInventoryMovement.reservation_event_id.in_(
                        [reserved.id, released.id]
                    )
                )
                .order_by(LabInventoryMovement.created_at)
            )
        ).scalars()
    )

    assert [movement.movement_type for movement in movements] == [
        "RESERVATION",
        "RESERVATION_RELEASE",
    ]
    assert all(
        movement.balance_before == movement.balance_after
        for movement in movements
    )
    assert all(movement.build_plan_line_id == line.id for movement in movements)


@pytest.mark.asyncio
async def test_a5_tare_and_close_are_append_only_and_close_blocks_addition(
    db_session,
):
    service = LabService(db_session)
    material = await service.create_material("A5 closed material")
    stock = await service.create_stock_solution(
        material_id=material.id,
        active_fraction=1.0,
        fraction_basis="mass_fraction",
        initial_mass_g=2.0,
    )
    bottle = await service.create_bottle("A5 close bottle")
    bottle_id = bottle.id
    stock_id = stock.id

    tare = await service.tare_bottle(
        bottle_id=bottle.id,
        tare_mass_g=12.5,
        expected_sequence=1,
        command_id="a5-tare",
        actor="operator",
    )
    closed = await service.close_bottle(
        bottle_id=bottle.id,
        expected_sequence=2,
        command_id="a5-close",
        actor="reviewer",
    )

    assert tare.event_type == "TARE_CONTAINER"
    assert tare.payload_json["tare_mass_g"] == pytest.approx(12.5)
    assert closed.event_type == "CLOSE_BATCH"
    with pytest.raises(LabTransactionError, match="closed"):
        await service.add_stock_to_bottle(
            bottle_id=bottle.id,
            stock_solution_id=stock.id,
            mass_g=0.5,
            expected_sequence=3,
            command_id="a5-after-close",
        )
    assert await service.repository.latest_sequence(bottle_id) == 3
    assert await service.stock_balance_g(stock_id) == pytest.approx(2.0)


@pytest.mark.asyncio
async def test_a5_transfer_records_measured_loss_in_one_transaction(db_session):
    service = LabService(db_session)
    source = await service.create_bottle("A5 transfer source", initial_mass_g=4)
    destination = await service.create_bottle("A5 transfer destination")

    outgoing, incoming = await service.transfer_between_bottles(
        source_bottle_id=source.id,
        destination_bottle_id=destination.id,
        mass_g=2.0,
        measured_loss_g=0.1,
        source_expected_sequence=1,
        destination_expected_sequence=1,
        command_id="a5-transfer-loss",
    )

    source_state = await service.reconstruct_bottle(source.id)
    destination_state = await service.reconstruct_bottle(destination.id)
    assert outgoing.event_type == incoming.event_type == "TRANSFER"
    assert outgoing.transaction_id == incoming.transaction_id
    assert outgoing.payload_json["measured_loss_g"] == pytest.approx(0.1)
    assert source_state.total_mass_g == pytest.approx(2.0)
    assert destination_state.total_mass_g == pytest.approx(1.9)
    assert (
        source_state.total_mass_g + destination_state.total_mass_g
        == pytest.approx(3.9)
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure_stage",
    ("event", "effect", "movement"),
)
async def test_a5_failure_at_each_write_stage_rolls_back_both_ledgers(
    db_session,
    monkeypatch,
    failure_stage,
):
    service = LabService(db_session)
    material = await service.create_material("A5 rollback material")
    stock = await service.create_stock_solution(
        material_id=material.id,
        active_fraction=1.0,
        fraction_basis="mass_fraction",
        initial_mass_g=2.0,
    )
    bottle = await service.create_bottle("A5 rollback bottle")
    bottle_id = bottle.id
    stock_id = stock.id
    original_add = service.repository.add

    async def fail_stage(record):
        should_fail = (
            (
                failure_stage == "event"
                and isinstance(record, LabBottleEvent)
                and record.event_type == "ADD_MATERIAL"
            )
            or (
                failure_stage == "effect"
                and isinstance(record, LabBottleEventEffect)
            )
            or (
                failure_stage == "movement"
                and isinstance(record, LabInventoryMovement)
            )
        )
        if should_fail:
            raise RuntimeError(f"injected {failure_stage} failure")
        return await original_add(record)

    monkeypatch.setattr(service.repository, "add", fail_stage)
    with pytest.raises(RuntimeError, match=f"injected {failure_stage}"):
        await service.add_stock_to_bottle(
            bottle_id=bottle.id,
            stock_solution_id=stock.id,
            mass_g=0.5,
            expected_sequence=1,
            command_id="a5-rollback",
        )

    db_session.expire_all()
    event_count = await db_session.scalar(
        select(func.count())
        .select_from(LabBottleEvent)
        .where(LabBottleEvent.bottle_id == bottle_id)
    )
    assert event_count == 1
    effect_count = await db_session.scalar(
        select(func.count())
        .select_from(LabBottleEventEffect)
        .where(LabBottleEventEffect.bottle_id == bottle_id)
    )
    movement_count = await db_session.scalar(
        select(func.count())
        .select_from(LabInventoryMovement)
        .where(LabInventoryMovement.stock_solution_id == stock_id)
    )
    assert effect_count == 0
    assert movement_count == 0
    assert await service.stock_balance_g(stock_id) == pytest.approx(2.0)


@pytest.mark.asyncio
async def test_a5_lifecycle_commit_persists_typed_line_delta(db_session):
    service, approved, line, stock = await _approved_plan(db_session)
    reservation = await service.reserve_inventory(
        build_plan_version_id=approved.id,
        build_plan_line_id=line.id,
        stock_solution_id=stock.id,
        reserved_mass_g=1.0,
        idempotency_key="a5-lifecycle-reservation",
        actor="planner",
        rationale="Reserve typed delta",
    )
    bottle = await service.create_bottle("A5 lifecycle bottle")
    proposal = await service.propose_bottle_action(
        BottleActionProposalInput(
            schema_version="a5-bottle-action-v1",
            reservation_id=reservation.reservation_id,
            bottle_id=bottle.id,
            action_type="ADD_MATERIAL",
            planned_mass_g=1.0,
            expected_sequence=1,
            idempotency_key="a5-lifecycle-proposal",
            actor="operator",
            rationale="Execute typed delta",
        )
    )
    await service.confirm_bottle_action(
        proposal.id,
        BottleActionConfirmationInput(
            decision="CONFIRMED",
            confirmer_pseudonym="human-1",
            confirmed_at=datetime(2026, 7, 30, 4, 0, tzinfo=timezone.utc),
            rationale="Verified",
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
            measured_at=datetime(2026, 7, 30, 4, 1, tzinfo=timezone.utc),
            actor="human-1",
        ),
    )
    commit = await service.commit_bottle_action(
        proposal.id,
        actor="operator",
        rationale="Commit typed delta",
    )
    line_delta = commit.state_diff_json["line_delta"]

    assert line_delta["target_line_id"] == line.target_line_id
    assert line_delta["target_identity"] == line.target_identity
    assert line_delta["planned_raw_quantity"] == pytest.approx(
        line.planned_raw_quantity
    )
    assert line_delta["planned_active_quantity"] == pytest.approx(
        line.planned_active_quantity
    )
    assert line_delta["reserved_quantity"] == pytest.approx(1.0)
    assert line_delta["committed_quantity"] == pytest.approx(0.98)
    assert line_delta["unit"] == line.unit
    assert line_delta["basis"] == line.concentration_basis
    assert line_delta["action_state"] == "COMMITTED"


@pytest.mark.asyncio
async def test_a5_simultaneous_commit_retries_create_one_atomic_result(
    test_engine,
):
    factory = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with factory() as setup_session:
        service, approved, line, stock = await _approved_plan(setup_session)
        reservation = await service.reserve_inventory(
            build_plan_version_id=approved.id,
            build_plan_line_id=line.id,
            stock_solution_id=stock.id,
            reserved_mass_g=1.0,
            idempotency_key="a5-concurrent-reservation",
            actor="planner",
            rationale="Concurrent commit",
        )
        bottle = await service.create_bottle("A5 concurrent commit")
        proposal = await service.propose_bottle_action(
            BottleActionProposalInput(
                schema_version="a5-bottle-action-v1",
                reservation_id=reservation.reservation_id,
                bottle_id=bottle.id,
                action_type="ADD_MATERIAL",
                planned_mass_g=1.0,
                expected_sequence=1,
                idempotency_key="a5-concurrent-proposal",
                actor="operator",
                rationale="Concurrent commit",
            )
        )
        await service.confirm_bottle_action(
            proposal.id,
            BottleActionConfirmationInput(
                decision="CONFIRMED",
                confirmer_pseudonym="human-1",
                confirmed_at=datetime(
                    2026,
                    7,
                    30,
                    5,
                    0,
                    tzinfo=timezone.utc,
                ),
                rationale="Verified",
            ),
        )
        await service.record_bottle_action_measurement(
            proposal.id,
            BottleActionMeasurementInput(
                quantity_kind="mass",
                value=0.9,
                unit="g",
                standard_uncertainty=0.002,
                method="gravimetric",
                measured_at=datetime(
                    2026,
                    7,
                    30,
                    5,
                    1,
                    tzinfo=timezone.utc,
                ),
                actor="human-1",
            ),
        )
        proposal_id = proposal.id
        bottle_id = bottle.id
        stock_id = stock.id
        await setup_session.commit()

    async def commit_once():
        async with factory() as session:
            return await LabService(session).commit_bottle_action(
                proposal_id,
                actor="operator",
                rationale="Concurrent idempotent commit",
            )

    commits = await asyncio.gather(commit_once(), commit_once())

    assert commits[0].id == commits[1].id
    async with factory() as check_session:
        service = LabService(check_session)
        assert (
            await service.reconstruct_bottle(bottle_id)
        ).stream_sequence == 2
        movement_count = await check_session.scalar(
            select(func.count())
            .select_from(LabInventoryMovement)
            .where(
                LabInventoryMovement.stock_solution_id == stock_id,
                LabInventoryMovement.movement_type == "CONSUMPTION",
            )
        )
    assert movement_count == 1
