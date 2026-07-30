from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from engine.inventory.operations import (
    ActionState,
    ComparabilityReason,
    InventoryMovement,
    LotCandidate,
    LotPolicy,
    LotRequirement,
    MovementType,
    StateDelta,
    replay_inventory_movements,
    select_best_lot,
    validate_transfer_pair,
)

NOW = datetime(2026, 7, 30, tzinfo=UTC)


def _movement(
    movement_id: str,
    movement_type: MovementType,
    *,
    before: str,
    after: str,
    raw: str,
    active: str = "0",
    transaction_id: str = "transaction-1",
    **kwargs,
) -> InventoryMovement:
    idempotency_key = kwargs.pop(
        "idempotency_key",
        f"idempotency-{movement_id}",
    )
    return InventoryMovement(
        movement_id=movement_id,
        movement_type=movement_type,
        stock_lot_id="lot-1",
        raw_quantity=Decimal(raw),
        active_quantity=Decimal(active),
        unit="g",
        basis="mass",
        balance_before=Decimal(before),
        balance_after=Decimal(after),
        standard_uncertainty=Decimal("0.001"),
        actor="operator",
        timestamp=NOW,
        transaction_id=transaction_id,
        idempotency_key=idempotency_key,
        **kwargs,
    )


def test_a5_movement_enum_is_complete():
    assert {item.value for item in MovementType} == {
        "RESERVATION",
        "RESERVATION_RELEASE",
        "CONSUMPTION",
        "RETURN",
        "ADJUSTMENT",
        "TRANSFER",
        "CORRECTION",
        "REVERSAL",
    }


def test_a5_inventory_replay_is_append_only_deterministic_and_balance_checked():
    movements = [
        _movement(
            "reserve",
            MovementType.RESERVATION,
            before="10",
            after="10",
            raw="2",
            build_plan_line_id="line-1",
            reservation_event_id="reservation-1",
        ),
        _movement(
            "consume",
            MovementType.CONSUMPTION,
            before="10",
            after="8",
            raw="2",
            active="0.4",
            build_plan_line_id="line-1",
            bottle_event_id="bottle-event-1",
        ),
    ]

    first = replay_inventory_movements({"lot-1": Decimal("10")}, movements)
    second = replay_inventory_movements({"lot-1": Decimal("10")}, list(movements))

    assert first == second == {"lot-1": Decimal("8")}


def test_a5_inventory_replay_rejects_negative_stale_and_duplicate_commands():
    stale = _movement(
        "stale",
        MovementType.CONSUMPTION,
        before="9",
        after="8",
        raw="1",
    )
    negative = _movement(
        "negative",
        MovementType.CONSUMPTION,
        before="1",
        after="-1",
        raw="2",
    )
    duplicate = _movement(
        "duplicate",
        MovementType.RETURN,
        before="8",
        after="9",
        raw="1",
        idempotency_key="idempotency-stale",
    )

    with pytest.raises(ValueError, match="stale balance"):
        replay_inventory_movements({"lot-1": Decimal("10")}, [stale])
    with pytest.raises(ValueError, match="negative"):
        replay_inventory_movements({"lot-1": Decimal("1")}, [negative])
    with pytest.raises(ValueError, match="idempotency"):
        replay_inventory_movements(
            {"lot-1": Decimal("9")},
            [stale, duplicate],
        )


def test_a5_correction_and_reversal_require_prior_acyclic_reference():
    original = _movement(
        "consume",
        MovementType.CONSUMPTION,
        before="10",
        after="9",
        raw="1",
    )
    reversal = _movement(
        "reverse",
        MovementType.REVERSAL,
        before="9",
        after="10",
        raw="1",
        reversal_of_movement_id="consume",
    )

    assert replay_inventory_movements(
        {"lot-1": Decimal("10")},
        [original, reversal],
    ) == {"lot-1": Decimal("10")}

    with pytest.raises(ValueError, match="prior movement"):
        replay_inventory_movements(
            {"lot-1": Decimal("9")},
            [reversal],
        )


def test_a5_transfer_pair_closes_with_measured_loss():
    outgoing = _movement(
        "transfer-out",
        MovementType.TRANSFER,
        before="5",
        after="3",
        raw="2",
        transaction_id="transfer-1",
        transfer_direction="OUT",
    )
    incoming = InventoryMovement(
        movement_id="transfer-in",
        movement_type=MovementType.TRANSFER,
        stock_lot_id="lot-2",
        raw_quantity=Decimal("1.9"),
        active_quantity=Decimal("0"),
        unit="g",
        basis="mass",
        balance_before=Decimal("0"),
        balance_after=Decimal("1.9"),
        standard_uncertainty=Decimal("0.002"),
        actor="operator",
        timestamp=NOW,
        transaction_id="transfer-1",
        idempotency_key="idempotency-transfer-in",
        transfer_direction="IN",
    )

    assert validate_transfer_pair(
        outgoing,
        incoming,
        measured_loss=Decimal("0.1"),
    ) is None

    with pytest.raises(ValueError, match="mass does not close"):
        validate_transfer_pair(
            outgoing,
            incoming,
            measured_loss=Decimal("0"),
        )


def test_a5_lot_selection_enforces_eligibility_then_fefo_and_waste():
    requirement = LotRequirement(
        identity="iris",
        grade="perfumery",
        basis="mass",
        required_quantity=Decimal("2"),
        unit="g",
        maximum_standard_uncertainty=Decimal("0.02"),
    )
    policy = LotPolicy(
        now=NOW,
        allow_opened=True,
        prefer_opened=True,
    )
    unsafe_high_concentration = LotCandidate(
        lot_id="unsafe",
        identity="iris",
        grade="perfumery",
        basis="mass",
        available_quantity=Decimal("10"),
        unit="g",
        concentration_fraction=Decimal("1"),
        standard_uncertainty=Decimal("0.001"),
        expires_at=NOW + timedelta(days=90),
        opened_at=None,
        safety_passed=False,
        expected_waste=Decimal("0"),
        substitution_cost=Decimal("0"),
        user_preference=10,
    )
    opened_fefo = LotCandidate(
        lot_id="opened-fefo",
        identity="iris",
        grade="perfumery",
        basis="mass",
        available_quantity=Decimal("2.05"),
        unit="g",
        concentration_fraction=Decimal("0.2"),
        standard_uncertainty=Decimal("0.01"),
        expires_at=NOW + timedelta(days=10),
        opened_at=NOW - timedelta(days=5),
        safety_passed=True,
        expected_waste=Decimal("0.05"),
        substitution_cost=Decimal("0"),
        user_preference=1,
    )
    unopened_later = LotCandidate(
        lot_id="unopened",
        identity="iris",
        grade="perfumery",
        basis="mass",
        available_quantity=Decimal("9"),
        unit="g",
        concentration_fraction=Decimal("0.8"),
        standard_uncertainty=Decimal("0.001"),
        expires_at=NOW + timedelta(days=60),
        opened_at=None,
        safety_passed=True,
        expected_waste=Decimal("7"),
        substitution_cost=Decimal("0"),
        user_preference=5,
    )

    decision = select_best_lot(
        requirement,
        [unsafe_high_concentration, unopened_later, opened_fefo],
        policy,
    )

    assert decision.selected_lot_id == "opened-fefo"
    assert "unsafe" in decision.rejected_lots
    assert decision.rejected_lots["unsafe"] == ("SAFETY_OR_EXPIRY_FAILED",)


def test_a5_lot_selection_fails_closed_on_basis_or_uncertainty():
    requirement = LotRequirement(
        identity="iris",
        grade="perfumery",
        basis="mass",
        required_quantity=Decimal("1"),
        unit="g",
        maximum_standard_uncertainty=Decimal("0.01"),
    )
    candidate = LotCandidate(
        lot_id="bad-basis",
        identity="iris",
        grade="perfumery",
        basis="volume",
        available_quantity=Decimal("5"),
        unit="mL",
        concentration_fraction=Decimal("0.2"),
        standard_uncertainty=Decimal("0.02"),
        expires_at=NOW + timedelta(days=1),
        opened_at=None,
        safety_passed=True,
        expected_waste=Decimal("0"),
        substitution_cost=Decimal("0"),
        user_preference=0,
    )

    decision = select_best_lot(requirement, [candidate], LotPolicy(now=NOW))

    assert decision.selected_lot_id is None
    assert decision.rejected_lots["bad-basis"] == (
        "BASIS_INCOMPARABLE",
        "MEASUREMENT_UNCERTAINTY_EXCEEDED",
    )


def test_a5_state_delta_is_typed_and_rejects_incomparable_commit():
    delta = StateDelta(
        target_line_id="line-1",
        target_identity="iris",
        target_quantity=Decimal("1"),
        selected_stock_quantity=Decimal("5"),
        planned_raw_quantity=Decimal("1"),
        planned_active_quantity=Decimal("0.2"),
        reserved_quantity=Decimal("1"),
        committed_quantity=Decimal("0.98"),
        unit="g",
        basis="mass",
        standard_uncertainty=Decimal("0.002"),
        density_source=None,
        comparable=True,
        incomparability_reason=None,
        substitution_state="EXACT",
        preserved_functions=("orris",),
        lost_functions=(),
        action_state=ActionState.COMMITTED,
    )

    assert delta.committed_quantity == Decimal("0.98")

    with pytest.raises(ValueError, match="incomparability_reason"):
        StateDelta(
            **{
                **delta.as_dict(),
                "comparable": False,
                "incomparability_reason": None,
            }
        )


def test_a5_state_delta_requires_stable_reason_for_unknown_density():
    delta = StateDelta(
        target_line_id="line-2",
        target_identity="iris",
        target_quantity=Decimal("1"),
        selected_stock_quantity=Decimal("5"),
        planned_raw_quantity=Decimal("1"),
        planned_active_quantity=Decimal("0.2"),
        reserved_quantity=Decimal("0"),
        committed_quantity=Decimal("0"),
        unit="mL",
        basis="volume",
        standard_uncertainty=None,
        density_source=None,
        comparable=False,
        incomparability_reason=ComparabilityReason.DENSITY_UNKNOWN,
        substitution_state="UNKNOWN",
        preserved_functions=(),
        lost_functions=("orris",),
        action_state=ActionState.PROPOSED,
    )

    assert delta.incomparability_reason is ComparabilityReason.DENSITY_UNKNOWN
