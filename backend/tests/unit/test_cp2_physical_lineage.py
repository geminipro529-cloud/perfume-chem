from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.lab import LabFormulaComponent
from app.services.lab_execution import (
    BottleActionConfirmationInput,
    BottleActionMeasurementInput,
    BottleActionProposalInput,
)
from app.services.lab_service import FormulaComponentInput
from app.services.physical_lineage import (
    PhysicalLineageError,
    PhysicalLineBindingInput,
)
from tests.a2_planning_fixtures import _approved_plan


async def _bound_plan(db_session):
    service, approved, line, stock = await _approved_plan(db_session)
    formula = await service.create_formula("CP2 exact physical fixture")
    version = await service.add_formula_version(
        formula.id,
        brief={"name": "exact physical fixture"},
        constraints={},
        components=(
            FormulaComponentInput(
                stock_solution_id=stock.id,
                requested_mass_g=Decimal("1.000000"),
                unit="g",
            ),
        ),
    )
    component = await db_session.scalar(
        select(LabFormulaComponent).where(
            LabFormulaComponent.formula_version_id == version.id
        )
    )
    assert component is not None
    lot_receipt = await service.finalize_stock_lot_physical_receipt(
        stock_solution_id=stock.id,
        supplier="Test supplier",
        lot_number="LOT-A2-1",
        bottle_identifier="BOTTLE-A2-1",
        label="Jasmine Absolute 10 percent fixture",
        active_fraction_decimal="0.1",
        fraction_basis="mass_fraction",
        carrier=None,
        density_g_ml_decimal="1",
        density_provenance="lot record",
        preparation_state="SUPPLIER_AS_SUPPLIED",
        stock_preparation_receipt_id=None,
        homogeneity_state="CONFIRMED",
        source_reference="test://stock-lot-a2-1",
        reviewer="fixture-reviewer",
        observed_at=datetime(2026, 9, 23, tzinfo=timezone.utc),
        idempotency_key="stock-lot-a2-1",
    )
    binding = await service.bind_build_plan_physical_lineage(
        build_plan_version_id=approved.id,
        formula_version_id=version.id,
        immediate_parent_formula_version_id=None,
        stock_lineage_receipts=[lot_receipt.id],
        release_authority_receipt_ids=["fixture-authority-review"],
        order_policy="BASKET_THEN_DESCENDING_LIQUIDS_MASS_SEPARATE",
        lines=(
            PhysicalLineBindingInput(
                build_plan_line_id=line.id,
                formula_component_id=component.id,
                basket="B1",
                operation="MASS_ADD",
                stock_solution_id=stock.id,
                concentration_fraction_decimal="0.100000",
                concentration_basis="mass_fraction",
                carrier=None,
                stock_preparation_receipt_id=None,
                amount_decimal="1.000000",
                amount_unit="g",
                density_g_ml_decimal=None,
                density_provenance=None,
            ),
        ),
    )
    return service, approved, line, stock, binding


@pytest.mark.asyncio
async def test_missing_physical_binding_returns_hold_not_a_command(db_session) -> None:
    service, approved, _line, _stock = await _approved_plan(db_session)

    result = await service.next_compounding_command(
        build_plan_version_id=approved.id,
        operator="fixture-operator",
        idempotency_key="missing-binding",
    )

    assert result["outcome"] == "ORDER_DRIFT_HOLD"
    assert result["reason"] == "EXACT_PHYSICAL_BINDING_MISSING"
    assert result["command"] is None
    assert result["compounding_authority"] is False


@pytest.mark.asyncio
async def test_readiness_packet_lists_all_missing_work_then_becomes_ready(
    db_session,
) -> None:
    service, approved, line, stock, _binding = await _bound_plan(db_session)

    held = await service.physical_readiness_packet(
        build_plan_version_id=approved.id
    )
    assert held["outcome"] == "HOLD_MISSING_REQUIREMENTS"
    assert {item["code"] for item in held["missing_requirements"]} == {
        "ACTIVE_EXACT_RESERVATION_MISSING"
    }
    assert held["expected_totals"] == {
        "liquid_uL": "0",
        "solid_mg": "1000",
        "combined_total": None,
        "reason": "Mass and volume remain dimensionally separate.",
    }
    assert held["physical_instruction_authorized"] is False

    await service.reserve_inventory(
        build_plan_version_id=approved.id,
        build_plan_line_id=line.id,
        stock_solution_id=stock.id,
        reserved_mass_g=1.0,
        idempotency_key="cp18-readiness-reservation",
        actor="fixture-planner",
        rationale="Readiness fixture",
    )
    ready = await service.physical_readiness_packet(
        build_plan_version_id=approved.id
    )
    assert ready["outcome"] == "READY_FOR_SERVER_SELECTED_COMMAND"
    assert ready["missing_requirements"] == []
    assert ready["operation_count"] == 1
    assert ready["basket_commands"][0]["target_amount_unit"] == "g"
    assert ready["compounding_authority"] is False


@pytest.mark.asyncio
async def test_stock_preparation_requires_exact_decimal_conservation_and_replays(
    db_session,
) -> None:
    service, approved, _line, _stock = await _approved_plan(db_session)
    parent_material = await service.create_material("Ambrox parent fixture")
    carrier_material = await service.create_material("TEC carrier fixture")
    parent = await service.create_stock_solution(
        material_id=parent_material.id,
        active_fraction=0.25,
        fraction_basis="mass_fraction",
        initial_mass_g=20.0,
    )
    carrier = await service.create_stock_solution(
        material_id=carrier_material.id,
        active_fraction=1.0,
        fraction_basis="mass_fraction",
        initial_mass_g=20.0,
    )
    prepared = await service.create_stock_solution(
        material_id=parent_material.id,
        active_fraction=0.05,
        fraction_basis="mass_fraction",
        initial_mass_g=10.0,
    )
    kwargs = {
        "build_plan_version_id": approved.id,
        "parent_stock_solution_id": parent.id,
        "carrier_stock_solution_id": carrier.id,
        "prepared_stock_solution_id": prepared.id,
        "basis": "W_W",
        "parent_quantity_decimal": "2.000000",
        "parent_quantity_unit": "g",
        "carrier_quantity_decimal": "8.000000",
        "carrier_quantity_unit": "g",
        "result_quantity_decimal": "10.000000",
        "result_quantity_unit": "g",
        "density_g_ml_decimal": None,
        "density_provenance": None,
        "homogeneity": "CONFIRMED",
        "label": "Ambrox 5 percent w/w fixture",
        "operator": "fixture-operator",
        "prepared_at": datetime(2026, 9, 23, tzinfo=timezone.utc),
        "idempotency_key": "preparation-fixture",
    }
    receipt = await service.finalize_build_plan_stock_preparation(**kwargs)
    replay = await service.finalize_build_plan_stock_preparation(**kwargs)
    assert replay.id == receipt.id
    assert receipt.resulting_active_fraction_decimal == "0.05"
    assert receipt.compounding_authority is False

    bad = dict(kwargs)
    bad["idempotency_key"] = "preparation-bad-conservation"
    bad["result_quantity_decimal"] = "9.999999"
    with pytest.raises(PhysicalLineageError) as raised:
        await service.finalize_build_plan_stock_preparation(**bad)
    assert raised.value.code == "STOCK_PREPARATION_CONSERVATION_FAILURE"


@pytest.mark.asyncio
async def test_next_resume_complete_replay_and_already_compounded(db_session) -> None:
    service, approved, line, stock, _binding = await _bound_plan(db_session)
    reservation = await service.reserve_inventory(
        build_plan_version_id=approved.id,
        build_plan_line_id=line.id,
        stock_solution_id=stock.id,
        reserved_mass_g=1.0,
        idempotency_key="cp2-physical-reservation",
        actor="fixture-planner",
        rationale="Exact fixture reservation",
    )
    next_command = await service.next_compounding_command(
        build_plan_version_id=approved.id,
        operator="fixture-operator",
        idempotency_key="cp2-next-command",
    )
    assert next_command["outcome"] == "NEXT_LINE_READY"
    assert next_command["command"]["target_amount_decimal"] == "1"
    assert next_command["command"]["physical_instruction_authorized"] is False

    bottle = await service.create_bottle("CP2 lineage fixture bottle")
    proposal = await service.propose_bottle_action(
        BottleActionProposalInput(
            schema_version="a2-bottle-action-v1",
            reservation_id=reservation.reservation_id,
            bottle_id=bottle.id,
            action_type="ADD_STOCK",
            planned_mass_g=1.0,
            expected_sequence=1,
            idempotency_key="cp2-bottle-proposal",
            actor="fixture-operator",
            rationale="Existing physical action fixture",
        )
    )
    await service.confirm_bottle_action(
        proposal.id,
        BottleActionConfirmationInput(
            decision="CONFIRMED",
            confirmer_pseudonym="fixture-human",
            confirmed_at=datetime(2026, 9, 23, 1, 0, tzinfo=timezone.utc),
            rationale="Fixture confirmation",
        ),
    )
    await service.record_bottle_action_measurement(
        proposal.id,
        BottleActionMeasurementInput(
            quantity_kind="mass",
            value=1.0,
            unit="g",
            standard_uncertainty=0.001,
            method="gravimetric",
            measured_at=datetime(2026, 9, 23, 1, 1, tzinfo=timezone.utc),
            actor="fixture-human",
        ),
    )
    commit = await service.commit_bottle_action(
        proposal.id,
        actor="fixture-operator",
        rationale="Fixture committed physical action",
    )
    completion_kwargs = {
        "build_plan_version_id": approved.id,
        "command_id": next_command["command"]["command_id"],
        "bottle_action_commit_id": commit.id,
        "operator": "fixture-operator",
        "completed_at": datetime(2026, 9, 23, 1, 2, tzinfo=timezone.utc),
        "idempotency_key": "cp2-command-completion",
    }
    receipt = await service.complete_compounding_command(**completion_kwargs)
    replay = await service.complete_compounding_command(**completion_kwargs)
    assert receipt == replay
    assert receipt["outcome"] == "COMPLETED"
    assert receipt["replay_safe"] is True
    assert receipt["compounding_authority"] is False

    already = await service.next_compounding_command(
        build_plan_version_id=approved.id,
        operator="fixture-operator",
        idempotency_key="cp2-next-after-complete",
    )
    assert already["outcome"] == "ALREADY_COMPOUNDED"
    assert already["command"] is None


@pytest.mark.asyncio
async def test_cancel_releases_active_reservations_and_is_idempotent(db_session) -> None:
    service, approved, line, stock = await _approved_plan(db_session)
    reservation = await service.reserve_inventory(
        build_plan_version_id=approved.id,
        build_plan_line_id=line.id,
        stock_solution_id=stock.id,
        reserved_mass_g=1.0,
        idempotency_key="cp2-cancel-reservation",
        actor="fixture-planner",
        rationale="Cancellation fixture",
    )
    kwargs = {
        "build_plan_version_id": approved.id,
        "operator": "fixture-operator",
        "reason": "Cancel fixture logical plan",
        "cancelled_at": datetime(2026, 9, 23, 2, 0, tzinfo=timezone.utc),
        "idempotency_key": "cp2-cancel-command",
    }
    cancelled = await service.cancel_compounding_plan(**kwargs)
    replay = await service.cancel_compounding_plan(**kwargs)
    assert cancelled["outcome"] == replay["outcome"] == "CANCELLED"
    assert cancelled["released_reservations"] == [reservation.reservation_id]
    latest = await service.repository.latest_reservation_event(
        reservation.reservation_id
    )
    assert latest is not None and latest.state == "RELEASED"
    assert replay["released_reservations"] == [reservation.reservation_id]
    assert cancelled["compounding_authority"] is False
