import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.lab import (
    LabApplication,
    LabBottle,
    LabBottleEventEffect,
    LabInventoryMovement,
)
from app.services.lab_service import (
    AlreadyCompensatedError,
    IdempotencyConflictError,
    InsufficientStockError,
    LabService,
    StaleBottleStreamError,
)


@pytest.mark.asyncio
async def test_outer_transaction_owns_rollback(db_session):
    service = LabService(db_session)

    with pytest.raises(RuntimeError, match="abort outer unit"):
        async with db_session.begin():
            await service.create_bottle("Must roll back", initial_mass_g=1.0)
            raise RuntimeError("abort outer unit")

    count = await db_session.scalar(select(func.count()).select_from(LabBottle))
    assert count == 0


@pytest.mark.asyncio
async def test_formula_versions_are_sequential_and_immutable(db_session):
    service = LabService(db_session)
    formula = await service.create_formula("Iris Cathedral")
    first = await service.add_formula_version(
        formula.id,
        brief={"identity": "iris and incense"},
        constraints={"must_preserve": ["iris"]},
    )
    second = await service.add_formula_version(
        formula.id,
        brief={"identity": "iris and incense"},
        constraints={"must_preserve": ["iris", "olibanum"]},
    )

    assert first.version_number == 1
    assert second.version_number == 2
    with pytest.raises(ValueError, match="immutable"):
        await service.update_formula_version(first.id, brief={"identity": "changed"})


@pytest.mark.asyncio
async def test_addition_is_atomic_idempotent_and_reconstructs_mass(db_session):
    service = LabService(db_session)
    material = await service.create_material("Alpha Irone")
    stock = await service.create_stock_solution(
        material_id=material.id,
        active_fraction=0.30,
        fraction_basis="mass_fraction",
        initial_mass_g=10.0,
        density_g_ml=0.96,
    )
    bottle = await service.create_bottle("Iris trial", initial_mass_g=5.0)

    event = await service.add_stock_to_bottle(
        bottle_id=bottle.id,
        stock_solution_id=stock.id,
        mass_g=1.25,
        measured_volume_ul=1302.083333,
        expected_sequence=1,
        command_id="add-alpha-irone-1",
    )
    retry = await service.add_stock_to_bottle(
        bottle_id=bottle.id,
        stock_solution_id=stock.id,
        mass_g=1.25,
        measured_volume_ul=1302.083333,
        expected_sequence=1,
        command_id="add-alpha-irone-1",
    )

    state = await service.reconstruct_bottle(bottle.id)
    assert retry.id == event.id
    assert state.stream_sequence == 2
    assert state.total_mass_g == pytest.approx(6.25)
    assert state.stock_masses_g[stock.id] == pytest.approx(1.25)
    assert await service.stock_balance_g(stock.id) == pytest.approx(8.75)

    with pytest.raises(IdempotencyConflictError, match="different request"):
        await service.add_stock_to_bottle(
            bottle_id=bottle.id,
            stock_solution_id=stock.id,
            mass_g=0.5,
            expected_sequence=2,
            command_id="add-alpha-irone-1",
        )


@pytest.mark.asyncio
async def test_stale_addition_and_insufficient_stock_leave_no_partial_event(db_session):
    service = LabService(db_session)
    material = await service.create_material("Orris Liquid")
    stock = await service.create_stock_solution(
        material_id=material.id,
        active_fraction=0.30,
        fraction_basis="mass_fraction",
        initial_mass_g=2.0,
        density_g_ml=0.98,
    )
    bottle = await service.create_bottle("Rollback trial", initial_mass_g=1.0)
    bottle_id = bottle.id
    stock_id = stock.id
    await service.add_stock_to_bottle(
        bottle_id=bottle_id,
        stock_solution_id=stock_id,
        mass_g=0.5,
        expected_sequence=1,
        command_id="first-addition",
    )

    with pytest.raises(StaleBottleStreamError):
        await service.add_stock_to_bottle(
            bottle_id=bottle_id,
            stock_solution_id=stock_id,
            mass_g=0.25,
            expected_sequence=1,
            command_id="stale-addition",
        )
    with pytest.raises(InsufficientStockError):
        await service.add_stock_to_bottle(
            bottle_id=bottle_id,
            stock_solution_id=stock_id,
            mass_g=5.0,
            expected_sequence=2,
            command_id="too-large",
        )

    state = await service.reconstruct_bottle(bottle_id)
    assert state.stream_sequence == 2
    assert state.total_mass_g == pytest.approx(1.5)
    assert await service.stock_balance_g(stock_id) == pytest.approx(1.5)


@pytest.mark.asyncio
async def test_transfer_moves_mass_between_bottles_in_one_transaction(db_session):
    service = LabService(db_session)
    source = await service.create_bottle("Source", initial_mass_g=4.0)
    destination = await service.create_bottle("Destination", initial_mass_g=1.0)

    source_event, destination_event = await service.transfer_between_bottles(
        source_bottle_id=source.id,
        destination_bottle_id=destination.id,
        mass_g=1.5,
        source_expected_sequence=1,
        destination_expected_sequence=1,
        command_id="transfer-1",
    )

    source_state = await service.reconstruct_bottle(source.id)
    destination_state = await service.reconstruct_bottle(destination.id)
    assert source_event.transaction_id == destination_event.transaction_id
    assert source_state.total_mass_g == pytest.approx(2.5)
    assert destination_state.total_mass_g == pytest.approx(2.5)
    assert source_state.total_mass_g + destination_state.total_mass_g == pytest.approx(5.0)


@pytest.mark.asyncio
async def test_transfer_command_identity_uses_full_command_and_retry_is_request_bound(db_session):
    service = LabService(db_session)
    source = await service.create_bottle("Long source", initial_mass_g=5.0)
    destination = await service.create_bottle("Long destination", initial_mass_g=0.0)
    common = "same-prefix-" + ("x" * 80)

    first = await service.transfer_between_bottles(
        source_bottle_id=source.id,
        destination_bottle_id=destination.id,
        mass_g=1.0,
        source_expected_sequence=1,
        destination_expected_sequence=1,
        command_id=common + "-one",
    )
    second = await service.transfer_between_bottles(
        source_bottle_id=source.id,
        destination_bottle_id=destination.id,
        mass_g=1.0,
        source_expected_sequence=2,
        destination_expected_sequence=2,
        command_id=common + "-two",
    )

    assert first[0].id != second[0].id
    with pytest.raises(IdempotencyConflictError, match="different request"):
        await service.transfer_between_bottles(
            source_bottle_id=source.id,
            destination_bottle_id=destination.id,
            mass_g=0.5,
            source_expected_sequence=3,
            destination_expected_sequence=3,
            command_id=common + "-two",
        )


@pytest.mark.asyncio
async def test_compensating_event_reverses_bottle_and_inventory_without_editing_history(
    db_session,
):
    service = LabService(db_session)
    material = await service.create_material("Hydroxycitronellol")
    stock = await service.create_stock_solution(
        material_id=material.id,
        active_fraction=1.0,
        fraction_basis="mass_fraction",
        initial_mass_g=3.0,
        density_g_ml=1.0,
    )
    bottle = await service.create_bottle("Correction trial", initial_mass_g=1.0)
    addition = await service.add_stock_to_bottle(
        bottle_id=bottle.id,
        stock_solution_id=stock.id,
        mass_g=0.5,
        expected_sequence=1,
        command_id="mistaken-addition",
    )

    correction = await service.compensate_bottle_event(
        bottle_id=bottle.id,
        event_id=addition.id,
        expected_sequence=2,
        command_id="reverse-mistaken-addition",
    )

    state = await service.reconstruct_bottle(bottle.id)
    assert correction.correction_of_event_id == addition.id
    assert state.stream_sequence == 3
    assert state.total_mass_g == pytest.approx(1.0)
    assert await service.stock_balance_g(stock.id) == pytest.approx(3.0)

    with pytest.raises(AlreadyCompensatedError):
        await service.compensate_bottle_event(
            bottle_id=bottle.id,
            event_id=addition.id,
            expected_sequence=3,
            command_id="second-reversal-attempt",
        )


@pytest.mark.asyncio
async def test_transfer_compensation_reverses_both_sides_and_preserves_total_mass(db_session):
    service = LabService(db_session)
    source = await service.create_bottle("Comp source", initial_mass_g=2.0)
    destination = await service.create_bottle("Comp destination", initial_mass_g=0.0)
    transfer_out, _ = await service.transfer_between_bottles(
        source_bottle_id=source.id,
        destination_bottle_id=destination.id,
        mass_g=1.0,
        source_expected_sequence=1,
        destination_expected_sequence=1,
        command_id="paired-transfer",
    )

    await service.compensate_bottle_event(
        bottle_id=source.id,
        event_id=transfer_out.id,
        expected_sequence=2,
        command_id="reverse-paired-transfer",
    )

    source_state = await service.reconstruct_bottle(source.id)
    destination_state = await service.reconstruct_bottle(destination.id)
    assert source_state.total_mass_g == pytest.approx(2.0)
    assert destination_state.total_mass_g == pytest.approx(0.0)
    assert source_state.total_mass_g + destination_state.total_mass_g == pytest.approx(2.0)


@pytest.mark.asyncio
async def test_concurrent_different_bottles_cannot_overdraw_shared_stock(test_engine):
    factory = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as setup_session:
        setup = LabService(setup_session)
        material = await setup.create_material("Concurrent stock")
        stock = await setup.create_stock_solution(
            material_id=material.id,
            active_fraction=1.0,
            fraction_basis="mass_fraction",
            initial_mass_g=1.0,
        )
        left = await setup.create_bottle("Concurrent left")
        right = await setup.create_bottle("Concurrent right")

    async def add(bottle_id: str, command_id: str):
        async with factory() as session:
            service = LabService(session)
            return await service.add_stock_to_bottle(
                bottle_id=bottle_id,
                stock_solution_id=stock.id,
                mass_g=0.75,
                expected_sequence=1,
                command_id=command_id,
            )

    results = await asyncio.gather(
        add(left.id, "concurrent-left"),
        add(right.id, "concurrent-right"),
        return_exceptions=True,
    )

    assert sum(not isinstance(result, Exception) for result in results) == 1
    assert sum(isinstance(result, InsufficientStockError) for result in results) == 1
    async with factory() as check_session:
        assert await LabService(check_session).stock_balance_g(stock.id) == pytest.approx(0.25)


@pytest.mark.asyncio
async def test_concurrent_same_bottle_rejects_stale_stream_write(test_engine):
    factory = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as setup_session:
        setup = LabService(setup_session)
        material = await setup.create_material("Concurrent stream material")
        stock = await setup.create_stock_solution(
            material_id=material.id,
            active_fraction=1.0,
            fraction_basis="mass_fraction",
            initial_mass_g=2.0,
        )
        bottle = await setup.create_bottle("Concurrent stream bottle")

    async def add(command_id: str):
        async with factory() as session:
            return await LabService(session).add_stock_to_bottle(
                bottle_id=bottle.id,
                stock_solution_id=stock.id,
                mass_g=0.75,
                expected_sequence=1,
                command_id=command_id,
            )

    results = await asyncio.gather(
        add("same-bottle-left"),
        add("same-bottle-right"),
        return_exceptions=True,
    )

    assert sum(not isinstance(result, Exception) for result in results) == 1
    assert sum(isinstance(result, StaleBottleStreamError) for result in results) == 1
    async with factory() as check_session:
        state = await LabService(check_session).reconstruct_bottle(bottle.id)
        assert state.stream_sequence == 2
        assert state.total_mass_g == pytest.approx(0.75)


@pytest.mark.asyncio
async def test_timezone_aware_application_round_trips_as_utc(test_engine):
    factory = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    bangkok = timezone(timedelta(hours=7))
    applied_at = datetime(2026, 7, 16, 20, 30, tzinfo=bangkok)
    async with factory() as setup_session:
        service = LabService(setup_session)
        bottle = await service.create_bottle("Timezone bottle")
        experiment = await service.create_experiment(
            "Timezone experiment",
            protocol={"timezone": "Asia/Bangkok"},
        )
        sample = await service.add_experiment_sample(
            experiment_id=experiment.id,
            bottle_id=bottle.id,
            blind_code="TZ-1",
        )
        application = await service.record_application(
            sample_id=sample.id,
            applied_at=applied_at,
            dose={"sprays": 1},
            context={"location": "Bangkok"},
        )
        application_id = application.id

    async with factory() as check_session:
        stored = await check_session.get(LabApplication, application_id)
        assert stored is not None
        assert stored.applied_at.utcoffset() == timedelta(0)
        assert stored.applied_at == applied_at.astimezone(timezone.utc)


@pytest.mark.asyncio
async def test_database_rejects_mismatched_effect_and_inventory_links(db_session):
    service = LabService(db_session)
    material = await service.create_material("Link integrity")
    stock = await service.create_stock_solution(
        material_id=material.id,
        active_fraction=1.0,
        fraction_basis="mass_fraction",
        initial_mass_g=1.0,
    )
    first = await service.create_bottle("Link first")
    second = await service.create_bottle("Link second")
    event = await service.add_stock_to_bottle(
        bottle_id=first.id,
        stock_solution_id=stock.id,
        mass_g=0.1,
        expected_sequence=1,
        command_id="valid-link",
    )
    event_id = event.id
    second_id = second.id
    stock_id = stock.id
    material_id = material.id

    with pytest.raises(IntegrityError):
        async with db_session.begin():
            db_session.add(
                LabBottleEventEffect(
                    event_id=event_id,
                    bottle_id=second_id,
                    stock_solution_id=stock_id,
                    material_id=material_id,
                    mass_delta_g=0.1,
                )
            )

    effect = (
        await db_session.execute(
            select(LabBottleEventEffect).where(LabBottleEventEffect.event_id == event_id)
        )
    ).scalar_one()
    effect_id = effect.id
    await db_session.rollback()
    with pytest.raises(IntegrityError):
        async with db_session.begin():
            db_session.add(
                LabInventoryMovement(
                    stock_solution_id=stock_id,
                    event_effect_id=effect_id,
                    mass_delta_g=-0.1,
                    reason="duplicate-effect-movement",
                )
            )
