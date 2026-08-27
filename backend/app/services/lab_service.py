"""Transactional application service for immutable laboratory history."""

from __future__ import annotations

import asyncio
import threading
import weakref
from collections.abc import Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from math import isfinite
from uuid import uuid4

from sqlalchemy import text
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
    LabMaterialAlias,
    LabObservation,
    LabOutcome,
    LabPairwiseComparison,
    LabPrediction,
    LabSample,
    LabStockSolution,
)
from app.repositories.lab import BottleLedgerState, LabRepository
from app.services.lab_analytical import LabAnalyticalAuthorityServiceMixin
from app.services.lab_backfill import LabBackfillServiceMixin
from app.services.lab_claims import LabClaimAuthorityServiceMixin
from app.services.lab_execution import LabExecutionServiceMixin
from app.services.lab_planning import LabPlanningServiceMixin
from app.services.lab_properties import LabPropertyServiceMixin
from app.services.lab_regulatory import LabRegulatoryAuthorityServiceMixin
from app.services.lab_rules import LabRuleServiceMixin
from app.services.lab_science import LabScienceServiceMixin
from app.services.lab_sources import LabSourceServiceMixin
from app.services.lab_thresholds import LabThresholdServiceMixin


@dataclass(frozen=True, slots=True)
class FormulaComponentInput:
    """One explicitly based stock dose in an immutable formula version."""

    stock_solution_id: str
    requested_mass_g: float
    requested_volume_ul: float | None = None
    role: str | None = None
    unit: str = "g"

    def __post_init__(self) -> None:
        stock_solution_id = self.stock_solution_id.strip()
        mass = float(self.requested_mass_g)
        volume = (
            float(self.requested_volume_ul)
            if self.requested_volume_ul is not None
            else None
        )
        role = self.role.strip() if self.role else None
        if not stock_solution_id:
            raise ValueError("stock_solution_id must not be empty")
        if not isfinite(mass) or mass <= 0:
            raise ValueError("requested_mass_g must be finite and greater than zero")
        if volume is not None and (not isfinite(volume) or volume <= 0):
            raise ValueError("requested_volume_ul must be finite and greater than zero")
        if self.unit != "g":
            raise ValueError("formula component unit must be g")
        object.__setattr__(self, "stock_solution_id", stock_solution_id)
        object.__setattr__(self, "requested_mass_g", mass)
        object.__setattr__(self, "requested_volume_ul", volume)
        object.__setattr__(self, "role", role)


class LabTransactionError(ValueError):
    """Base error for rejected laboratory commands."""


class StaleBottleStreamError(LabTransactionError):
    """Raised when a command was prepared from an older bottle state."""


class InsufficientStockError(LabTransactionError):
    """Raised when a stock movement would make inventory negative."""


class InsufficientBottleMassError(LabTransactionError):
    """Raised when a transfer exceeds reconstructed source mass."""


class IdempotencyConflictError(LabTransactionError):
    """Raised when a command identifier is reused for a different request."""


class AlreadyCompensatedError(LabTransactionError):
    """Raised when immutable history already contains a correction."""


class ConcurrentWriteError(LabTransactionError):
    """Raised when a write loses a database-level optimistic race."""


_LAB_WRITE_LOCKS: weakref.WeakKeyDictionary[
    asyncio.AbstractEventLoop,
    asyncio.Lock,
] = weakref.WeakKeyDictionary()
_LAB_WRITE_LOCKS_GUARD = threading.Lock()


def _lab_write_lock() -> asyncio.Lock:
    """Return the write lock owned by the current event loop."""

    loop = asyncio.get_running_loop()
    with _LAB_WRITE_LOCKS_GUARD:
        lock = _LAB_WRITE_LOCKS.get(loop)
        if lock is None:
            lock = asyncio.Lock()
            _LAB_WRITE_LOCKS[loop] = lock
        return lock


class LabService(
    LabExecutionServiceMixin,
    LabBackfillServiceMixin,
    LabRuleServiceMixin,
    LabThresholdServiceMixin,
    LabPropertyServiceMixin,
    LabRegulatoryAuthorityServiceMixin,
    LabSourceServiceMixin,
    LabAnalyticalAuthorityServiceMixin,
    LabClaimAuthorityServiceMixin,
    LabScienceServiceMixin,
    LabPlanningServiceMixin,
):
    """Own transactions while delegating persistence to ``LabRepository``."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = LabRepository(session)

    @asynccontextmanager
    async def _transaction(self):
        """Join caller transactions; otherwise own one serialized write unit."""

        write_lock = _lab_write_lock()
        await write_lock.acquire()
        owns_transaction = not self.session.in_transaction()
        try:
            if owns_transaction:
                bind = self.session.get_bind()
                if bind.dialect.name == "sqlite":
                    await self.session.execute(text("BEGIN IMMEDIATE"))
                else:
                    await self.session.begin()
            try:
                yield
            except BaseException:
                if owns_transaction:
                    await self.session.rollback()
                raise
            else:
                if owns_transaction:
                    await self.session.commit()
        finally:
            write_lock.release()

    async def create_material(self, canonical_name: str) -> LabMaterial:
        name = canonical_name.strip()
        if not name:
            raise ValueError("canonical_name must not be empty")
        async with self._transaction():
            return await self.repository.add(LabMaterial(canonical_name=name))

    async def create_material_alias(
        self,
        material_id: str,
        alias: str,
    ) -> LabMaterialAlias:
        alias_text = alias.strip()
        if not alias_text:
            raise ValueError("alias must not be empty")
        async with self._transaction():
            if await self.repository.get_material(material_id) is None:
                raise KeyError(f"Unknown material: {material_id}")
            return await self.repository.add(
                LabMaterialAlias(
                    material_id=material_id,
                    alias=alias_text,
                    normalized_alias=alias_text.lower(),
                )
            )

    async def create_stock_solution(
        self,
        *,
        material_id: str,
        active_fraction: float,
        fraction_basis: str,
        initial_mass_g: float,
        density_g_ml: float | None = None,
        supplier: str | None = None,
        lot_number: str | None = None,
        solvent_name: str | None = None,
    ) -> LabStockSolution:
        if not 0 < active_fraction <= 1:
            raise ValueError("active_fraction must be greater than zero and at most one")
        if fraction_basis not in {"mass_fraction", "volume_fraction", "amount_fraction"}:
            raise ValueError("fraction_basis must be explicit")
        if initial_mass_g < 0:
            raise ValueError("initial_mass_g must be nonnegative")
        if density_g_ml is not None and density_g_ml <= 0:
            raise ValueError("density_g_ml must be greater than zero")
        async with self._transaction():
            if await self.repository.get_material(material_id) is None:
                raise KeyError(f"Unknown material: {material_id}")
            return await self.repository.add(
                LabStockSolution(
                    material_id=material_id,
                    active_fraction=active_fraction,
                    fraction_basis=fraction_basis,
                    initial_mass_g=initial_mass_g,
                    remaining_mass_g=initial_mass_g,
                    density_g_ml=density_g_ml,
                    supplier=supplier,
                    lot_number=lot_number,
                    solvent_name=solvent_name,
                )
            )

    async def create_formula(self, name: str) -> LabFormula:
        name = name.strip()
        if not name:
            raise ValueError("formula name must not be empty")
        async with self._transaction():
            return await self.repository.add(LabFormula(name=name))

    async def add_formula_version(
        self,
        formula_id: str,
        *,
        brief: dict,
        constraints: dict,
        concentration_fraction: float | None = None,
        concentration_basis: str | None = None,
        source: dict | None = None,
        components: Sequence[FormulaComponentInput] = (),
    ) -> LabFormulaVersion:
        component_rows = tuple(components)
        stock_ids = [component.stock_solution_id for component in component_rows]
        if len(stock_ids) != len(set(stock_ids)):
            raise ValueError("formula components must not repeat a stock solution")
        async with self._transaction():
            if await self.repository.get_formula(formula_id) is None:
                raise KeyError(f"Unknown formula: {formula_id}")
            for component in component_rows:
                if await self.repository.get_stock(component.stock_solution_id) is None:
                    raise KeyError(
                        f"Unknown stock solution: {component.stock_solution_id}"
                    )
            version = LabFormulaVersion(
                formula_id=formula_id,
                version_number=await self.repository.next_formula_version(formula_id),
                brief_json=dict(brief),
                constraints_json=dict(constraints),
                concentration_fraction=concentration_fraction,
                concentration_basis=concentration_basis,
                source_json=dict(source or {}),
            )
            await self.repository.add(version)
            for position, component in enumerate(component_rows, start=1):
                await self.repository.add(
                    LabFormulaComponent(
                        formula_version_id=version.id,
                        stock_solution_id=component.stock_solution_id,
                        position=position,
                        requested_mass_g=component.requested_mass_g,
                        requested_volume_ul=component.requested_volume_ul,
                        role=component.role,
                        unit=component.unit,
                    )
                )
            return version

    async def update_formula_version(self, _version_id: str, **_changes) -> None:
        raise ValueError("formula versions are immutable; create a new version")

    async def create_bottle(
        self,
        label: str,
        *,
        initial_mass_g: float = 0.0,
    ) -> LabBottle:
        if initial_mass_g < 0:
            raise ValueError("initial_mass_g must be nonnegative")
        async with self._transaction():
            bottle = await self.repository.add(LabBottle(label=label.strip()))
            event = await self.repository.add(
                LabBottleEvent(
                    bottle_id=bottle.id,
                    stream_sequence=1,
                    expected_sequence=0,
                    command_id=f"create-{bottle.id}",
                    transaction_id=str(uuid4()),
                    event_type="create",
                    payload_json={"initial_mass_g": initial_mass_g},
                )
            )
            if initial_mass_g:
                await self.repository.add(
                    LabBottleEventEffect(
                        event_id=event.id,
                        bottle_id=bottle.id,
                        mass_delta_g=initial_mass_g,
                    )
                )
            return bottle

    async def add_stock_to_bottle(
        self,
        *,
        bottle_id: str,
        stock_solution_id: str,
        mass_g: float,
        expected_sequence: int,
        command_id: str,
        measured_volume_ul: float | None = None,
        standard_uncertainty: float | None = None,
        actor: str = "system",
    ) -> LabBottleEvent:
        async with self._transaction():
            return await self._add_stock_to_bottle_in_transaction(
                bottle_id=bottle_id,
                stock_solution_id=stock_solution_id,
                mass_g=mass_g,
                expected_sequence=expected_sequence,
                command_id=command_id,
                measured_volume_ul=measured_volume_ul,
                standard_uncertainty=standard_uncertainty,
                actor=actor,
            )

    async def _add_stock_to_bottle_in_transaction(
        self,
        *,
        bottle_id: str,
        stock_solution_id: str,
        mass_g: float,
        expected_sequence: int,
        command_id: str,
        measured_volume_ul: float | None = None,
        standard_uncertainty: float | None = None,
        actor: str = "system",
        build_plan_line_id: str | None = None,
        reservation_event_id: str | None = None,
        event_type: str = "ADD_MATERIAL",
    ) -> LabBottleEvent:
        """Apply one stock addition inside the caller's canonical transaction."""

        if mass_g <= 0:
            raise ValueError("mass_g must be greater than zero")
        if standard_uncertainty is not None and standard_uncertainty < 0:
            raise ValueError("standard_uncertainty must be nonnegative")
        actor = actor.strip()
        if not actor:
            raise ValueError("actor must not be empty")
        if event_type not in {"ADD_MATERIAL", "ADD_SOLVENT"}:
            raise ValueError(f"unsupported addition event_type: {event_type}")
        token = _command_token("add-stock", command_id)
        request_payload = {
            "stock_solution_id": stock_solution_id,
            "mass_g": mass_g,
            "measured_volume_ul": measured_volume_ul,
            "standard_uncertainty": standard_uncertainty,
            "expected_sequence": expected_sequence,
            "event_type": event_type,
        }
        existing = await self.repository.event_for_command(bottle_id, token)
        if existing is not None:
            if existing.payload_json != request_payload:
                raise IdempotencyConflictError(
                    "command identifier was already used for a different request"
                )
            return existing
        bottle = await self.repository.get_bottle(bottle_id)
        stock = await self.repository.get_stock(stock_solution_id)
        if bottle is None:
            raise KeyError(f"Unknown bottle: {bottle_id}")
        if stock is None:
            raise KeyError(f"Unknown stock solution: {stock_solution_id}")
        if await self.repository.bottle_is_closed(bottle_id):
            raise LabTransactionError("bottle is closed")
        current_sequence = await self.repository.latest_sequence(bottle_id)
        if current_sequence != expected_sequence:
            raise StaleBottleStreamError(
                f"expected sequence {expected_sequence}, current sequence is {current_sequence}"
            )
        available_g = await self.repository.stock_balance_g(stock_solution_id)
        if mass_g > available_g + 1e-12:
            raise InsufficientStockError(
                f"requested {mass_g:g} g but only {available_g:g} g is available"
            )

        event = await self.repository.add(
            LabBottleEvent(
                bottle_id=bottle_id,
                stream_sequence=current_sequence + 1,
                expected_sequence=expected_sequence,
                command_id=token,
                transaction_id=str(uuid4()),
                event_type=event_type,
                payload_json=request_payload,
            )
        )
        effect = await self.repository.add(
            LabBottleEventEffect(
                event_id=event.id,
                bottle_id=bottle_id,
                stock_solution_id=stock_solution_id,
                material_id=stock.material_id,
                mass_delta_g=mass_g,
                measured_volume_ul=measured_volume_ul,
                density_g_ml=stock.density_g_ml,
            )
        )
        await self._append_inventory_movement(
            stock=stock,
            movement_type="CONSUMPTION",
            raw_quantity=mass_g,
            balance_before=available_g,
            balance_after=available_g - mass_g,
            actor=actor,
            transaction_id=event.transaction_id,
            idempotency_key=f"movement:{event.id}",
            reason="bottle_addition",
            mass_delta_g=-mass_g,
            event_effect_id=effect.id,
            bottle_event_id=event.id,
            build_plan_line_id=build_plan_line_id,
            reservation_event_id=reservation_event_id,
            measured_volume_ul=measured_volume_ul,
            standard_uncertainty=standard_uncertainty,
        )
        stock.remaining_mass_g = available_g - mass_g
        return event

    async def add_solvent_to_bottle(
        self,
        *,
        bottle_id: str,
        stock_solution_id: str,
        mass_g: float,
        expected_sequence: int,
        command_id: str,
        measured_volume_ul: float | None = None,
        standard_uncertainty: float | None = None,
        actor: str = "system",
    ) -> LabBottleEvent:
        """Append a solvent addition without classifying it as odorant mass."""

        async with self._transaction():
            return await self._add_stock_to_bottle_in_transaction(
                bottle_id=bottle_id,
                stock_solution_id=stock_solution_id,
                mass_g=mass_g,
                expected_sequence=expected_sequence,
                command_id=command_id,
                measured_volume_ul=measured_volume_ul,
                standard_uncertainty=standard_uncertainty,
                actor=actor,
                event_type="ADD_SOLVENT",
            )

    async def _append_inventory_movement(
        self,
        *,
        stock: LabStockSolution,
        movement_type: str,
        raw_quantity: float,
        balance_before: float,
        balance_after: float,
        actor: str,
        transaction_id: str,
        idempotency_key: str,
        reason: str,
        mass_delta_g: float,
        event_effect_id: str | None = None,
        build_plan_line_id: str | None = None,
        reservation_event_id: str | None = None,
        bottle_event_id: str | None = None,
        admin_cause: str | None = None,
        correction_of_movement_id: str | None = None,
        reversal_of_movement_id: str | None = None,
        measured_volume_ul: float | None = None,
        standard_uncertainty: float | None = None,
    ) -> LabInventoryMovement:
        return await self.repository.add(
            LabInventoryMovement(
                stock_solution_id=stock.id,
                event_effect_id=event_effect_id,
                build_plan_line_id=build_plan_line_id,
                reservation_event_id=reservation_event_id,
                bottle_event_id=bottle_event_id,
                movement_type=movement_type,
                raw_quantity=raw_quantity,
                active_quantity=raw_quantity * stock.active_fraction,
                unit="g",
                basis="mass",
                balance_before=balance_before,
                balance_after=balance_after,
                standard_uncertainty=standard_uncertainty,
                actor=actor,
                transaction_id=transaction_id,
                idempotency_key=idempotency_key,
                admin_cause=admin_cause,
                correction_of_movement_id=correction_of_movement_id,
                reversal_of_movement_id=reversal_of_movement_id,
                mass_delta_g=mass_delta_g,
                measured_volume_ul=measured_volume_ul,
                reason=reason,
            )
        )

    async def _append_bottle_metadata_event(
        self,
        *,
        bottle_id: str,
        event_type: str,
        expected_sequence: int,
        command_id: str,
        actor: str,
        payload: dict,
    ) -> LabBottleEvent:
        actor = actor.strip()
        if not actor:
            raise ValueError("actor must not be empty")
        token = _command_token(event_type.lower(), command_id)
        request_payload = {
            **payload,
            "actor": actor,
            "expected_sequence": expected_sequence,
        }
        async with self._transaction():
            existing = await self.repository.event_for_command(
                bottle_id,
                token,
            )
            if existing is not None:
                if existing.payload_json != request_payload:
                    raise IdempotencyConflictError(
                        "command identifier was already used for a different request"
                    )
                return existing
            if await self.repository.get_bottle(bottle_id) is None:
                raise KeyError(f"Unknown bottle: {bottle_id}")
            current_sequence = await self.repository.latest_sequence(bottle_id)
            if current_sequence != expected_sequence:
                raise StaleBottleStreamError(
                    f"expected sequence {expected_sequence}, "
                    f"current sequence is {current_sequence}"
                )
            if (
                event_type == "CLOSE_BATCH"
                and await self.repository.bottle_is_closed(bottle_id)
            ):
                raise LabTransactionError("bottle is already closed")
            return await self.repository.add(
                LabBottleEvent(
                    bottle_id=bottle_id,
                    stream_sequence=current_sequence + 1,
                    expected_sequence=expected_sequence,
                    command_id=token,
                    transaction_id=str(uuid4()),
                    event_type=event_type,
                    payload_json=request_payload,
                )
            )

    async def tare_bottle(
        self,
        *,
        bottle_id: str,
        tare_mass_g: float,
        expected_sequence: int,
        command_id: str,
        actor: str,
    ) -> LabBottleEvent:
        if tare_mass_g < 0:
            raise ValueError("tare_mass_g must be nonnegative")
        return await self._append_bottle_metadata_event(
            bottle_id=bottle_id,
            event_type="TARE_CONTAINER",
            expected_sequence=expected_sequence,
            command_id=command_id,
            actor=actor,
            payload={"tare_mass_g": tare_mass_g},
        )

    async def close_bottle(
        self,
        *,
        bottle_id: str,
        expected_sequence: int,
        command_id: str,
        actor: str,
    ) -> LabBottleEvent:
        return await self._append_bottle_metadata_event(
            bottle_id=bottle_id,
            event_type="CLOSE_BATCH",
            expected_sequence=expected_sequence,
            command_id=command_id,
            actor=actor,
            payload={},
        )

    async def transfer_between_bottles(
        self,
        *,
        source_bottle_id: str,
        destination_bottle_id: str,
        mass_g: float,
        measured_loss_g: float = 0.0,
        source_expected_sequence: int,
        destination_expected_sequence: int,
        command_id: str,
    ) -> tuple[LabBottleEvent, LabBottleEvent]:
        if source_bottle_id == destination_bottle_id:
            raise ValueError("source and destination bottles must differ")
        if mass_g <= 0:
            raise ValueError("mass_g must be greater than zero")
        if measured_loss_g < 0 or measured_loss_g >= mass_g:
            raise ValueError(
                "measured_loss_g must be nonnegative and less than mass_g"
            )
        source_command = _command_token("transfer-source", command_id)
        destination_command = _command_token("transfer-destination", command_id)
        request_payload = {
            "source_bottle_id": source_bottle_id,
            "destination_bottle_id": destination_bottle_id,
            "mass_g": mass_g,
            "measured_loss_g": measured_loss_g,
            "source_expected_sequence": source_expected_sequence,
            "destination_expected_sequence": destination_expected_sequence,
        }
        async with self._transaction():
            existing_source = await self.repository.event_for_command(
                source_bottle_id, source_command
            )
            existing_destination = await self.repository.event_for_command(
                destination_bottle_id, destination_command
            )
            if existing_source is not None and existing_destination is not None:
                if (
                    existing_source.payload_json != request_payload
                    or existing_destination.payload_json != request_payload
                ):
                    raise IdempotencyConflictError(
                        "command identifier was already used for a different request"
                    )
                return existing_source, existing_destination
            if existing_source is not None or existing_destination is not None:
                raise ConcurrentWriteError("partial transfer command already exists")

            source_sequence = await self.repository.latest_sequence(source_bottle_id)
            destination_sequence = await self.repository.latest_sequence(destination_bottle_id)
            if source_sequence != source_expected_sequence:
                raise StaleBottleStreamError("source bottle stream is stale")
            if destination_sequence != destination_expected_sequence:
                raise StaleBottleStreamError("destination bottle stream is stale")
            if await self.repository.bottle_is_closed(source_bottle_id):
                raise LabTransactionError("source bottle is closed")
            if await self.repository.bottle_is_closed(destination_bottle_id):
                raise LabTransactionError("destination bottle is closed")
            source_state = await self.repository.reconstruct_bottle(source_bottle_id)
            if mass_g > source_state.total_mass_g + 1e-12:
                raise InsufficientBottleMassError("transfer exceeds source bottle mass")

            transaction_id = str(uuid4())
            source_event = await self.repository.add(
                LabBottleEvent(
                    bottle_id=source_bottle_id,
                    stream_sequence=source_sequence + 1,
                    expected_sequence=source_expected_sequence,
                    command_id=source_command,
                    transaction_id=transaction_id,
                    event_type="TRANSFER",
                    payload_json=request_payload,
                )
            )
            destination_event = await self.repository.add(
                LabBottleEvent(
                    bottle_id=destination_bottle_id,
                    stream_sequence=destination_sequence + 1,
                    expected_sequence=destination_expected_sequence,
                    command_id=destination_command,
                    transaction_id=transaction_id,
                    event_type="TRANSFER",
                    payload_json=request_payload,
                )
            )

            transferred_stock_mass = 0.0
            for stock_id, stock_mass in source_state.stock_masses_g.items():
                portion = mass_g * stock_mass / source_state.total_mass_g
                transferred_stock_mass += portion
                stock = await self.repository.get_stock(stock_id)
                material_id = stock.material_id if stock is not None else None
                destination_portion = portion * (
                    (mass_g - measured_loss_g) / mass_g
                )
                await self.repository.add(
                    LabBottleEventEffect(
                        event_id=source_event.id,
                        bottle_id=source_bottle_id,
                        stock_solution_id=stock_id,
                        material_id=material_id,
                        mass_delta_g=-portion,
                    )
                )
                await self.repository.add(
                    LabBottleEventEffect(
                        event_id=destination_event.id,
                        bottle_id=destination_bottle_id,
                        stock_solution_id=stock_id,
                        material_id=material_id,
                        mass_delta_g=destination_portion,
                    )
                )
            unassigned_mass = mass_g - transferred_stock_mass
            if unassigned_mass > 1e-12:
                destination_unassigned = unassigned_mass * (
                    (mass_g - measured_loss_g) / mass_g
                )
                await self.repository.add(
                    LabBottleEventEffect(
                        event_id=source_event.id,
                        bottle_id=source_bottle_id,
                        mass_delta_g=-unassigned_mass,
                    )
                )
                await self.repository.add(
                    LabBottleEventEffect(
                        event_id=destination_event.id,
                        bottle_id=destination_bottle_id,
                        mass_delta_g=destination_unassigned,
                    )
                )
            return source_event, destination_event

    async def compensate_bottle_event(
        self,
        *,
        bottle_id: str,
        event_id: str,
        expected_sequence: int,
        command_id: str,
        actor: str = "system",
    ) -> LabBottleEvent:
        token = _command_token(f"compensate:{event_id}", command_id)
        async with self._transaction():
            existing = await self.repository.event_for_command(bottle_id, token)
            if existing is not None:
                if existing.correction_of_event_id != event_id:
                    raise IdempotencyConflictError(
                        "command identifier was already used for a different request"
                    )
                return existing
            original = await self.repository.get_event(event_id)
            if original is None or original.bottle_id != bottle_id:
                raise KeyError(f"Unknown bottle event: {event_id}")
            if original.event_type in {"compensate", "CORRECT_ENTRY"}:
                raise ValueError("compensating events cannot themselves be compensated")

            originals = (
                await self.repository.events_for_transaction(original.transaction_id)
                if original.event_type
                in {"transfer_out", "transfer_in", "TRANSFER"}
                else [original]
            )
            for item in originals:
                if await self.repository.correction_for_event(item.id) is not None:
                    raise AlreadyCompensatedError(
                        "event transaction is already compensated"
                    )

            current_sequences = {
                item.bottle_id: await self.repository.latest_sequence(item.bottle_id)
                for item in originals
            }
            if current_sequences[bottle_id] != expected_sequence:
                raise StaleBottleStreamError(
                    f"expected sequence {expected_sequence}, current sequence is "
                    f"{current_sequences[bottle_id]}"
                )

            correction_transaction_id = str(uuid4())
            selected_correction: LabBottleEvent | None = None
            for item in originals:
                current_sequence = current_sequences[item.bottle_id]
                correction = await self.repository.add(
                    LabBottleEvent(
                        bottle_id=item.bottle_id,
                        stream_sequence=current_sequence + 1,
                        expected_sequence=current_sequence,
                        command_id=_command_token(f"compensate:{item.id}", command_id),
                        transaction_id=correction_transaction_id,
                        event_type="CORRECT_ENTRY",
                        correction_of_event_id=item.id,
                        payload_json={
                            "correction_of_event_id": item.id,
                            "correction_of_transaction_id": original.transaction_id,
                            "actor": actor,
                        },
                    )
                )
                if item.id == event_id:
                    selected_correction = correction
                await self._reverse_event_effects(
                    item.id,
                    correction,
                    actor=actor,
                )
            assert selected_correction is not None
            return selected_correction

    async def _reverse_event_effects(
        self,
        event_id: str,
        correction: LabBottleEvent,
        *,
        actor: str,
    ) -> None:
        for original_effect in await self.repository.effects_for_event(event_id):
            inverse_effect = await self.repository.add(
                LabBottleEventEffect(
                    event_id=correction.id,
                    bottle_id=original_effect.bottle_id,
                    stock_solution_id=original_effect.stock_solution_id,
                    material_id=original_effect.material_id,
                    mass_delta_g=-original_effect.mass_delta_g,
                    measured_volume_ul=(
                        -original_effect.measured_volume_ul
                        if original_effect.measured_volume_ul is not None
                        else None
                    ),
                    density_g_ml=original_effect.density_g_ml,
                )
            )
            original_movement = await self.repository.inventory_movement_for_effect(
                original_effect.id
            )
            if original_movement is not None:
                stock = await self.repository.get_stock(
                    original_movement.stock_solution_id
                )
                if stock is None:
                    raise KeyError(
                        "Unknown stock solution: "
                        f"{original_movement.stock_solution_id}"
                    )
                before = await self.repository.stock_balance_g(stock.id)
                delta = -original_movement.mass_delta_g
                await self._append_inventory_movement(
                    stock=stock,
                    movement_type="REVERSAL",
                    raw_quantity=abs(delta),
                    balance_before=before,
                    balance_after=before + delta,
                    actor=actor,
                    transaction_id=correction.transaction_id,
                    idempotency_key=f"movement:{correction.id}:{inverse_effect.id}",
                    reason="compensating_event",
                    mass_delta_g=delta,
                    event_effect_id=inverse_effect.id,
                    bottle_event_id=correction.id,
                    reversal_of_movement_id=original_movement.id,
                    measured_volume_ul=(
                        -original_movement.measured_volume_ul
                        if original_movement.measured_volume_ul is not None
                        else None
                    ),
                    standard_uncertainty=(
                        original_movement.standard_uncertainty
                    ),
                )

    async def reconstruct_bottle(self, bottle_id: str) -> BottleLedgerState:
        return await self.repository.reconstruct_bottle(bottle_id)

    async def stock_balance_g(self, stock_solution_id: str) -> float:
        return await self.repository.stock_balance_g(stock_solution_id)

    async def reconcile_stock_balance(
        self,
        stock_solution_id: str,
        remaining_mass_g: float,
        *,
        actor: str = "administrator",
        command_id: str | None = None,
        standard_uncertainty: float | None = None,
    ) -> LabStockSolution:
        """Record an append-only adjustment while keeping the projection synchronized."""

        if remaining_mass_g < 0:
            raise ValueError("remaining_mass_g must be nonnegative")
        async with self._transaction():
            stock = await self.repository.get_stock(stock_solution_id)
            if stock is None:
                raise KeyError(f"Unknown stock solution: {stock_solution_id}")
            current_balance = await self.repository.stock_balance_g(stock_solution_id)
            adjustment = remaining_mass_g - current_balance
            if abs(adjustment) > 1e-12:
                transaction_id = str(uuid4())
                await self._append_inventory_movement(
                    stock=stock,
                    movement_type="ADJUSTMENT",
                    raw_quantity=abs(adjustment),
                    balance_before=current_balance,
                    balance_after=remaining_mass_g,
                    actor=actor,
                    transaction_id=transaction_id,
                    idempotency_key=(
                        f"reconcile:{command_id}"
                        if command_id
                        else f"reconcile:{transaction_id}"
                    ),
                    reason="manual_reconciliation",
                    mass_delta_g=adjustment,
                    admin_cause="manual_reconciliation",
                    standard_uncertainty=standard_uncertainty,
                )
            stock.remaining_mass_g = remaining_mass_g
            return stock

    async def create_experiment(
        self,
        name: str,
        *,
        protocol: dict,
        status: str = "planned",
    ) -> LabExperiment:
        name = name.strip()
        status = status.strip()
        if not name or not status:
            raise ValueError("experiment name and status must not be empty")
        async with self._transaction():
            return await self.repository.add(
                LabExperiment(name=name, protocol_json=dict(protocol), status=status)
            )

    async def add_experiment_sample(
        self,
        *,
        experiment_id: str,
        bottle_id: str,
        blind_code: str,
    ) -> LabSample:
        blind_code = blind_code.strip()
        if not blind_code:
            raise ValueError("blind_code must not be empty")
        async with self._transaction():
            if await self.repository.get_experiment(experiment_id) is None:
                raise KeyError(f"Unknown experiment: {experiment_id}")
            if await self.repository.get_bottle(bottle_id) is None:
                raise KeyError(f"Unknown bottle: {bottle_id}")
            return await self.repository.add(
                LabSample(
                    experiment_id=experiment_id,
                    bottle_id=bottle_id,
                    blind_code=blind_code,
                )
            )

    async def record_application(
        self,
        *,
        sample_id: str,
        applied_at: datetime,
        dose: dict,
        context: dict,
    ) -> LabApplication:
        if applied_at.tzinfo is None or applied_at.utcoffset() is None:
            raise ValueError("applied_at must be timezone-aware")
        async with self._transaction():
            if await self.repository.get_sample(sample_id) is None:
                raise KeyError(f"Unknown sample: {sample_id}")
            return await self.repository.add(
                LabApplication(
                    sample_id=sample_id,
                    applied_at=applied_at,
                    dose_json=dict(dose),
                    context_json=dict(context),
                )
            )

    async def record_observation(
        self,
        *,
        application_id: str,
        elapsed_seconds: float,
        observations: dict,
    ) -> LabObservation:
        if elapsed_seconds < 0:
            raise ValueError("elapsed_seconds must be nonnegative")
        async with self._transaction():
            if await self.repository.get_application(application_id) is None:
                raise KeyError(f"Unknown application: {application_id}")
            return await self.repository.add(
                LabObservation(
                    application_id=application_id,
                    elapsed_seconds=elapsed_seconds,
                    observations_json=dict(observations),
                )
            )

    async def record_pairwise_comparison(
        self,
        *,
        experiment_id: str,
        left_sample_id: str,
        right_sample_id: str,
        preferred_sample_id: str | None,
        context: dict,
    ) -> LabPairwiseComparison:
        if left_sample_id == right_sample_id:
            raise ValueError("pairwise comparison requires different samples")
        if preferred_sample_id not in {None, left_sample_id, right_sample_id}:
            raise ValueError("preferred sample must be left, right, or None for a tie")
        async with self._transaction():
            if await self.repository.get_experiment(experiment_id) is None:
                raise KeyError(f"Unknown experiment: {experiment_id}")
            left = await self.repository.get_sample(left_sample_id)
            right = await self.repository.get_sample(right_sample_id)
            if left is None or right is None:
                raise KeyError("Unknown comparison sample")
            if left.experiment_id != experiment_id or right.experiment_id != experiment_id:
                raise ValueError("comparison samples must belong to the same experiment")
            return await self.repository.add(
                LabPairwiseComparison(
                    experiment_id=experiment_id,
                    left_sample_id=left_sample_id,
                    right_sample_id=right_sample_id,
                    preferred_sample_id=preferred_sample_id,
                    context_json=dict(context),
                )
            )

    async def record_prediction(
        self,
        *,
        experiment_id: str,
        sample_id: str | None,
        model_key: str,
        model_version: str,
        status: str,
        prediction: dict,
        evidence_id: str | None = None,
    ) -> LabPrediction:
        if not model_key.strip() or not model_version.strip() or not status.strip():
            raise ValueError("prediction model key, version, and status must not be empty")
        async with self._transaction():
            if await self.repository.get_experiment(experiment_id) is None:
                raise KeyError(f"Unknown experiment: {experiment_id}")
            if sample_id is not None:
                sample = await self.repository.get_sample(sample_id)
                if sample is None or sample.experiment_id != experiment_id:
                    raise ValueError("prediction sample must belong to the experiment")
            return await self.repository.add(
                LabPrediction(
                    experiment_id=experiment_id,
                    sample_id=sample_id,
                    model_key=model_key.strip(),
                    model_version=model_version.strip(),
                    status=status.strip(),
                    prediction_json=dict(prediction),
                    evidence_id=evidence_id,
                )
            )

    async def record_outcome(
        self,
        *,
        experiment_id: str,
        prediction_id: str | None,
        outcome: dict,
    ) -> LabOutcome:
        async with self._transaction():
            if await self.repository.get_experiment(experiment_id) is None:
                raise KeyError(f"Unknown experiment: {experiment_id}")
            if prediction_id is not None:
                prediction = await self.repository.get_prediction(prediction_id)
                if prediction is None or prediction.experiment_id != experiment_id:
                    raise ValueError("outcome prediction must belong to the experiment")
            return await self.repository.add(
                LabOutcome(
                    experiment_id=experiment_id,
                    prediction_id=prediction_id,
                    outcome_json=dict(outcome),
                )
            )


__all__ = [
    "AlreadyCompensatedError",
    "ConcurrentWriteError",
    "IdempotencyConflictError",
    "InsufficientBottleMassError",
    "InsufficientStockError",
    "LabService",
    "LabTransactionError",
    "StaleBottleStreamError",
]


def _command_token(scope: str, command_id: str) -> str:
    command = command_id.strip()
    if not command:
        raise ValueError("command_id must not be empty")
    return sha256(f"{scope}\0{command}".encode("utf-8")).hexdigest()
