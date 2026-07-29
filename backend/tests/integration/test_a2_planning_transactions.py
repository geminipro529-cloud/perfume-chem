import asyncio
from dataclasses import replace

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.lab_planning import LabInventoryReservationEvent
from app.services.lab_planning import (
    InsufficientAvailableStockError,
    PlanningConflictError,
)
from app.services.lab_service import LabService
from tests.a2_planning_fixtures import (
    _approved_plan,
    _build_plan_command,
    _planning_graph,
)


@pytest.mark.asyncio
async def test_reservation_is_atomic_idempotent_and_reduces_available_stock(
    db_session,
):
    service, approved_plan, line, stock = await _approved_plan(db_session)
    event = await service.reserve_inventory(
        build_plan_version_id=approved_plan.id,
        build_plan_line_id=line.id,
        stock_solution_id=stock.id,
        reserved_mass_g=1.25,
        idempotency_key="reserve-plan-line-1",
        actor="Sol",
        rationale="Approved build",
    )
    retry = await service.reserve_inventory(
        build_plan_version_id=approved_plan.id,
        build_plan_line_id=line.id,
        stock_solution_id=stock.id,
        reserved_mass_g=1.25,
        idempotency_key="reserve-plan-line-1",
        actor="Sol",
        rationale="Approved build",
    )
    assert retry.id == event.id
    assert await service.available_stock_g(stock.id) == pytest.approx(
        stock.initial_mass_g - 1.25
    )
    latest_plan = await service.repository.latest_build_plan_version(
        approved_plan.plan_id
    )
    assert latest_plan is not None
    assert latest_plan.status == "RESERVED"
    assert latest_plan.parent_version_id == approved_plan.id


@pytest.mark.asyncio
async def test_reservation_idempotency_conflict_rolls_back(db_session):
    service, approved_plan, line, stock = await _approved_plan(db_session)
    event = await service.reserve_inventory(
        build_plan_version_id=approved_plan.id,
        build_plan_line_id=line.id,
        stock_solution_id=stock.id,
        reserved_mass_g=1.25,
        idempotency_key="reserve-plan-line-conflict",
        actor="Sol",
        rationale="Approved build",
    )
    with pytest.raises(PlanningConflictError) as error:
        await service.reserve_inventory(
            build_plan_version_id=approved_plan.id,
            build_plan_line_id=line.id,
            stock_solution_id=stock.id,
            reserved_mass_g=1.5,
            idempotency_key="reserve-plan-line-conflict",
            actor="Sol",
            rationale="Different command bytes",
        )
    assert error.value.code == "RESERVATION_IDEMPOTENCY_CONFLICT"
    assert len(
        await service.repository.reservation_events(event.reservation_id)
    ) == 1


@pytest.mark.asyncio
async def test_reservation_release_restores_availability_and_is_terminal(
    db_session,
):
    service, approved_plan, line, stock = await _approved_plan(db_session)
    reserved = await service.reserve_inventory(
        build_plan_version_id=approved_plan.id,
        build_plan_line_id=line.id,
        stock_solution_id=stock.id,
        reserved_mass_g=2.0,
        idempotency_key="reserve-release",
        actor="Sol",
        rationale="Approved build",
    )
    released = await service.transition_reservation(
        reserved.reservation_id,
        "RELEASED",
        idempotency_key="release-reservation",
        actor="Sol",
        rationale="Build cancelled before execution",
    )
    assert released.sequence == 2
    assert released.parent_event_id == reserved.id
    assert released.state == "RELEASED"
    assert await service.available_stock_g(stock.id) == pytest.approx(
        stock.initial_mass_g
    )
    with pytest.raises(PlanningConflictError) as terminal:
        await service.transition_reservation(
            reserved.reservation_id,
            "FULFILLED",
            idempotency_key="release-terminal-conflict",
            actor="Sol",
            rationale="Invalid terminal transition",
        )
    assert terminal.value.code == "INVALID_RESERVATION_TRANSITION"


@pytest.mark.asyncio
async def test_reservation_rejects_unknown_or_mismatched_authority_without_rows(
    db_session,
):
    service, approved_plan, line, stock = await _approved_plan(db_session)
    other_material = await service.create_material("Other stock material")
    other_stock = await service.create_stock_solution(
        material_id=other_material.id,
        active_fraction=1.0,
        fraction_basis="mass_fraction",
        initial_mass_g=5.0,
    )
    commands = (
        {
            "build_plan_version_id": "missing-plan",
            "build_plan_line_id": line.id,
            "stock_solution_id": stock.id,
            "expected_code": "BUILD_PLAN_NOT_FOUND",
        },
        {
            "build_plan_version_id": approved_plan.id,
            "build_plan_line_id": "missing-line",
            "stock_solution_id": stock.id,
            "expected_code": "BUILD_PLAN_LINE_NOT_FOUND",
        },
        {
            "build_plan_version_id": approved_plan.id,
            "build_plan_line_id": line.id,
            "stock_solution_id": other_stock.id,
            "expected_code": "RESERVATION_STOCK_MISMATCH",
        },
    )
    for position, command in enumerate(commands, start=1):
        expected_code = command.pop("expected_code")
        with pytest.raises(PlanningConflictError) as error:
            await service.reserve_inventory(
                **command,
                reserved_mass_g=1.0,
                idempotency_key=f"invalid-reservation-{position}",
                actor="Sol",
                rationale="Must roll back",
            )
        assert error.value.code == expected_code
    assert (
        await db_session.scalar(
            select(func.count()).select_from(LabInventoryReservationEvent)
        )
        == 0
    )


@pytest.mark.asyncio
async def test_concurrent_reservations_cannot_overreserve_shared_stock(
    test_engine,
):
    factory = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with factory() as setup_session:
        service, target, acceptance, mapping, target_line, stock, evidence = (
            await _planning_graph(setup_session)
        )
        base_command = _build_plan_command(
            target,
            acceptance,
            mapping,
            target_line,
            stock,
            evidence,
        )

        async def approve(command):
            draft = await service.create_build_plan(command)
            review = await service.transition_build_plan(
                draft.id,
                next_status="UNDER_REVIEW",
                actor="reviewer",
                rationale="Concurrent fixture review",
            )
            approved = await service.transition_build_plan(
                review.id,
                next_status="APPROVED",
                actor="reviewer",
                rationale="Concurrent fixture approval",
            )
            approved_line = (
                await service.repository.build_plan_lines(approved.id)
            )[0]
            return approved, approved_line

        left_plan, left_line = await approve(base_command)
        right_plan, right_line = await approve(
            replace(
                base_command,
                rationale="Second executable plan sharing one stock lot",
            )
        )
        await setup_session.commit()

    async def reserve(plan, line, idempotency_key: str):
        async with factory() as session:
            return await LabService(session).reserve_inventory(
                build_plan_version_id=plan.id,
                build_plan_line_id=line.id,
                stock_solution_id=stock.id,
                reserved_mass_g=7.5,
                idempotency_key=idempotency_key,
                actor="Sol",
                rationale="Concurrent reservation test",
            )

    results = await asyncio.gather(
        reserve(left_plan, left_line, "reservation-a"),
        reserve(right_plan, right_line, "reservation-b"),
        return_exceptions=True,
    )
    assert (
        sum(
            isinstance(result, LabInventoryReservationEvent)
            for result in results
        )
        == 1
    ), results
    assert (
        sum(
            isinstance(result, InsufficientAvailableStockError)
            for result in results
        )
        == 1
    ), results
    async with factory() as check_session:
        assert await LabService(check_session).available_stock_g(
            stock.id
        ) == pytest.approx(2.5)
