import json

import pytest
from sqlalchemy import func, select

from app.models.base import Base
from app.services.lab_export import LabExportService
from tests.a2_planning_fixtures import _approved_plan
from tests.unit.test_a2_planning_schema import PLANNING_TABLES

V1_TABLE_ORDER = (
    "lab_evidence_records",
    "lab_materials",
    "lab_material_aliases",
    "lab_material_properties",
    "lab_restrictions",
    "lab_constituents",
    "lab_stock_solutions",
    "lab_formulas",
    "lab_formula_versions",
    "lab_formula_components",
    "lab_batches",
    "lab_bottles",
    "lab_bottle_events",
    "lab_bottle_event_effects",
    "lab_inventory_movements",
    "lab_bottle_measurements",
    "lab_experiments",
    "lab_samples",
    "lab_applications",
    "lab_observations",
    "lab_pairwise_comparisons",
    "lab_predictions",
    "lab_outcomes",
)


async def _planning_row_count(session) -> int:
    total = 0
    for table_name in sorted(PLANNING_TABLES):
        table = Base.metadata.tables[table_name]
        total += int(
            await session.scalar(select(func.count()).select_from(table)) or 0
        )
    return total


@pytest.mark.asyncio
async def test_v2_export_orders_complete_planning_graph(db_session):
    service, approved_plan, line, stock = await _approved_plan(db_session)
    await service.reserve_inventory(
        build_plan_version_id=approved_plan.id,
        build_plan_line_id=line.id,
        stock_solution_id=stock.id,
        reserved_mass_g=1.25,
        idempotency_key="export-reservation",
        actor="Sol",
        rationale="Complete export graph",
    )
    packet = await LabExportService(db_session).export_planning_workspace()
    assert packet["format_revision"] == "lab-export-v2"
    assert set(PLANNING_TABLES) <= set(packet["tables"])
    assert packet["ordering_contract"]["target_versions"] == [
        "target_id",
        "version_number",
        "id",
    ]
    assert packet["ordering_contract"]["build_plan_versions"] == [
        "plan_id",
        "version_number",
        "id",
    ]
    assert packet["ordering_contract"]["reservation_events"] == [
        "reservation_id",
        "sequence",
        "id",
    ]
    assert len(packet["tables"]["lab_build_plan_versions"]) == 4
    assert len(packet["tables"]["lab_inventory_reservation_events"]) == 1


@pytest.mark.asyncio
async def test_v2_export_import_is_byte_deterministic_and_idempotent(
    db_session,
):
    service, approved_plan, line, stock = await _approved_plan(db_session)
    await service.reserve_inventory(
        build_plan_version_id=approved_plan.id,
        build_plan_line_id=line.id,
        stock_solution_id=stock.id,
        reserved_mass_g=1.25,
        idempotency_key="roundtrip-reservation",
        actor="Sol",
        rationale="Round-trip export graph",
    )
    exporter = LabExportService(db_session)
    packet = await exporter.export_planning_workspace()
    before = json.dumps(
        packet,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    result = await exporter.import_workspace(packet)
    after_packet = await exporter.export_planning_workspace()
    after = json.dumps(
        after_packet,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert result.inserted == 0
    assert result.skipped == sum(
        len(rows) for rows in packet["tables"].values()
    )
    assert after == before
    assert json.loads(after) == packet


@pytest.mark.asyncio
async def test_v1_packet_imports_without_inventing_planning_authority(
    db_session,
):
    packet = {
        "format_revision": "lab-export-v1",
        "tables": {name: [] for name in V1_TABLE_ORDER},
    }
    result = await LabExportService(db_session).import_workspace(packet)
    assert result.inserted == 0
    assert result.skipped == 0
    assert await _planning_row_count(db_session) == 0
