"""Deterministic reads for append-only B2 property authority records."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models.lab_properties import (
    LabPropertyConflictMember,
    LabPropertyConflictSet,
    LabPropertyObservation,
    LabSelectedAssertion,
    LabSelectedAssertionCandidate,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class LabPropertyRepositoryMixin:
    """B2 property reads; transaction ownership remains in ``LabService``."""

    if TYPE_CHECKING:
        session: AsyncSession

    async def get_property_observation(
        self,
        observation_id: str,
    ) -> LabPropertyObservation | None:
        return await self.session.get(LabPropertyObservation, observation_id)

    async def property_observation_by_hash(
        self,
        content_sha256: str,
    ) -> LabPropertyObservation | None:
        result = await self.session.execute(
            select(LabPropertyObservation)
            .where(
                LabPropertyObservation.content_sha256 == content_sha256
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def property_observations_by_ids(
        self,
        observation_ids: tuple[str, ...],
    ) -> list[LabPropertyObservation]:
        if not observation_ids:
            return []
        result = await self.session.execute(
            select(LabPropertyObservation).where(
                LabPropertyObservation.id.in_(observation_ids)
            )
        )
        by_id = {record.id: record for record in result.scalars()}
        return [
            by_id[observation_id]
            for observation_id in observation_ids
            if observation_id in by_id
        ]

    async def get_property_conflict_set(
        self,
        conflict_set_id: str,
    ) -> LabPropertyConflictSet | None:
        return await self.session.get(LabPropertyConflictSet, conflict_set_id)

    async def property_conflict_by_hash(
        self,
        content_sha256: str,
    ) -> LabPropertyConflictSet | None:
        result = await self.session.execute(
            select(LabPropertyConflictSet)
            .where(LabPropertyConflictSet.content_sha256 == content_sha256)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def property_conflict_members(
        self,
        conflict_set_id: str,
    ) -> list[LabPropertyConflictMember]:
        result = await self.session.execute(
            select(LabPropertyConflictMember)
            .where(
                LabPropertyConflictMember.conflict_set_id == conflict_set_id
            )
            .order_by(
                LabPropertyConflictMember.observation_id,
                LabPropertyConflictMember.id,
            )
        )
        return list(result.scalars())

    async def get_selected_assertion(
        self,
        assertion_id: str,
    ) -> LabSelectedAssertion | None:
        return await self.session.get(LabSelectedAssertion, assertion_id)

    async def selected_assertion_by_hash(
        self,
        content_sha256: str,
    ) -> LabSelectedAssertion | None:
        result = await self.session.execute(
            select(LabSelectedAssertion)
            .where(LabSelectedAssertion.content_sha256 == content_sha256)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def selected_assertion_candidates(
        self,
        assertion_id: str,
    ) -> list[LabSelectedAssertionCandidate]:
        result = await self.session.execute(
            select(LabSelectedAssertionCandidate)
            .where(
                LabSelectedAssertionCandidate.selected_assertion_id
                == assertion_id
            )
            .order_by(
                LabSelectedAssertionCandidate.observation_id,
                LabSelectedAssertionCandidate.id,
            )
        )
        return list(result.scalars())


__all__ = ["LabPropertyRepositoryMixin"]
