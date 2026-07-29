"""Queries for the append-oriented physical execution lifecycle."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lab import LabBottleMeasurement
from app.models.lab_execution import (
    LabBottleActionCommit,
    LabBottleActionConfirmation,
    LabBottleActionProposal,
)


class LabExecutionRepositoryMixin:
    session: AsyncSession

    async def get_bottle_action_proposal(
        self,
        proposal_id: str,
    ) -> LabBottleActionProposal | None:
        return await self.session.get(LabBottleActionProposal, proposal_id)

    async def bottle_action_proposal_for_idempotency(
        self,
        idempotency_key: str,
    ) -> LabBottleActionProposal | None:
        result = await self.session.execute(
            select(LabBottleActionProposal).where(
                LabBottleActionProposal.idempotency_key == idempotency_key
            )
        )
        return result.scalar_one_or_none()

    async def bottle_action_confirmation(
        self,
        proposal_id: str,
    ) -> LabBottleActionConfirmation | None:
        result = await self.session.execute(
            select(LabBottleActionConfirmation).where(
                LabBottleActionConfirmation.proposal_id == proposal_id
            )
        )
        return result.scalar_one_or_none()

    async def bottle_action_measurement(
        self,
        proposal_id: str,
        quantity_kind: str,
    ) -> LabBottleMeasurement | None:
        result = await self.session.execute(
            select(LabBottleMeasurement).where(
                LabBottleMeasurement.proposal_id == proposal_id,
                LabBottleMeasurement.quantity_kind == quantity_kind,
            )
        )
        return result.scalar_one_or_none()

    async def bottle_action_measurements(
        self,
        proposal_id: str,
    ) -> list[LabBottleMeasurement]:
        result = await self.session.execute(
            select(LabBottleMeasurement)
            .where(LabBottleMeasurement.proposal_id == proposal_id)
            .order_by(
                LabBottleMeasurement.quantity_kind,
                LabBottleMeasurement.id,
            )
        )
        return list(result.scalars())

    async def bottle_action_commit(
        self,
        proposal_id: str,
    ) -> LabBottleActionCommit | None:
        result = await self.session.execute(
            select(LabBottleActionCommit).where(
                LabBottleActionCommit.proposal_id == proposal_id
            )
        )
        return result.scalar_one_or_none()


__all__ = ["LabExecutionRepositoryMixin"]
