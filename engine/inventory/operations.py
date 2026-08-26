"""Pure append-only inventory operations and explainable lot selection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Iterable, Mapping

ZERO = Decimal("0")


class MovementType(StrEnum):
    RESERVATION = "RESERVATION"
    RESERVATION_RELEASE = "RESERVATION_RELEASE"
    CONSUMPTION = "CONSUMPTION"
    RETURN = "RETURN"
    ADJUSTMENT = "ADJUSTMENT"
    TRANSFER = "TRANSFER"
    CORRECTION = "CORRECTION"
    REVERSAL = "REVERSAL"


class ActionState(StrEnum):
    PROPOSED = "PROPOSED"
    CONFIRMED = "CONFIRMED"
    MEASURED = "MEASURED"
    COMMITTED = "COMMITTED"
    CORRECTED = "CORRECTED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class ComparabilityReason(StrEnum):
    UNIT_INCOMPARABLE = "UNIT_INCOMPARABLE"
    BASIS_INCOMPARABLE = "BASIS_INCOMPARABLE"
    DENSITY_UNKNOWN = "DENSITY_UNKNOWN"
    IDENTITY_UNRESOLVED = "IDENTITY_UNRESOLVED"
    UNCERTAINTY_UNBOUNDED = "UNCERTAINTY_UNBOUNDED"


def _decimal(value: Decimal, field: str, *, nonnegative: bool = False) -> Decimal:
    normalized = Decimal(value)
    if not normalized.is_finite():
        raise ValueError(f"{field} must be finite")
    if nonnegative and normalized < ZERO:
        raise ValueError(f"{field} must be nonnegative")
    return normalized


def _text(value: str, field: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field} must not be empty")
    return normalized


@dataclass(frozen=True, slots=True)
class InventoryMovement:
    """One immutable inventory movement with replay-closing balances."""

    movement_id: str
    movement_type: MovementType
    stock_lot_id: str
    raw_quantity: Decimal
    active_quantity: Decimal
    unit: str
    basis: str
    balance_before: Decimal
    balance_after: Decimal
    standard_uncertainty: Decimal | None
    actor: str
    timestamp: datetime
    transaction_id: str
    idempotency_key: str
    build_plan_line_id: str | None = None
    reservation_event_id: str | None = None
    bottle_event_id: str | None = None
    admin_cause: str | None = None
    correction_of_movement_id: str | None = None
    reversal_of_movement_id: str | None = None
    transfer_direction: str | None = None

    def __post_init__(self) -> None:
        for field in (
            "movement_id",
            "stock_lot_id",
            "unit",
            "basis",
            "actor",
            "transaction_id",
            "idempotency_key",
        ):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        object.__setattr__(
            self,
            "movement_type",
            MovementType(self.movement_type),
        )
        object.__setattr__(
            self,
            "raw_quantity",
            _decimal(self.raw_quantity, "raw_quantity", nonnegative=True),
        )
        object.__setattr__(
            self,
            "active_quantity",
            _decimal(self.active_quantity, "active_quantity", nonnegative=True),
        )
        object.__setattr__(
            self,
            "balance_before",
            _decimal(self.balance_before, "balance_before"),
        )
        object.__setattr__(
            self,
            "balance_after",
            _decimal(self.balance_after, "balance_after"),
        )
        if self.active_quantity > self.raw_quantity:
            raise ValueError("active_quantity cannot exceed raw_quantity")
        if self.standard_uncertainty is not None:
            object.__setattr__(
                self,
                "standard_uncertainty",
                _decimal(
                    self.standard_uncertainty,
                    "standard_uncertainty",
                    nonnegative=True,
                ),
            )
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        if self.correction_of_movement_id and self.reversal_of_movement_id:
            raise ValueError(
                "a movement cannot be both a correction and a reversal"
            )
        if (
            self.movement_type is MovementType.CORRECTION
            and not self.correction_of_movement_id
        ):
            raise ValueError("CORRECTION requires correction_of_movement_id")
        if (
            self.movement_type is MovementType.REVERSAL
            and not self.reversal_of_movement_id
        ):
            raise ValueError("REVERSAL requires reversal_of_movement_id")
        if self.movement_type is MovementType.TRANSFER:
            direction = str(self.transfer_direction or "").upper()
            if direction not in {"IN", "OUT"}:
                raise ValueError("TRANSFER requires transfer_direction IN or OUT")
            object.__setattr__(self, "transfer_direction", direction)


def _expected_delta(movement: InventoryMovement) -> Decimal:
    kind = movement.movement_type
    if kind in {
        MovementType.RESERVATION,
        MovementType.RESERVATION_RELEASE,
    }:
        return ZERO
    if kind is MovementType.CONSUMPTION:
        return -movement.raw_quantity
    if kind in {MovementType.RETURN, MovementType.REVERSAL}:
        return movement.raw_quantity
    if kind is MovementType.TRANSFER:
        return (
            -movement.raw_quantity
            if movement.transfer_direction == "OUT"
            else movement.raw_quantity
        )
    return movement.balance_after - movement.balance_before


def replay_inventory_movements(
    opening_balances: Mapping[str, Decimal],
    movements: Iterable[InventoryMovement],
) -> dict[str, Decimal]:
    """Replay movements in caller-supplied append order and close every row."""

    balances = {
        _text(lot_id, "stock_lot_id"): _decimal(
            balance,
            "opening_balance",
            nonnegative=True,
        )
        for lot_id, balance in opening_balances.items()
    }
    movement_ids: set[str] = set()
    idempotency_keys: set[str] = set()
    referenced: set[str] = set()
    for movement in movements:
        if movement.movement_id in movement_ids:
            raise ValueError(f"duplicate movement_id {movement.movement_id!r}")
        if movement.idempotency_key in idempotency_keys:
            raise ValueError(
                f"duplicate idempotency key {movement.idempotency_key!r}"
            )
        current = balances.get(movement.stock_lot_id, ZERO)
        if movement.balance_before != current:
            raise ValueError(
                f"stale balance for {movement.stock_lot_id!r}: "
                f"expected {current}, got {movement.balance_before}"
            )
        if movement.balance_before < ZERO or movement.balance_after < ZERO:
            raise ValueError("inventory balance cannot become negative")
        delta = movement.balance_after - movement.balance_before
        expected_delta = _expected_delta(movement)
        if delta != expected_delta:
            raise ValueError(
                f"{movement.movement_type.value} balance delta {delta} "
                f"does not match {expected_delta}"
            )
        reference = (
            movement.correction_of_movement_id
            or movement.reversal_of_movement_id
        )
        if reference is not None:
            if reference not in movement_ids:
                raise ValueError("correction/reversal must reference a prior movement")
            if reference in referenced:
                raise ValueError("movement already has a correction or reversal")
            referenced.add(reference)
        movement_ids.add(movement.movement_id)
        idempotency_keys.add(movement.idempotency_key)
        balances[movement.stock_lot_id] = movement.balance_after
    return balances


def validate_transfer_pair(
    outgoing: InventoryMovement,
    incoming: InventoryMovement,
    *,
    measured_loss: Decimal,
) -> None:
    """Validate one atomic cross-lot transfer pair and measured loss."""

    loss = _decimal(measured_loss, "measured_loss", nonnegative=True)
    if (
        outgoing.movement_type is not MovementType.TRANSFER
        or outgoing.transfer_direction != "OUT"
        or incoming.movement_type is not MovementType.TRANSFER
        or incoming.transfer_direction != "IN"
    ):
        raise ValueError("transfer pair requires one OUT and one IN movement")
    if outgoing.transaction_id != incoming.transaction_id:
        raise ValueError("transfer pair must share transaction_id")
    if outgoing.unit != incoming.unit or outgoing.basis != incoming.basis:
        raise ValueError("transfer pair unit and basis must match")
    if outgoing.raw_quantity != incoming.raw_quantity + loss:
        raise ValueError("transfer mass does not close with measured loss")


@dataclass(frozen=True, slots=True)
class LotRequirement:
    identity: str
    grade: str
    basis: str
    required_quantity: Decimal
    unit: str
    maximum_standard_uncertainty: Decimal

    def __post_init__(self) -> None:
        for field in ("identity", "grade", "basis", "unit"):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        object.__setattr__(
            self,
            "required_quantity",
            _decimal(
                self.required_quantity,
                "required_quantity",
                nonnegative=True,
            ),
        )
        object.__setattr__(
            self,
            "maximum_standard_uncertainty",
            _decimal(
                self.maximum_standard_uncertainty,
                "maximum_standard_uncertainty",
                nonnegative=True,
            ),
        )


@dataclass(frozen=True, slots=True)
class LotCandidate:
    lot_id: str
    identity: str
    grade: str
    basis: str
    available_quantity: Decimal
    unit: str
    concentration_fraction: Decimal
    standard_uncertainty: Decimal
    expires_at: datetime | None
    opened_at: datetime | None
    safety_passed: bool
    expected_waste: Decimal
    substitution_cost: Decimal
    user_preference: int

    def __post_init__(self) -> None:
        for field in ("lot_id", "identity", "grade", "basis", "unit"):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        for field in (
            "available_quantity",
            "concentration_fraction",
            "standard_uncertainty",
            "expected_waste",
            "substitution_cost",
        ):
            object.__setattr__(
                self,
                field,
                _decimal(getattr(self, field), field, nonnegative=True),
            )
        if self.concentration_fraction > Decimal("1"):
            raise ValueError("concentration_fraction cannot exceed one")
        for field in ("expires_at", "opened_at"):
            value = getattr(self, field)
            if value is not None and (
                value.tzinfo is None or value.utcoffset() is None
            ):
                raise ValueError(f"{field} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class LotPolicy:
    now: datetime
    allow_opened: bool = True
    prefer_opened: bool = False

    def __post_init__(self) -> None:
        if self.now.tzinfo is None or self.now.utcoffset() is None:
            raise ValueError("now must be timezone-aware")


@dataclass(frozen=True, slots=True)
class LotSelection:
    selected_lot_id: str | None
    rejected_lots: dict[str, tuple[str, ...]]
    eligible_lots: tuple[str, ...]


def _lot_rejection_reasons(
    requirement: LotRequirement,
    candidate: LotCandidate,
    policy: LotPolicy,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if candidate.identity.casefold() != requirement.identity.casefold():
        reasons.append("IDENTITY_MISMATCH")
    if candidate.grade.casefold() != requirement.grade.casefold():
        reasons.append("GRADE_MISMATCH")
    if (
        candidate.basis.casefold() != requirement.basis.casefold()
        or candidate.unit != requirement.unit
    ):
        reasons.append("BASIS_INCOMPARABLE")
    measurable = candidate.available_quantity - candidate.standard_uncertainty
    if measurable < requirement.required_quantity:
        reasons.append("INSUFFICIENT_MEASURABLE_AMOUNT")
    if (
        not candidate.safety_passed
        or (
            candidate.expires_at is not None
            and candidate.expires_at <= policy.now
        )
    ):
        reasons.append("SAFETY_OR_EXPIRY_FAILED")
    if candidate.opened_at is not None and not policy.allow_opened:
        reasons.append("OPENED_LOT_DISALLOWED")
    if (
        candidate.standard_uncertainty
        > requirement.maximum_standard_uncertainty
    ):
        reasons.append("MEASUREMENT_UNCERTAINTY_EXCEEDED")
    return tuple(reasons)


def select_best_lot(
    requirement: LotRequirement,
    candidates: Iterable[LotCandidate],
    policy: LotPolicy,
) -> LotSelection:
    """Filter by all eligibility gates, then rank by FEFO and total waste."""

    rejected: dict[str, tuple[str, ...]] = {}
    eligible: list[LotCandidate] = []
    for candidate in candidates:
        reasons = _lot_rejection_reasons(requirement, candidate, policy)
        if reasons:
            rejected[candidate.lot_id] = reasons
        else:
            eligible.append(candidate)

    far_future = datetime.max.replace(tzinfo=policy.now.tzinfo)

    def rank(candidate: LotCandidate) -> tuple[object, ...]:
        opened_rank = (
            0
            if policy.prefer_opened and candidate.opened_at is not None
            else 1
        )
        return (
            opened_rank,
            candidate.expires_at or far_future,
            candidate.expected_waste,
            candidate.substitution_cost,
            candidate.standard_uncertainty,
            -candidate.user_preference,
            candidate.lot_id,
        )

    ranked = sorted(eligible, key=rank)
    return LotSelection(
        selected_lot_id=ranked[0].lot_id if ranked else None,
        rejected_lots=rejected,
        eligible_lots=tuple(candidate.lot_id for candidate in ranked),
    )


@dataclass(frozen=True, slots=True)
class StateDelta:
    """Typed target-to-stock execution delta without mixed-unit strings."""

    target_line_id: str
    target_identity: str
    target_quantity: Decimal
    selected_stock_quantity: Decimal
    planned_raw_quantity: Decimal
    planned_active_quantity: Decimal
    reserved_quantity: Decimal
    committed_quantity: Decimal
    unit: str
    basis: str
    standard_uncertainty: Decimal | None
    density_source: str | None
    comparable: bool
    incomparability_reason: ComparabilityReason | None
    substitution_state: str
    preserved_functions: tuple[str, ...]
    lost_functions: tuple[str, ...]
    action_state: ActionState

    def __post_init__(self) -> None:
        for field in (
            "target_line_id",
            "target_identity",
            "unit",
            "basis",
            "substitution_state",
        ):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        for field in (
            "target_quantity",
            "selected_stock_quantity",
            "planned_raw_quantity",
            "planned_active_quantity",
            "reserved_quantity",
            "committed_quantity",
        ):
            object.__setattr__(
                self,
                field,
                _decimal(getattr(self, field), field, nonnegative=True),
            )
        if self.standard_uncertainty is not None:
            object.__setattr__(
                self,
                "standard_uncertainty",
                _decimal(
                    self.standard_uncertainty,
                    "standard_uncertainty",
                    nonnegative=True,
                ),
            )
        object.__setattr__(self, "action_state", ActionState(self.action_state))
        if self.incomparability_reason is not None:
            object.__setattr__(
                self,
                "incomparability_reason",
                ComparabilityReason(self.incomparability_reason),
            )
        if self.comparable and self.incomparability_reason is not None:
            raise ValueError(
                "comparable delta cannot have incomparability_reason"
            )
        if not self.comparable and self.incomparability_reason is None:
            raise ValueError(
                "incomparable delta requires incomparability_reason"
            )

    def as_dict(self) -> dict[str, object]:
        """Return constructor-compatible typed fields."""

        return {
            field: getattr(self, field)
            for field in self.__dataclass_fields__
        }


__all__ = [
    "ActionState",
    "ComparabilityReason",
    "InventoryMovement",
    "LotCandidate",
    "LotPolicy",
    "LotRequirement",
    "LotSelection",
    "MovementType",
    "StateDelta",
    "replay_inventory_movements",
    "select_best_lot",
    "validate_transfer_pair",
]
