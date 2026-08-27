"""Deterministic read queries for immutable A2 planning records."""

from __future__ import annotations

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lab import LabEvidenceRecord
from app.models.lab_planning import (
    LabAcceptedTargetVersion,
    LabBuildPlanLine,
    LabBuildPlanVersion,
    LabFormulaVersionEdge,
    LabInventoryMappingVersion,
    LabInventoryReservationEvent,
    LabTargetHypothesisVersion,
    LabTargetLine,
)


class LabPlanningRepositoryMixin:
    """Planning reads only; transaction ownership remains in ``LabService``."""

    session: AsyncSession

    async def get_evidence_record(
        self,
        evidence_id: str,
    ) -> LabEvidenceRecord | None:
        return await self.session.get(LabEvidenceRecord, evidence_id)

    async def get_target_version(
        self,
        version_id: str,
    ) -> LabTargetHypothesisVersion | None:
        return await self.session.get(LabTargetHypothesisVersion, version_id)

    async def latest_target_version(
        self,
        target_id: str,
    ) -> LabTargetHypothesisVersion | None:
        result = await self.session.execute(
            select(LabTargetHypothesisVersion)
            .where(LabTargetHypothesisVersion.target_id == target_id)
            .order_by(
                LabTargetHypothesisVersion.version_number.desc(),
                LabTargetHypothesisVersion.id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_target_line(self, line_id: str) -> LabTargetLine | None:
        return await self.session.get(LabTargetLine, line_id)

    async def target_lines(self, version_id: str) -> list[LabTargetLine]:
        result = await self.session.execute(
            select(LabTargetLine)
            .where(LabTargetLine.target_hypothesis_version_id == version_id)
            .order_by(LabTargetLine.position, LabTargetLine.line_id, LabTargetLine.id)
        )
        return list(result.scalars())

    async def get_acceptance(
        self,
        acceptance_id: str,
    ) -> LabAcceptedTargetVersion | None:
        return await self.session.get(LabAcceptedTargetVersion, acceptance_id)

    async def acceptance_for_target_version(
        self,
        target_version_id: str,
    ) -> LabAcceptedTargetVersion | None:
        result = await self.session.execute(
            select(LabAcceptedTargetVersion).where(
                LabAcceptedTargetVersion.target_hypothesis_version_id
                == target_version_id
            )
        )
        return result.scalar_one_or_none()

    async def formula_parent_edges(
        self,
        child_version_id: str,
    ) -> list[LabFormulaVersionEdge]:
        result = await self.session.execute(
            select(LabFormulaVersionEdge)
            .where(LabFormulaVersionEdge.child_version_id == child_version_id)
            .order_by(
                LabFormulaVersionEdge.parent_version_id,
                LabFormulaVersionEdge.id,
            )
        )
        return list(result.scalars())

    async def formula_has_path(
        self,
        start_version_id: str,
        target_version_id: str,
    ) -> bool:
        pending = [start_version_id]
        visited: set[str] = set()
        while pending:
            current = pending.pop()
            if current == target_version_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            pending.extend(
                edge.parent_version_id
                for edge in await self.formula_parent_edges(current)
            )
        return False

    async def get_mapping_version(
        self,
        version_id: str,
    ) -> LabInventoryMappingVersion | None:
        return await self.session.get(LabInventoryMappingVersion, version_id)

    async def latest_mapping_version(
        self,
        mapping_id: str,
    ) -> LabInventoryMappingVersion | None:
        result = await self.session.execute(
            select(LabInventoryMappingVersion)
            .where(LabInventoryMappingVersion.mapping_id == mapping_id)
            .order_by(
                LabInventoryMappingVersion.version_number.desc(),
                LabInventoryMappingVersion.id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_build_plan_version(
        self,
        version_id: str,
    ) -> LabBuildPlanVersion | None:
        return await self.session.get(LabBuildPlanVersion, version_id)

    async def latest_build_plan_version(
        self,
        plan_id: str,
    ) -> LabBuildPlanVersion | None:
        result = await self.session.execute(
            select(LabBuildPlanVersion)
            .where(LabBuildPlanVersion.plan_id == plan_id)
            .order_by(
                LabBuildPlanVersion.version_number.desc(),
                LabBuildPlanVersion.id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_build_plan_line(
        self,
        line_id: str,
    ) -> LabBuildPlanLine | None:
        return await self.session.get(LabBuildPlanLine, line_id)

    async def build_plan_lines(self, version_id: str) -> list[LabBuildPlanLine]:
        result = await self.session.execute(
            select(LabBuildPlanLine)
            .where(LabBuildPlanLine.build_plan_version_id == version_id)
            .order_by(
                LabBuildPlanLine.position,
                LabBuildPlanLine.line_id,
                LabBuildPlanLine.id,
            )
        )
        return list(result.scalars())

    async def reservation_events(
        self,
        reservation_id: str,
    ) -> list[LabInventoryReservationEvent]:
        result = await self.session.execute(
            select(LabInventoryReservationEvent)
            .where(
                LabInventoryReservationEvent.reservation_id == reservation_id
            )
            .order_by(
                LabInventoryReservationEvent.sequence,
                LabInventoryReservationEvent.id,
            )
        )
        return list(result.scalars())

    async def latest_reservation_event(
        self,
        reservation_id: str,
    ) -> LabInventoryReservationEvent | None:
        result = await self.session.execute(
            select(LabInventoryReservationEvent)
            .where(
                LabInventoryReservationEvent.reservation_id == reservation_id
            )
            .order_by(
                LabInventoryReservationEvent.sequence.desc(),
                LabInventoryReservationEvent.id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def reservation_event_for_idempotency(
        self,
        idempotency_key: str,
    ) -> LabInventoryReservationEvent | None:
        result = await self.session.execute(
            select(LabInventoryReservationEvent).where(
                LabInventoryReservationEvent.idempotency_key == idempotency_key
            )
        )
        return result.scalar_one_or_none()

    async def active_reserved_mass_g(self, stock_solution_id: str) -> float:
        latest = (
            select(
                LabInventoryReservationEvent.reservation_id.label(
                    "reservation_id"
                ),
                func.max(LabInventoryReservationEvent.sequence).label(
                    "latest_sequence"
                ),
            )
            .group_by(LabInventoryReservationEvent.reservation_id)
            .subquery()
        )
        result = await self.session.execute(
            select(
                func.coalesce(
                    func.sum(LabInventoryReservationEvent.reserved_mass_g),
                    0.0,
                )
            )
            .join(
                latest,
                and_(
                    LabInventoryReservationEvent.reservation_id
                    == latest.c.reservation_id,
                    LabInventoryReservationEvent.sequence
                    == latest.c.latest_sequence,
                ),
            )
            .where(
                LabInventoryReservationEvent.stock_solution_id
                == stock_solution_id,
                LabInventoryReservationEvent.state == "RESERVED",
            )
        )
        return float(result.scalar_one())

    async def active_reserved_build_line_ids(
        self,
        build_plan_version_id: str,
    ) -> set[str]:
        latest = (
            select(
                LabInventoryReservationEvent.reservation_id.label(
                    "reservation_id"
                ),
                func.max(LabInventoryReservationEvent.sequence).label(
                    "latest_sequence"
                ),
            )
            .group_by(LabInventoryReservationEvent.reservation_id)
            .subquery()
        )
        result = await self.session.execute(
            select(LabInventoryReservationEvent.build_plan_line_id)
            .join(
                latest,
                and_(
                    LabInventoryReservationEvent.reservation_id
                    == latest.c.reservation_id,
                    LabInventoryReservationEvent.sequence
                    == latest.c.latest_sequence,
                ),
            )
            .where(
                LabInventoryReservationEvent.build_plan_version_id
                == build_plan_version_id,
                LabInventoryReservationEvent.state == "RESERVED",
            )
            .order_by(LabInventoryReservationEvent.build_plan_line_id)
        )
        return {str(line_id) for line_id in result.scalars()}


__all__ = ["LabPlanningRepositoryMixin"]
