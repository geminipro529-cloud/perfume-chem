"""Canonical proposal-confirm-measure-commit bottle execution lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import TYPE_CHECKING, Any

from engine.calibration.hashing import stable_json_hash

from app.models.lab import LabBottleMeasurement
from app.models.lab_execution import (
    ACTION_TYPES,
    CONFIRMATION_DECISIONS,
    LabBottleActionCommit,
    LabBottleActionConfirmation,
    LabBottleActionProposal,
)
from app.models.lab_planning import LabInventoryReservationEvent
from app.repositories.lab import BottleLedgerState

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.lab import LabBottleEvent
    from app.repositories.lab import LabRepository


class ExecutionDomainError(ValueError):
    """Stable coded rejection for a physical execution command."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class ExecutionConflictError(ExecutionDomainError):
    """A valid command conflicts with canonical lifecycle state."""


def _text(value: str, field: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ExecutionDomainError(
            "INVALID_ACTION_INPUT",
            f"{field} must not be empty.",
        )
    return normalized


def _positive(value: float, field: str) -> float:
    normalized = float(value)
    if not isfinite(normalized) or normalized <= 0:
        raise ExecutionDomainError(
            "INVALID_ACTION_INPUT",
            f"{field} must be finite and greater than zero.",
        )
    return normalized


def _nonnegative_optional(
    value: float | None,
    field: str,
) -> float | None:
    if value is None:
        return None
    normalized = float(value)
    if not isfinite(normalized) or normalized < 0:
        raise ExecutionDomainError(
            "INVALID_ACTION_INPUT",
            f"{field} must be finite and nonnegative.",
        )
    return normalized


def _aware(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExecutionDomainError(
            "INVALID_ACTION_INPUT",
            f"{field} must be timezone-aware.",
        )
    return value


@dataclass(frozen=True, slots=True)
class BottleActionProposalInput:
    schema_version: str
    reservation_id: str
    bottle_id: str
    action_type: str
    planned_mass_g: float
    expected_sequence: int
    idempotency_key: str
    actor: str
    rationale: str

    def __post_init__(self) -> None:
        for field in (
            "schema_version",
            "reservation_id",
            "bottle_id",
            "idempotency_key",
            "actor",
            "rationale",
        ):
            object.__setattr__(
                self,
                field,
                _text(getattr(self, field), field),
            )
        action_type = _text(self.action_type, "action_type").upper()
        if action_type not in ACTION_TYPES:
            raise ExecutionDomainError(
                "ACTION_TYPE_NOT_SUPPORTED",
                f"Unsupported action type: {action_type}.",
            )
        object.__setattr__(self, "action_type", action_type)
        object.__setattr__(
            self,
            "planned_mass_g",
            _positive(self.planned_mass_g, "planned_mass_g"),
        )
        sequence = int(self.expected_sequence)
        if sequence < 0:
            raise ExecutionDomainError(
                "INVALID_ACTION_INPUT",
                "expected_sequence must be nonnegative.",
            )
        object.__setattr__(self, "expected_sequence", sequence)


@dataclass(frozen=True, slots=True)
class BottleActionConfirmationInput:
    decision: str
    confirmer_pseudonym: str
    confirmed_at: datetime
    rationale: str

    def __post_init__(self) -> None:
        decision = _text(self.decision, "decision").upper()
        if decision not in CONFIRMATION_DECISIONS:
            raise ExecutionDomainError(
                "INVALID_CONFIRMATION_DECISION",
                f"Unsupported confirmation decision: {decision}.",
            )
        object.__setattr__(self, "decision", decision)
        object.__setattr__(
            self,
            "confirmer_pseudonym",
            _text(self.confirmer_pseudonym, "confirmer_pseudonym"),
        )
        object.__setattr__(
            self,
            "confirmed_at",
            _aware(self.confirmed_at, "confirmed_at"),
        )
        object.__setattr__(
            self,
            "rationale",
            _text(self.rationale, "rationale"),
        )


@dataclass(frozen=True, slots=True)
class BottleActionMeasurementInput:
    quantity_kind: str
    value: float
    unit: str
    standard_uncertainty: float | None
    method: str
    measured_at: datetime
    actor: str

    def __post_init__(self) -> None:
        quantity_kind = _text(
            self.quantity_kind,
            "quantity_kind",
        ).lower()
        unit = _text(self.unit, "unit")
        if quantity_kind != "mass" or unit != "g":
            raise ExecutionDomainError(
                "ACTION_MEASUREMENT_BASIS_UNSUPPORTED",
                "Bottle additions require a mass measurement in g.",
            )
        object.__setattr__(self, "quantity_kind", quantity_kind)
        object.__setattr__(self, "unit", unit)
        object.__setattr__(self, "value", _positive(self.value, "value"))
        object.__setattr__(
            self,
            "standard_uncertainty",
            _nonnegative_optional(
                self.standard_uncertainty,
                "standard_uncertainty",
            ),
        )
        object.__setattr__(self, "method", _text(self.method, "method"))
        object.__setattr__(
            self,
            "measured_at",
            _aware(self.measured_at, "measured_at"),
        )
        object.__setattr__(self, "actor", _text(self.actor, "actor"))


def bottle_state_payload(state: BottleLedgerState) -> dict[str, Any]:
    return {
        "bottle_id": state.bottle_id,
        "stream_sequence": state.stream_sequence,
        "total_mass_g": state.total_mass_g,
        "stock_masses_g": {
            stock_id: state.stock_masses_g[stock_id]
            for stock_id in sorted(state.stock_masses_g)
        },
        "solvent_mass_g": state.solvent_mass_g,
        "tare_mass_g": state.tare_mass_g,
        "is_closed": state.is_closed,
    }


def structured_bottle_state_diff(
    before: BottleLedgerState,
    after: BottleLedgerState,
    *,
    line_delta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if before.bottle_id != after.bottle_id:
        raise ExecutionDomainError(
            "BOTTLE_STATE_MISMATCH",
            "State diff requires the same bottle identity.",
        )
    stock_ids = sorted(
        set(before.stock_masses_g) | set(after.stock_masses_g)
    )
    deltas = {
        stock_id: (
            after.stock_masses_g.get(stock_id, 0.0)
            - before.stock_masses_g.get(stock_id, 0.0)
        )
        for stock_id in stock_ids
    }
    result = {
        "schema_version": (
            "a5-bottle-state-diff-v1"
            if line_delta is not None
            else "a2-bottle-state-diff-v1"
        ),
        "bottle_id": before.bottle_id,
        "from_sequence": before.stream_sequence,
        "to_sequence": after.stream_sequence,
        "total_mass_delta_g": after.total_mass_g - before.total_mass_g,
        "stock_mass_deltas_g": {
            stock_id: delta
            for stock_id, delta in deltas.items()
            if abs(delta) > 1e-12
        },
        "before": bottle_state_payload(before),
        "after": bottle_state_payload(after),
    }
    if line_delta is not None:
        result["line_delta"] = dict(line_delta)
    return result


class LabExecutionServiceMixin:
    """Execution commands sharing the canonical LabService transaction owner."""

    if TYPE_CHECKING:
        repository: LabRepository
        session: AsyncSession

        def _transaction(self) -> AbstractAsyncContextManager[None]: ...

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
        ) -> LabBottleEvent: ...

    async def propose_bottle_action(
        self,
        command: BottleActionProposalInput,
    ) -> LabBottleActionProposal:
        async with self._transaction():
            existing = (
                await self.repository.bottle_action_proposal_for_idempotency(
                    command.idempotency_key
                )
            )
            if existing is not None:
                if (
                    existing.schema_version == command.schema_version
                    and existing.reservation_id == command.reservation_id
                    and existing.bottle_id == command.bottle_id
                    and existing.action_type == command.action_type
                    and existing.planned_mass_g == command.planned_mass_g
                    and existing.expected_sequence == command.expected_sequence
                    and existing.actor == command.actor
                    and existing.rationale == command.rationale
                ):
                    return existing
                raise ExecutionConflictError(
                    "ACTION_IDEMPOTENCY_CONFLICT",
                    "Action idempotency key was reused for a different proposal.",
                )
            reservation = await self.repository.latest_reservation_event(
                command.reservation_id
            )
            if reservation is None:
                raise ExecutionConflictError(
                    "RESERVATION_NOT_FOUND",
                    f"Reservation not found: {command.reservation_id}.",
                )
            if reservation.state != "RESERVED":
                raise ExecutionConflictError(
                    "RESERVATION_NOT_ACTIVE",
                    "Physical actions require an active reservation.",
                )
            if command.planned_mass_g > reservation.reserved_mass_g + 1e-12:
                raise ExecutionConflictError(
                    "ACTION_EXCEEDS_RESERVATION",
                    "Planned action mass exceeds the active reservation.",
                )
            if await self.repository.get_bottle(command.bottle_id) is None:
                raise ExecutionConflictError(
                    "BOTTLE_NOT_FOUND",
                    f"Bottle not found: {command.bottle_id}.",
                )
            bottle_events = await self.repository.events_for_bottle(
                command.bottle_id
            )
            if any(
                event.event_type in {"ADD_MATERIAL", "ADD_SOLVENT"}
                and event.payload_json.get("execution_scope")
                != "PLANNED_PROPOSAL_CONFIRM_MEASURE_COMMIT"
                for event in bottle_events
            ):
                raise ExecutionConflictError(
                    "BOTTLE_FREEFORM_QUARANTINED",
                    "A bottle with freeform additions cannot enter planned formula execution.",
                )
            sequence = await self.repository.latest_sequence(command.bottle_id)
            if sequence != command.expected_sequence:
                raise ExecutionConflictError(
                    "STALE_BOTTLE_STREAM",
                    f"Expected sequence {command.expected_sequence}, "
                    f"current sequence is {sequence}.",
                )
            payload = {
                "schema": "lab-bottle-action-proposal-v1",
                "schema_version": command.schema_version,
                "reservation_id": reservation.reservation_id,
                "reservation_event_id": reservation.id,
                "bottle_id": command.bottle_id,
                "action_type": command.action_type,
                "stock_solution_id": reservation.stock_solution_id,
                "planned_mass_g": command.planned_mass_g,
                "expected_sequence": command.expected_sequence,
                "idempotency_key": command.idempotency_key,
                "actor": command.actor,
                "rationale": command.rationale,
            }
            return await self.repository.add(
                LabBottleActionProposal(
                    schema_version=command.schema_version,
                    reservation_id=reservation.reservation_id,
                    reservation_event_id=reservation.id,
                    bottle_id=command.bottle_id,
                    action_type=command.action_type,
                    stock_solution_id=reservation.stock_solution_id,
                    planned_mass_g=command.planned_mass_g,
                    expected_sequence=command.expected_sequence,
                    idempotency_key=command.idempotency_key,
                    actor=command.actor,
                    rationale=command.rationale,
                    content_sha256=stable_json_hash(payload),
                )
            )

    async def confirm_bottle_action(
        self,
        proposal_id: str,
        command: BottleActionConfirmationInput,
    ) -> LabBottleActionConfirmation:
        proposal_id = _text(proposal_id, "proposal_id")
        payload = {
            "schema": "lab-bottle-action-confirmation-v1",
            "proposal_id": proposal_id,
            "decision": command.decision,
            "confirmer_pseudonym": command.confirmer_pseudonym,
            "confirmed_at": command.confirmed_at.isoformat(),
            "rationale": command.rationale,
        }
        content_sha256 = stable_json_hash(payload)
        async with self._transaction():
            if (
                await self.repository.get_bottle_action_proposal(proposal_id)
                is None
            ):
                raise ExecutionConflictError(
                    "ACTION_PROPOSAL_NOT_FOUND",
                    f"Action proposal not found: {proposal_id}.",
                )
            existing = await self.repository.bottle_action_confirmation(
                proposal_id
            )
            if existing is not None:
                if existing.content_sha256 == content_sha256:
                    return existing
                raise ExecutionConflictError(
                    "ACTION_ALREADY_CONFIRMED",
                    "Action proposal already has an immutable human decision.",
                )
            return await self.repository.add(
                LabBottleActionConfirmation(
                    proposal_id=proposal_id,
                    decision=command.decision,
                    confirmer_pseudonym=command.confirmer_pseudonym,
                    confirmed_at=command.confirmed_at,
                    rationale=command.rationale,
                    content_sha256=content_sha256,
                )
            )

    async def record_bottle_action_measurement(
        self,
        proposal_id: str,
        command: BottleActionMeasurementInput,
    ) -> LabBottleMeasurement:
        proposal_id = _text(proposal_id, "proposal_id")
        async with self._transaction():
            proposal = await self.repository.get_bottle_action_proposal(
                proposal_id
            )
            if proposal is None:
                raise ExecutionConflictError(
                    "ACTION_PROPOSAL_NOT_FOUND",
                    f"Action proposal not found: {proposal_id}.",
                )
            confirmation = await self.repository.bottle_action_confirmation(
                proposal_id
            )
            if confirmation is None or confirmation.decision != "CONFIRMED":
                raise ExecutionConflictError(
                    "ACTION_NOT_CONFIRMED",
                    "Measurement requires an affirmative human confirmation.",
                )
            existing = await self.repository.bottle_action_measurement(
                proposal_id,
                command.quantity_kind,
            )
            if existing is not None:
                if (
                    existing.value == command.value
                    and existing.unit == command.unit
                    and existing.standard_uncertainty
                    == command.standard_uncertainty
                    and existing.method == command.method
                    and existing.measured_at == command.measured_at
                    and existing.actor == command.actor
                ):
                    return existing
                raise ExecutionConflictError(
                    "ACTION_MEASUREMENT_CONFLICT",
                    "The immutable action measurement already exists.",
                )
            return await self.repository.add(
                LabBottleMeasurement(
                    bottle_event_id=None,
                    proposal_id=proposal_id,
                    quantity_kind=command.quantity_kind,
                    value=command.value,
                    unit=command.unit,
                    standard_uncertainty=command.standard_uncertainty,
                    method=command.method,
                    measured_at=command.measured_at,
                    actor=command.actor,
                )
            )

    async def commit_bottle_action(
        self,
        proposal_id: str,
        *,
        actor: str,
        rationale: str,
    ) -> LabBottleActionCommit:
        proposal_id = _text(proposal_id, "proposal_id")
        actor = _text(actor, "actor")
        rationale = _text(rationale, "rationale")
        async with self._transaction():
            existing = await self.repository.bottle_action_commit(proposal_id)
            if existing is not None:
                if existing.actor == actor and existing.rationale == rationale:
                    return existing
                raise ExecutionConflictError(
                    "ACTION_ALREADY_COMMITTED",
                    "Action proposal already has an immutable transaction commit.",
                )
            proposal = await self.repository.get_bottle_action_proposal(
                proposal_id
            )
            if proposal is None:
                raise ExecutionConflictError(
                    "ACTION_PROPOSAL_NOT_FOUND",
                    f"Action proposal not found: {proposal_id}.",
                )
            confirmation = await self.repository.bottle_action_confirmation(
                proposal_id
            )
            if confirmation is None or confirmation.decision != "CONFIRMED":
                raise ExecutionConflictError(
                    "ACTION_NOT_CONFIRMED",
                    "Transaction commit requires human confirmation.",
                )
            measurement = await self.repository.bottle_action_measurement(
                proposal_id,
                "mass",
            )
            if measurement is None:
                raise ExecutionConflictError(
                    "ACTION_MEASUREMENT_REQUIRED",
                    "Transaction commit requires a gravimetric mass measurement.",
                )
            reservation = await self.repository.latest_reservation_event(
                proposal.reservation_id
            )
            if reservation is None or reservation.state != "RESERVED":
                raise ExecutionConflictError(
                    "RESERVATION_NOT_ACTIVE",
                    "Transaction commit requires the active reservation.",
                )
            if reservation.id != proposal.reservation_event_id:
                raise ExecutionConflictError(
                    "RESERVATION_VERSION_CHANGED",
                    "Reservation state changed after action proposal.",
                )
            if measurement.value > reservation.reserved_mass_g + 1e-12:
                raise ExecutionConflictError(
                    "MEASUREMENT_EXCEEDS_RESERVATION",
                    "Measured mass exceeds the active reservation.",
                )
            line = await self.repository.get_build_plan_line(
                reservation.build_plan_line_id
            )
            if line is None:
                raise ExecutionConflictError(
                    "BUILD_PLAN_LINE_NOT_FOUND",
                    "Reserved build-plan line no longer exists.",
                )
            if str(line.unit).strip().casefold() not in {"g", "gram", "grams"}:
                raise ExecutionConflictError(
                    "BUILD_PLAN_UNIT_NOT_GRAVIMETRIC",
                    "Bottle-action completion requires a mass-based build-plan line.",
                )
            # Resolution is the only immutable line field that is an explicit
            # completion granularity. Expected transfer loss and measurement
            # uncertainty are evidence to retain, not permission to silently
            # turn a short dose into a fully satisfied reservation.
            completion_tolerance_g = max(float(line.resolution), 1e-12)
            if (
                abs(line.planned_raw_quantity - reservation.reserved_mass_g)
                > completion_tolerance_g
            ):
                raise ExecutionConflictError(
                    "RESERVATION_PLAN_QUANTITY_MISMATCH",
                    "Active reservation does not match the immutable build-plan quantity within tolerance.",
                )
            if (
                abs(proposal.planned_mass_g - reservation.reserved_mass_g)
                > completion_tolerance_g
            ):
                raise ExecutionConflictError(
                    "PROPOSAL_RESERVATION_QUANTITY_MISMATCH",
                    "Action proposal does not cover the active reservation within tolerance.",
                )
            completion_delta_g = abs(
                measurement.value - reservation.reserved_mass_g
            )
            if completion_delta_g > completion_tolerance_g:
                raise ExecutionConflictError(
                    "MEASUREMENT_OUTSIDE_COMPLETION_TOLERANCE",
                    "Measured mass cannot fulfill the reservation outside the immutable completion tolerance.",
                )
            before = await self.repository.reconstruct_bottle(
                proposal.bottle_id
            )
            if before.stream_sequence != proposal.expected_sequence:
                raise ExecutionConflictError(
                    "STALE_BOTTLE_STREAM",
                    f"Expected sequence {proposal.expected_sequence}, "
                    f"current sequence is {before.stream_sequence}.",
                )
            event = await self._add_stock_to_bottle_in_transaction(
                bottle_id=proposal.bottle_id,
                stock_solution_id=proposal.stock_solution_id,
                mass_g=measurement.value,
                expected_sequence=proposal.expected_sequence,
                command_id=f"action-proposal:{proposal.id}",
                measured_volume_ul=None,
                standard_uncertainty=measurement.standard_uncertainty,
                actor=actor,
                build_plan_line_id=line.id,
                reservation_event_id=reservation.id,
                event_type=(
                    "ADD_SOLVENT"
                    if proposal.action_type == "ADD_SOLVENT"
                    else "ADD_MATERIAL"
                ),
            )
            after = await self.repository.reconstruct_bottle(
                proposal.bottle_id
            )
            movement = await self.repository.inventory_movement_for_event(
                event.id
            )
            if movement is None:
                raise ExecutionConflictError(
                    "INVENTORY_MOVEMENT_MISSING",
                    "Committed bottle event has no inventory movement.",
                )
            state_diff = structured_bottle_state_diff(
                before,
                after,
                line_delta={
                    "target_line_id": line.target_line_id,
                    "target_identity": line.target_identity,
                    "target_quantity": line.planned_raw_quantity,
                    "selected_stock_quantity": movement.balance_before,
                    "planned_raw_quantity": line.planned_raw_quantity,
                    "planned_active_quantity": (
                        line.planned_active_quantity
                    ),
                    "reserved_quantity": reservation.reserved_mass_g,
                    "committed_quantity": measurement.value,
                    "completion_tolerance_g": completion_tolerance_g,
                    "completion_delta_g": completion_delta_g,
                    "unit": line.unit,
                    "basis": line.concentration_basis,
                    "standard_uncertainty": (
                        measurement.standard_uncertainty
                    ),
                    "density_source": line.density_source,
                    "comparable": True,
                    "incomparability_reason": None,
                    "substitution_state": line.substitution_class,
                    "preserved_functions": list(
                        line.preserved_functions_json
                    ),
                    "lost_functions": list(line.lost_functions_json),
                    "action_state": "COMMITTED",
                },
            )
            reservation_payload = {
                "schema": "a2-reservation-command-v1",
                "operation": "TRANSITION",
                "reservation_id": reservation.reservation_id,
                "next_state": "FULFILLED",
                "idempotency_key": f"action-fulfill:{proposal.id}",
                "actor": actor,
                "rationale": rationale,
            }
            fulfilled = await self.repository.add(
                LabInventoryReservationEvent(
                    reservation_id=reservation.reservation_id,
                    sequence=reservation.sequence + 1,
                    parent_event_id=reservation.id,
                    build_plan_version_id=reservation.build_plan_version_id,
                    build_plan_line_id=reservation.build_plan_line_id,
                    stock_solution_id=reservation.stock_solution_id,
                    state="FULFILLED",
                    reserved_mass_g=reservation.reserved_mass_g,
                    idempotency_key=f"action-fulfill:{proposal.id}",
                    command_sha256=stable_json_hash(reservation_payload),
                    actor=actor,
                    rationale=rationale,
                )
            )
            before_payload = bottle_state_payload(before)
            after_payload = bottle_state_payload(after)
            commit_payload = {
                "schema": "lab-bottle-action-commit-v1",
                "proposal_id": proposal.id,
                "bottle_event_id": event.id,
                "fulfilled_reservation_event_id": fulfilled.id,
                "actor": actor,
                "rationale": rationale,
                "before_state": before_payload,
                "after_state": after_payload,
                "state_diff": state_diff,
            }
            return await self.repository.add(
                LabBottleActionCommit(
                    proposal_id=proposal.id,
                    bottle_event_id=event.id,
                    fulfilled_reservation_event_id=fulfilled.id,
                    actor=actor,
                    rationale=rationale,
                    before_state_json=before_payload,
                    after_state_json=after_payload,
                    state_diff_json=state_diff,
                    content_sha256=stable_json_hash(commit_payload),
                )
            )

    async def bottle_action_diff(self, proposal_id: str) -> dict[str, Any]:
        proposal_id = _text(proposal_id, "proposal_id")
        commit = await self.repository.bottle_action_commit(proposal_id)
        if commit is None:
            raise ExecutionConflictError(
                "ACTION_NOT_COMMITTED",
                "Structured state diff is available only after commit.",
            )
        return dict(commit.state_diff_json)


__all__ = [
    "BottleActionConfirmationInput",
    "BottleActionMeasurementInput",
    "BottleActionProposalInput",
    "ExecutionConflictError",
    "ExecutionDomainError",
    "LabExecutionServiceMixin",
    "bottle_state_payload",
    "structured_bottle_state_diff",
]
