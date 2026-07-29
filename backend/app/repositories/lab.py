"""Persistence-only repository for canonical laboratory records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lab import (
    LabApplication,
    LabBottle,
    LabBottleEvent,
    LabBottleEventEffect,
    LabExperiment,
    LabFormula,
    LabFormulaComponent,
    LabFormulaVersion,
    LabInventoryMovement,
    LabMaterial,
    LabPrediction,
    LabRestriction,
    LabSample,
    LabStockSolution,
)
from app.repositories.lab_planning import LabPlanningRepositoryMixin
from app.repositories.lab_science import LabScienceRepositoryMixin

RecordT = TypeVar("RecordT")


@dataclass(frozen=True, slots=True)
class BottleLedgerState:
    bottle_id: str
    stream_sequence: int
    total_mass_g: float
    stock_masses_g: dict[str, float]


class LabRepository(LabScienceRepositoryMixin, LabPlanningRepositoryMixin):
    """SQLAlchemy queries without transaction ownership or scientific arithmetic."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, record: RecordT) -> RecordT:
        self.session.add(record)
        await self.session.flush()
        return record

    async def get_material(self, material_id: str) -> LabMaterial | None:
        return await self.session.get(LabMaterial, material_id)

    async def get_restriction(
        self,
        restriction_id: str,
    ) -> LabRestriction | None:
        return await self.session.get(LabRestriction, restriction_id)

    async def get_stock(self, stock_id: str) -> LabStockSolution | None:
        return await self.session.get(LabStockSolution, stock_id)

    async def get_bottle(self, bottle_id: str) -> LabBottle | None:
        return await self.session.get(LabBottle, bottle_id)

    async def get_formula(self, formula_id: str) -> LabFormula | None:
        return await self.session.get(LabFormula, formula_id)

    async def get_formula_version(self, version_id: str) -> LabFormulaVersion | None:
        return await self.session.get(LabFormulaVersion, version_id)

    async def formula_components(self, version_id: str) -> list[LabFormulaComponent]:
        result = await self.session.execute(
            select(LabFormulaComponent)
            .where(LabFormulaComponent.formula_version_id == version_id)
            .order_by(LabFormulaComponent.position)
        )
        return list(result.scalars())

    async def get_experiment(self, experiment_id: str) -> LabExperiment | None:
        return await self.session.get(LabExperiment, experiment_id)

    async def get_sample(self, sample_id: str) -> LabSample | None:
        return await self.session.get(LabSample, sample_id)

    async def get_application(self, application_id: str) -> LabApplication | None:
        return await self.session.get(LabApplication, application_id)

    async def get_prediction(self, prediction_id: str) -> LabPrediction | None:
        return await self.session.get(LabPrediction, prediction_id)

    async def next_formula_version(self, formula_id: str) -> int:
        result = await self.session.execute(
            select(func.max(LabFormulaVersion.version_number)).where(
                LabFormulaVersion.formula_id == formula_id
            )
        )
        return int(result.scalar_one_or_none() or 0) + 1

    async def event_for_command(
        self,
        bottle_id: str,
        command_id: str,
    ) -> LabBottleEvent | None:
        result = await self.session.execute(
            select(LabBottleEvent).where(
                LabBottleEvent.bottle_id == bottle_id,
                LabBottleEvent.command_id == command_id,
            )
        )
        return result.scalar_one_or_none()

    async def latest_sequence(self, bottle_id: str) -> int:
        result = await self.session.execute(
            select(func.max(LabBottleEvent.stream_sequence)).where(
                LabBottleEvent.bottle_id == bottle_id
            )
        )
        return int(result.scalar_one_or_none() or 0)

    async def get_event(self, event_id: str) -> LabBottleEvent | None:
        return await self.session.get(LabBottleEvent, event_id)

    async def events_for_transaction(self, transaction_id: str) -> list[LabBottleEvent]:
        result = await self.session.execute(
            select(LabBottleEvent)
            .where(LabBottleEvent.transaction_id == transaction_id)
            .order_by(LabBottleEvent.bottle_id, LabBottleEvent.stream_sequence)
        )
        return list(result.scalars())

    async def correction_for_event(self, event_id: str) -> LabBottleEvent | None:
        result = await self.session.execute(
            select(LabBottleEvent).where(
                LabBottleEvent.correction_of_event_id == event_id
            )
        )
        return result.scalar_one_or_none()

    async def effects_for_event(self, event_id: str) -> list[LabBottleEventEffect]:
        result = await self.session.execute(
            select(LabBottleEventEffect).where(
                LabBottleEventEffect.event_id == event_id
            )
        )
        return list(result.scalars())

    async def inventory_movement_for_effect(
        self,
        effect_id: str,
    ) -> LabInventoryMovement | None:
        result = await self.session.execute(
            select(LabInventoryMovement).where(
                LabInventoryMovement.event_effect_id == effect_id
            )
        )
        return result.scalar_one_or_none()

    async def stock_balance_g(self, stock_id: str) -> float:
        stock = await self.get_stock(stock_id)
        if stock is None:
            raise KeyError(f"Unknown stock solution: {stock_id}")
        result = await self.session.execute(
            select(func.coalesce(func.sum(LabInventoryMovement.mass_delta_g), 0.0)).where(
                LabInventoryMovement.stock_solution_id == stock_id
            )
        )
        return float(stock.initial_mass_g) + float(result.scalar_one())

    async def reconstruct_bottle(self, bottle_id: str) -> BottleLedgerState:
        if await self.get_bottle(bottle_id) is None:
            raise KeyError(f"Unknown bottle: {bottle_id}")
        sequence = await self.latest_sequence(bottle_id)
        total_result = await self.session.execute(
            select(func.coalesce(func.sum(LabBottleEventEffect.mass_delta_g), 0.0)).where(
                LabBottleEventEffect.bottle_id == bottle_id
            )
        )
        stock_result = await self.session.execute(
            select(
                LabBottleEventEffect.stock_solution_id,
                func.sum(LabBottleEventEffect.mass_delta_g),
            )
            .where(
                LabBottleEventEffect.bottle_id == bottle_id,
                LabBottleEventEffect.stock_solution_id.is_not(None),
            )
            .group_by(LabBottleEventEffect.stock_solution_id)
        )
        stock_masses = {
            str(stock_id): float(mass_g)
            for stock_id, mass_g in stock_result
            if abs(float(mass_g)) > 1e-12
        }
        return BottleLedgerState(
            bottle_id=bottle_id,
            stream_sequence=sequence,
            total_mass_g=float(total_result.scalar_one()),
            stock_masses_g=stock_masses,
        )


__all__ = ["BottleLedgerState", "LabRepository"]
