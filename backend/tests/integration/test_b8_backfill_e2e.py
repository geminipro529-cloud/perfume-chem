from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from app.models.lab_backfill import (
    BACKFILL_DASHBOARD_DIMENSIONS,
    BACKFILL_REQUIREMENT_TYPES,
    LabBackfillCampaignVersion,
    LabBackfillDashboardCell,
    LabBackfillGapItem,
    LabBackfillMaterialPriority,
    LabBackfillPrioritySignalLink,
)
from app.services.lab_backfill import (
    BackfillConflictError,
    BackfillGapCommand,
    BackfillMaterialCommand,
    BackfillSignalCommand,
    CreateBackfillCampaignCommand,
)
from app.services.lab_service import LabService

NOW = datetime(2026, 7, 31, 3, 0, tzinfo=timezone.utc)
B8_MODELS = (
    LabBackfillCampaignVersion,
    LabBackfillMaterialPriority,
    LabBackfillPrioritySignalLink,
    LabBackfillGapItem,
    LabBackfillDashboardCell,
)


def _missing_gaps(material_id: str) -> tuple[BackfillGapCommand, ...]:
    return tuple(
        BackfillGapCommand(
            requirement_type=requirement,
            state="MISSING",
            evidence_class="UNKNOWN",
            claim_authority_version_id=None,
            applicability_scope={"material_id": material_id},
            missing_requirements=(requirement,),
        )
        for requirement in BACKFILL_REQUIREMENT_TYPES
    )


def _campaign(
    *,
    material_id: str,
    stock_id: str,
    parent_version_id: str | None = None,
) -> CreateBackfillCampaignCommand:
    return CreateBackfillCampaignCommand(
        campaign_key="current-lab-backfill",
        name="Current laboratory backfill",
        purpose="Prioritize unresolved scientific data without promotion.",
        as_of_utc=NOW,
        reviewer_pseudonym="b8-reviewer",
        reviewed_at=NOW,
        parent_version_id=parent_version_id,
        materials=(
            BackfillMaterialCommand(
                material_id=material_id,
                chemical_family=None,
                signals=(
                    BackfillSignalCommand(
                        signal_type="CURRENT_INVENTORY",
                        source_id=stock_id,
                    ),
                ),
                gaps=_missing_gaps(material_id),
            ),
        ),
    )


@pytest.mark.asyncio
async def test_b8_campaign_persists_and_reconstructs_exact_snapshot(
    db_session,
):
    service = LabService(db_session)
    material = await service.create_material("B8 current material")
    stock = await service.create_stock_solution(
        material_id=material.id,
        active_fraction=1.0,
        fraction_basis="mass_fraction",
        initial_mass_g=10.0,
        supplier="B8 fixture",
        lot_number="B8-LOT",
    )

    campaign = await service.create_backfill_campaign(
        _campaign(material_id=material.id, stock_id=stock.id)
    )

    assert campaign.version_number == 1
    assert campaign.parent_version_id is None
    assert campaign.material_count == 1
    assert campaign.signal_count == 1
    assert campaign.gap_count == len(BACKFILL_REQUIREMENT_TYPES)
    assert campaign.missing_count == len(BACKFILL_REQUIREMENT_TYPES)
    assert campaign.release_authority is False

    priorities = await service.repository.backfill_material_priorities(
        campaign.id
    )
    assert len(priorities) == 1
    assert priorities[0].material_id == material.id
    assert priorities[0].rank == 1
    assert priorities[0].primary_priority_class == "CURRENT_INVENTORY"

    signals = await service.repository.backfill_priority_signals(
        priorities[0].id
    )
    assert len(signals) == 1
    assert signals[0].signal_type == "CURRENT_INVENTORY"
    assert signals[0].stock_solution_id == stock.id
    assert signals[0].signal_value_json["positive_balance"] is True

    gaps = await service.repository.backfill_gap_items(priorities[0].id)
    assert {gap.requirement_type for gap in gaps} == set(
        BACKFILL_REQUIREMENT_TYPES
    )
    assert {gap.state for gap in gaps} == {"MISSING"}

    dashboard = await service.repository.backfill_dashboard_cells(campaign.id)
    assert {cell.dimension for cell in dashboard} == set(
        BACKFILL_DASHBOARD_DIMENSIONS
    )
    assert all(
        cell.requirements_total
        == cell.accepted_exact_count
        + cell.accepted_scoped_count
        + cell.weak_count
        + cell.conflicted_count
        + cell.unknown_count
        + cell.missing_count
        + cell.not_applicable_count
        for cell in dashboard
    )

    reconstructed = await service.reconstruct_backfill_campaign(campaign.id)
    assert reconstructed["integrity_verified"] is True
    assert reconstructed["content_sha256"] == campaign.content_sha256
    assert reconstructed["materials"][0]["material_id"] == material.id
    assert reconstructed["materials"][0]["rank"] == 1
    assert reconstructed["materials"][0]["signals"][0]["source_id"] == stock.id
    assert "aggregate_coverage_score" not in reconstructed


@pytest.mark.asyncio
async def test_b8_rejects_cross_material_inventory_and_rolls_back_atomically(
    db_session,
):
    service = LabService(db_session)
    source_material = await service.create_material("B8 stock owner")
    target_material = await service.create_material("B8 wrong target")
    stock = await service.create_stock_solution(
        material_id=source_material.id,
        active_fraction=1.0,
        fraction_basis="mass_fraction",
        initial_mass_g=1.0,
    )

    with pytest.raises(BackfillConflictError) as error:
        await service.create_backfill_campaign(
            _campaign(material_id=target_material.id, stock_id=stock.id)
        )
    assert error.value.code == "BACKFILL_SIGNAL_MATERIAL_MISMATCH"

    for model in B8_MODELS:
        assert (
            await db_session.scalar(select(func.count()).select_from(model))
            == 0
        )


@pytest.mark.asyncio
async def test_b8_revision_requires_latest_parent_and_preserves_chain(
    db_session,
):
    service = LabService(db_session)
    material = await service.create_material("B8 revision material")
    stock = await service.create_stock_solution(
        material_id=material.id,
        active_fraction=1.0,
        fraction_basis="mass_fraction",
        initial_mass_g=2.0,
    )
    root = await service.create_backfill_campaign(
        _campaign(material_id=material.id, stock_id=stock.id)
    )
    revision = await service.create_backfill_campaign(
        _campaign(
            material_id=material.id,
            stock_id=stock.id,
            parent_version_id=root.id,
        )
    )

    assert revision.version_number == 2
    assert revision.parent_version_id == root.id
    assert revision.parent_sha256 == root.content_sha256

    with pytest.raises(BackfillConflictError) as error:
        await service.create_backfill_campaign(
            _campaign(
                material_id=material.id,
                stock_id=stock.id,
                parent_version_id=root.id,
            )
        )
    assert error.value.code == "BACKFILL_PARENT_NOT_LATEST"
