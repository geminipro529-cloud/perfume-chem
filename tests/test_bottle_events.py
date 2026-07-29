"""Tests for engine.bottle.events."""

from __future__ import annotations
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.bottle.events import (
    BottleEvent,
    BottleBatch,
    compute_replay_state,
    DOSE_STOCK,
    ADD_SOLVENT,
    CLOSE_BATCH,
    TARE_CONTAINER,
    CORRECT_ENTRY,
    PROPOSED,
    COMMITTED,
)


def test_chained_correction_replays():
    # Add material A
    e1 = BottleEvent(
        event_id="evt1",
        batch_id="b1",
        event_type=DOSE_STOCK,
        timestamp="2026-01-01T00:00:00Z",
        operator="test",
        stock_label="Iso E Super",
        intended_mass_g=1.0,
        confirmation=COMMITTED,
    )
    # Correct to 1.5
    e2 = BottleEvent(
        event_id="evt2",
        batch_id="b1",
        event_type=CORRECT_ENTRY,
        timestamp="2026-01-01T00:01:00Z",
        operator="test",
        stock_label="Iso E Super",
        intended_mass_g=1.5,
        confirmation=COMMITTED,
        correction_ref="evt1",
    )
    # Correct the correction to 1.2
    e3 = BottleEvent(
        event_id="evt3",
        batch_id="b1",
        event_type=CORRECT_ENTRY,
        timestamp="2026-01-01T00:02:00Z",
        operator="test",
        stock_label="Iso E Super",
        intended_mass_g=1.2,
        confirmation=COMMITTED,
        correction_ref="evt2",
    )
    state = compute_replay_state([e1, e2, e3])
    assert abs(state.get("Iso E Super", 0.0) - 1.2) < 0.001


def test_correction_cycle_detected():
    e1 = BottleEvent(
        event_id="evt1",
        batch_id="b1",
        event_type=CORRECT_ENTRY,
        timestamp="2026-01-01T00:00:00Z",
        operator="test",
        stock_label="X",
        intended_mass_g=1.0,
        confirmation=COMMITTED,
        correction_ref="evt2",
    )
    e2 = BottleEvent(
        event_id="evt2",
        batch_id="b1",
        event_type=CORRECT_ENTRY,
        timestamp="2026-01-01T00:01:00Z",
        operator="test",
        stock_label="X",
        intended_mass_g=1.0,
        confirmation=COMMITTED,
        correction_ref="evt1",
    )
    import pytest

    with pytest.raises(ValueError):
        compute_replay_state([e1, e2])


def test_add_solvent_tracks_separately():
    e1 = BottleEvent(
        event_id="e1",
        batch_id="b1",
        event_type=DOSE_STOCK,
        timestamp="2026",
        operator="t",
        stock_label="Iso E Super",
        intended_mass_g=1.0,
        confirmation=COMMITTED,
    )
    e2 = BottleEvent(
        event_id="e2",
        batch_id="b1",
        event_type=ADD_SOLVENT,
        timestamp="2026",
        operator="t",
        stock_label="Ethanol",
        intended_mass_g=9.0,
        confirmation=COMMITTED,
    )
    state = compute_replay_state([e1, e2])
    assert abs(state.get("Iso E Super", 0.0) - 1.0) < 0.001
    assert abs(state.get("_solvent_mass_g", 0.0) - 9.0) < 0.001


def test_close_batch_blocks_new_events():
    close_evt = BottleEvent(
        event_id="e1",
        batch_id="b1",
        event_type=CLOSE_BATCH,
        timestamp="2026",
        operator="t",
        confirmation=COMMITTED,
    )
    batch = BottleBatch.from_events("b1", [close_evt])
    assert batch.is_closed

    new_evt = BottleEvent(
        event_id="e2",
        batch_id="b1",
        event_type=DOSE_STOCK,
        timestamp="2026",
        operator="t",
        stock_label="X",
        intended_mass_g=1.0,
        confirmation=COMMITTED,
    )
    import pytest

    with pytest.raises(ValueError, match="LabService"):
        batch.add_event(new_evt)


def test_tare_container_affects_total():
    e1 = BottleEvent(
        event_id="e1",
        batch_id="b1",
        event_type=DOSE_STOCK,
        timestamp="2026",
        operator="t",
        stock_label="X",
        intended_mass_g=5.0,
        confirmation=COMMITTED,
    )
    batch = BottleBatch.from_events("b1", [e1], container_tare_g=10.0)
    state = batch.replay()
    assert "_tare_g" in state and state["_tare_g"] == 10.0
