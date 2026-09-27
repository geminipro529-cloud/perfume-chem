import json
from datetime import datetime, timezone

import pytest

from app.services.lab_execution import (
    BottleActionConfirmationInput,
    BottleActionMeasurementInput,
    BottleActionProposalInput,
)
from app.services.lab_export import LabExportService
from tests.a2_planning_fixtures import _approved_plan

EXECUTION_TABLES = {
    "lab_bottle_action_proposals",
    "lab_bottle_action_confirmations",
    "lab_bottle_measurements",
    "lab_bottle_action_commits",
}


@pytest.mark.asyncio
async def test_v4_export_is_complete_deterministic_and_idempotent(db_session):
    service, approved, line, stock = await _approved_plan(db_session)
    reservation = await service.reserve_inventory(
        build_plan_version_id=approved.id,
        build_plan_line_id=line.id,
        stock_solution_id=stock.id,
        reserved_mass_g=1.0,
        idempotency_key="execution-export-reservation",
        actor="planner",
        rationale="Reserve export fixture",
    )
    bottle = await service.create_bottle("A2 execution export")
    proposal = await service.propose_bottle_action(
        BottleActionProposalInput(
            schema_version="a2-bottle-action-v1",
            reservation_id=reservation.reservation_id,
            bottle_id=bottle.id,
            action_type="ADD_STOCK",
            planned_mass_g=1.0,
            expected_sequence=1,
            idempotency_key="execution-export-proposal",
            actor="operator",
            rationale="Execute export fixture",
        )
    )
    await service.confirm_bottle_action(
        proposal.id,
        BottleActionConfirmationInput(
            decision="CONFIRMED",
            confirmer_pseudonym="human-export",
            confirmed_at=datetime(2026, 7, 30, 5, 0, tzinfo=timezone.utc),
            rationale="Verified",
        ),
    )
    await service.record_bottle_action_measurement(
        proposal.id,
        BottleActionMeasurementInput(
            quantity_kind="mass",
            value=1.0,
            unit="g",
            standard_uncertainty=0.002,
            method="gravimetric",
            measured_at=datetime(2026, 7, 30, 5, 1, tzinfo=timezone.utc),
            actor="human-export",
        ),
    )
    await service.commit_bottle_action(
        proposal.id,
        actor="operator",
        rationale="Commit export fixture",
    )

    exporter = LabExportService(db_session)
    packet = await exporter.export_execution_workspace()
    before = await exporter.canonical_execution_bytes()
    result = await exporter.import_workspace(packet)
    after = await exporter.canonical_execution_bytes()

    assert packet["format_revision"] == "lab-export-v4"
    assert EXECUTION_TABLES <= set(packet["tables"])
    assert packet["ordering_contract"]["bottle_action_commits"] == [
        "proposal_id",
        "id",
    ]
    assert packet["provenance_contract"]["human_confirmation"] == (
        "lab_bottle_action_confirmations"
    )
    assert result.inserted == 0
    assert result.skipped == sum(
        len(rows) for rows in packet["tables"].values()
    )
    assert after == before
    assert json.loads(after) == packet
