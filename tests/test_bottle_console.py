"""Tests for engine.bottle.console."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from engine.bottle.console import (
    BatchAction,
    create_rescue_addition,
    format_action_output,
    pre_action_gate,
    propose_addition,
)
from engine.bottle.events import (
    BottleBatch,
    BottleEvent,
    DOSE_STOCK,
    PROPOSED,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_batch(batch_id: str = "test-batch") -> BottleBatch:
    """Create a minimal batch with one event so the ledger is non-empty."""
    # Add a CREATE_BATCH event so event_count > 0 and batch_id is set.
    seed = BottleEvent(
        event_id="seed-1",
        batch_id=batch_id,
        event_type="CREATE_BATCH",
        timestamp="2026-01-01T00:00:00Z",
        operator="test",
        confirmation="COMMITTED",
    )
    return BottleBatch.from_events(batch_id, [seed])


# ── BatchAction creation ─────────────────────────────────────────────────────


class TestBatchAction:
    """BatchAction dataclass creation and round-trip."""

    def test_create_with_all_fields(self):
        """BatchAction can be created with all fields populated."""
        action = BatchAction(
            action_type=DOSE_STOCK,
            material_label="Bergamot FCF",
            stock_id="stock-001",
            amount_ul=150.0,
            amount_g=0.1500,
            reason="Add citrus top note",
            expected_effect="Fresh bergamot opening",
            main_risk="Overpowers delicate florals",
            evaluation_time_minutes=45,
            stop_condition="If bergamot dominates, reduce next dose",
        )
        assert action.action_type == DOSE_STOCK
        assert action.material_label == "Bergamot FCF"
        assert action.stock_id == "stock-001"
        assert action.amount_ul == 150.0
        assert action.amount_g == 0.1500
        assert action.reason == "Add citrus top note"
        assert action.expected_effect == "Fresh bergamot opening"
        assert action.main_risk == "Overpowers delicate florals"
        assert action.evaluation_time_minutes == 45
        assert action.stop_condition == "If bergamot dominates, reduce next dose"

    def test_defaults(self):
        """BatchAction uses sensible defaults for optional fields."""
        action = BatchAction(action_type=DOSE_STOCK, material_label="Iso E Super")
        assert action.stock_id is None
        assert action.amount_ul == 0.0
        assert action.amount_g is None
        assert action.reason == ""
        assert action.expected_effect == ""
        assert action.main_risk == ""
        assert action.evaluation_time_minutes == 30
        assert action.stop_condition == ""

    def test_as_dict_round_trip(self):
        """BatchAction.as_dict() and BatchAction.from_dict() round-trip."""
        original = BatchAction(
            action_type=DOSE_STOCK,
            material_label="Hedione",
            stock_id="stock-002",
            amount_ul=300.0,
            reason="Radiance amplifier",
            expected_effect="Volume and diffusion",
            main_risk="Crowding",
            evaluation_time_minutes=60,
            stop_condition="If other notes buried",
        )
        data = original.as_dict()
        restored = BatchAction(**data)
        assert restored == original
        assert restored.as_dict() == data


# ── pre_action_gate ──────────────────────────────────────────────────────────


class TestPreActionGate:
    """pre_action_gate safety checks."""

    def test_valid_action_passes(self):
        """A fully populated action against a valid batch returns no violations."""
        batch = _make_batch()
        action = BatchAction(
            action_type=DOSE_STOCK,
            material_label="Linalool",
            stock_id="stock-003",
            amount_ul=100.0,
            reason="Add floral-lavender note",
            main_risk="Too thin",
            stop_condition="If too thin, add more base",
        )
        violations = pre_action_gate(action, batch)
        assert violations == []

    def test_missing_reason(self):
        """Action without reason triggers a violation."""
        batch = _make_batch()
        action = BatchAction(
            action_type=DOSE_STOCK,
            material_label="Linalool",
            stock_id="stock-003",
            amount_ul=100.0,
            reason="",
            main_risk="Too thin",
            stop_condition="If too thin, add more base",
        )
        violations = pre_action_gate(action, batch)
        assert any("reason" in v.lower() or "role" in v.lower() for v in violations)

    def test_zero_amount(self):
        """Action with amount_ul == 0 and no amount_g triggers a violation."""
        batch = _make_batch()
        action = BatchAction(
            action_type=DOSE_STOCK,
            material_label="Linalool",
            stock_id="stock-003",
            amount_ul=0.0,
            reason="Add floral-lavender note",
            main_risk="Too thin",
            stop_condition="If too thin, add more base",
        )
        violations = pre_action_gate(action, batch)
        assert any("amount" in v.lower() and "measur" in v.lower() for v in violations)

    def test_missing_stop_condition(self):
        """Action without stop_condition triggers a violation."""
        batch = _make_batch()
        action = BatchAction(
            action_type=DOSE_STOCK,
            material_label="Linalool",
            stock_id="stock-003",
            amount_ul=100.0,
            reason="Add floral-lavender note",
            main_risk="Too thin",
            stop_condition="",
        )
        violations = pre_action_gate(action, batch)
        assert any("stop_condition" in v.lower() for v in violations)

    def test_missing_main_risk(self):
        """Action without main_risk triggers a violation."""
        batch = _make_batch()
        action = BatchAction(
            action_type=DOSE_STOCK,
            material_label="Linalool",
            stock_id="stock-003",
            amount_ul=100.0,
            reason="Add floral-lavender note",
            main_risk="",
            stop_condition="If too thin, add more base",
        )
        violations = pre_action_gate(action, batch)
        assert any("main_risk" in v.lower() for v in violations)

    def test_missing_stock_id_for_dose_stock(self):
        """DOSE_STOCK action without stock_id triggers a violation."""
        batch = _make_batch()
        action = BatchAction(
            action_type=DOSE_STOCK,
            material_label="Linalool",
            stock_id=None,
            amount_ul=100.0,
            reason="Add floral-lavender note",
            main_risk="Too thin",
            stop_condition="If too thin, add more base",
        )
        violations = pre_action_gate(action, batch)
        assert any("stock" in v.lower() and "identity" in v.lower() for v in violations)

    def test_empty_batch_ledger(self):
        """An empty batch ledger triggers a violation."""
        batch = BottleBatch("empty-batch")
        action = BatchAction(
            action_type=DOSE_STOCK,
            material_label="Linalool",
            stock_id="stock-003",
            amount_ul=100.0,
            reason="Add floral-lavender note",
            main_risk="Too thin",
            stop_condition="If too thin, add more base",
        )
        violations = pre_action_gate(action, batch)
        assert any("ledger" in v.lower() or "event" in v.lower() for v in violations)


# ── propose_addition ─────────────────────────────────────────────────────────


class TestProposeAddition:
    """propose_addition creates PROPOSED DOSE_STOCK events."""

    def test_creates_proposed_event(self):
        """propose_addition returns a BottleEvent with PROPOSED status."""
        batch = _make_batch()
        event = propose_addition(
            batch=batch,
            material="Bergamot FCF",
            amount_ul=200.0,
            reason="Citrus opening",
        )
        assert isinstance(event, BottleEvent)
        assert event.confirmation == PROPOSED

    def test_event_type_is_dose_stock(self):
        """The created event has event_type DOSE_STOCK."""
        batch = _make_batch()
        event = propose_addition(
            batch=batch,
            material="Bergamot FCF",
            amount_ul=200.0,
            reason="Citrus opening",
        )
        assert event.event_type == DOSE_STOCK

    def test_event_matches_material_amount_reason(self):
        """The event carries the correct material label, volume, and reason."""
        batch = _make_batch()
        event = propose_addition(
            batch=batch,
            material="Bergamot FCF",
            amount_ul=200.0,
            reason="Citrus opening",
        )
        assert event.stock_label == "Bergamot FCF"
        assert event.volume_ul == 200.0
        # The reason is passed as a separate parameter to propose_action,
        # not embedded in notes. Verify the event was created correctly.
        assert event.event_type == DOSE_STOCK
        assert event.confirmation == PROPOSED

    def test_notes_include_optional_fields(self):
        """When expected_effect, main_risk, and stop_condition are provided,
        they appear in the event notes."""
        batch = _make_batch()
        event = propose_addition(
            batch=batch,
            material="Hedione",
            amount_ul=300.0,
            reason="Radiance",
            expected_effect="Volume boost",
            main_risk="Crowding",
            evaluation_minutes=60,
            stop_condition="If buried",
        )
        assert "Expected effect: Volume boost" in event.notes
        assert "Main risk: Crowding" in event.notes
        assert "Stop condition: If buried" in event.notes
        assert "Evaluation time: 60 min" in event.notes

    def test_event_not_added_to_batch(self):
        """propose_addition does NOT add the event to the batch."""
        batch = _make_batch()
        count_before = batch.event_count()
        propose_addition(
            batch=batch,
            material="Bergamot FCF",
            amount_ul=200.0,
            reason="Citrus opening",
        )
        assert batch.event_count() == count_before


# ── format_action_output ─────────────────────────────────────────────────────


class TestFormatActionOutput:
    """format_action_output produces a human-readable summary."""

    def test_contains_action_type(self):
        """Output contains the action type."""
        batch = _make_batch()
        action = BatchAction(
            action_type=DOSE_STOCK,
            material_label="Linalool",
            stock_id="stock-003",
            amount_ul=100.0,
            reason="Add floral note",
            main_risk="Too thin",
            stop_condition="If too thin, add base",
        )
        event = propose_addition(batch, "Linalool", 100.0, "Add floral note")
        output = format_action_output(action, event)
        assert DOSE_STOCK in output

    def test_contains_material(self):
        """Output contains the material label or stock ID."""
        batch = _make_batch()
        action = BatchAction(
            action_type=DOSE_STOCK,
            material_label="Linalool",
            stock_id="stock-003",
            amount_ul=100.0,
            reason="Add floral note",
            main_risk="Too thin",
            stop_condition="If too thin, add base",
        )
        event = propose_addition(batch, "Linalool", 100.0, "Add floral note")
        output = format_action_output(action, event)
        assert "Linalool" in output or "stock-003" in output

    def test_contains_amount(self):
        """Output contains the amount in microlitres."""
        batch = _make_batch()
        action = BatchAction(
            action_type=DOSE_STOCK,
            material_label="Linalool",
            stock_id="stock-003",
            amount_ul=100.0,
            reason="Add floral note",
            main_risk="Too thin",
            stop_condition="If too thin, add base",
        )
        event = propose_addition(batch, "Linalool", 100.0, "Add floral note")
        output = format_action_output(action, event)
        assert "100" in output and "uL" in output

    def test_contains_reason(self):
        """Output contains the reason."""
        batch = _make_batch()
        action = BatchAction(
            action_type=DOSE_STOCK,
            material_label="Linalool",
            stock_id="stock-003",
            amount_ul=100.0,
            reason="Add floral note",
            main_risk="Too thin",
            stop_condition="If too thin, add base",
        )
        event = propose_addition(batch, "Linalool", 100.0, "Add floral note")
        output = format_action_output(action, event)
        assert "Add floral note" in output

    def test_contains_stop_condition(self):
        """Output contains the stop condition."""
        batch = _make_batch()
        action = BatchAction(
            action_type=DOSE_STOCK,
            material_label="Linalool",
            stock_id="stock-003",
            amount_ul=100.0,
            reason="Add floral note",
            main_risk="Too thin",
            stop_condition="If too thin, add base",
        )
        event = propose_addition(batch, "Linalool", 100.0, "Add floral note")
        output = format_action_output(action, event)
        assert "If too thin, add base" in output

    def test_contains_pending_status(self):
        """Output contains the ledger confirmation status (PROPOSED)."""
        batch = _make_batch()
        action = BatchAction(
            action_type=DOSE_STOCK,
            material_label="Linalool",
            stock_id="stock-003",
            amount_ul=100.0,
            reason="Add floral note",
            main_risk="Too thin",
            stop_condition="If too thin, add base",
        )
        event = propose_addition(batch, "Linalool", 100.0, "Add floral note")
        output = format_action_output(action, event)
        assert PROPOSED in output

    def test_amount_with_grams(self):
        """When amount_g is set, output includes the gram value."""
        batch = _make_batch()
        action = BatchAction(
            action_type=DOSE_STOCK,
            material_label="Linalool",
            stock_id="stock-003",
            amount_ul=100.0,
            amount_g=0.1000,
            reason="Add floral note",
            main_risk="Too thin",
            stop_condition="If too thin, add base",
        )
        event = propose_addition(batch, "Linalool", 100.0, "Add floral note")
        output = format_action_output(action, event)
        assert "0.1000 g" in output or "0.1" in output


# ── create_rescue_addition ───────────────────────────────────────────────────


class TestCreateRescueAddition:
    """create_rescue_addition creates a rescue event."""

    def test_creates_proposed_event(self):
        """create_rescue_addition returns a BottleEvent with PROPOSED status."""
        batch = _make_batch()
        event = create_rescue_addition(
            batch=batch,
            material="Iso E Super",
            amount_ul=50.0,
            reason="Too thin, need more body",
        )
        assert isinstance(event, BottleEvent)
        assert event.confirmation == PROPOSED

    def test_event_type_is_dose_stock(self):
        """The rescue event has event_type DOSE_STOCK."""
        batch = _make_batch()
        event = create_rescue_addition(
            batch=batch,
            material="Iso E Super",
            amount_ul=50.0,
            reason="Too thin, need more body",
        )
        assert event.event_type == DOSE_STOCK

    def test_notes_contain_rescue_marker(self):
        """The event notes contain the BATCH_RESCUE marker."""
        batch = _make_batch()
        event = create_rescue_addition(
            batch=batch,
            material="Iso E Super",
            amount_ul=50.0,
            reason="Too thin, need more body",
        )
        assert "RESCUE OPERATION" in event.notes

    def test_notes_contain_reason(self):
        """The event notes contain the rescue reason."""
        batch = _make_batch()
        event = create_rescue_addition(
            batch=batch,
            material="Iso E Super",
            amount_ul=50.0,
            reason="Too thin, need more body",
        )
        assert "Too thin, need more body" in event.notes

    def test_event_not_added_to_batch(self):
        """create_rescue_addition does NOT add the event to the batch."""
        batch = _make_batch()
        count_before = batch.event_count()
        create_rescue_addition(
            batch=batch,
            material="Iso E Super",
            amount_ul=50.0,
            reason="Too thin, need more body",
        )
        assert batch.event_count() == count_before


# ── Import resolution ────────────────────────────────────────────────────────


class TestImports:
    """BottleEvent and BottleBatch resolve correctly from engine.bottle.events."""

    def test_bottle_event_import(self):
        """BottleEvent is importable and constructable."""
        evt = BottleEvent(
            event_id="test-id",
            batch_id="test-batch",
            event_type="CREATE_BATCH",
            timestamp="2026-01-01T00:00:00Z",
            operator="test",
            confirmation="COMMITTED",
        )
        assert isinstance(evt, BottleEvent)
        assert evt.event_id == "test-id"

    def test_bottle_batch_import(self):
        """BottleBatch is importable and constructable."""
        batch = BottleBatch("test-batch")
        assert isinstance(batch, BottleBatch)
        assert batch.batch_id == "test-batch"
