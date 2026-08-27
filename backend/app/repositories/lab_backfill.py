"""Persistence-only queries for B8 prioritized backfill campaigns."""

from __future__ import annotations

from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lab import LabFormulaComponent
from app.models.lab_analytical import LabAnalyticalSequenceEntry
from app.models.lab_backfill import (
    LabBackfillCampaignVersion,
    LabBackfillDashboardCell,
    LabBackfillGapItem,
    LabBackfillMaterialPriority,
    LabBackfillPrioritySignalLink,
)
from app.models.lab_regulatory import LabRegulatoryCompositionEntry


class LabBackfillRepositoryMixin:
    session: AsyncSession

    async def get_backfill_campaign_version(
        self,
        version_id: str,
    ) -> LabBackfillCampaignVersion | None:
        return await self.session.get(LabBackfillCampaignVersion, version_id)

    async def latest_backfill_campaign_version(
        self,
        campaign_key: str,
    ) -> LabBackfillCampaignVersion | None:
        return cast(
            LabBackfillCampaignVersion | None,
            await self.session.scalar(
                select(LabBackfillCampaignVersion)
                .where(
                    LabBackfillCampaignVersion.campaign_key == campaign_key
                )
                .order_by(
                    LabBackfillCampaignVersion.version_number.desc(),
                    LabBackfillCampaignVersion.id,
                )
                .limit(1)
            ),
        )

    async def backfill_campaign_by_hash(
        self,
        content_sha256: str,
    ) -> LabBackfillCampaignVersion | None:
        return cast(
            LabBackfillCampaignVersion | None,
            await self.session.scalar(
                select(LabBackfillCampaignVersion).where(
                    LabBackfillCampaignVersion.content_sha256
                    == content_sha256
                )
            ),
        )

    async def backfill_material_priorities(
        self,
        campaign_version_id: str,
    ) -> list[LabBackfillMaterialPriority]:
        result = await self.session.scalars(
            select(LabBackfillMaterialPriority)
            .where(
                LabBackfillMaterialPriority.campaign_version_id
                == campaign_version_id
            )
            .order_by(
                LabBackfillMaterialPriority.rank,
                LabBackfillMaterialPriority.material_id,
                LabBackfillMaterialPriority.id,
            )
        )
        return list(result)

    async def backfill_priority_signals(
        self,
        material_priority_id: str,
    ) -> list[LabBackfillPrioritySignalLink]:
        result = await self.session.scalars(
            select(LabBackfillPrioritySignalLink)
            .where(
                LabBackfillPrioritySignalLink.material_priority_id
                == material_priority_id
            )
            .order_by(
                LabBackfillPrioritySignalLink.position,
                LabBackfillPrioritySignalLink.signal_type,
                LabBackfillPrioritySignalLink.id,
            )
        )
        return list(result)

    async def backfill_gap_items(
        self,
        material_priority_id: str,
    ) -> list[LabBackfillGapItem]:
        result = await self.session.scalars(
            select(LabBackfillGapItem)
            .where(
                LabBackfillGapItem.material_priority_id
                == material_priority_id
            )
            .order_by(
                LabBackfillGapItem.position,
                LabBackfillGapItem.requirement_type,
                LabBackfillGapItem.id,
            )
        )
        return list(result)

    async def backfill_dashboard_cells(
        self,
        campaign_version_id: str,
    ) -> list[LabBackfillDashboardCell]:
        result = await self.session.scalars(
            select(LabBackfillDashboardCell)
            .where(
                LabBackfillDashboardCell.campaign_version_id
                == campaign_version_id
            )
            .order_by(
                LabBackfillDashboardCell.dimension,
                LabBackfillDashboardCell.dimension_key,
                LabBackfillDashboardCell.id,
            )
        )
        return list(result)

    async def get_formula_component(
        self,
        component_id: str,
    ) -> LabFormulaComponent | None:
        return await self.session.get(LabFormulaComponent, component_id)

    async def get_analytical_sequence_entry(
        self,
        entry_id: str,
    ) -> LabAnalyticalSequenceEntry | None:
        return await self.session.get(LabAnalyticalSequenceEntry, entry_id)

    async def get_regulatory_composition_entry(
        self,
        entry_id: str,
    ) -> LabRegulatoryCompositionEntry | None:
        return await self.session.get(
            LabRegulatoryCompositionEntry,
            entry_id,
        )


__all__ = ["LabBackfillRepositoryMixin"]
