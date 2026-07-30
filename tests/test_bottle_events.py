"""Tests for engine.bottle.events."""

from __future__ import annotations

from engine.bottle.events import (
    ADD_MATERIAL,
    ADD_SOLVENT,
    CLOSE_BATCH,
    COMMITTED,
    CORRECT_ENTRY,
    DILUTE,
    DOSE_STOCK,
    EVENT_SEMANTICS,
    PROPOSED,
    TARE_CONTAINER,
    TRANSFER,
    BottleBatch,
    BottleEvent,
    compute_replay_state,
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


def _committed_event(
    event_id: str,
    event_type: str,
    *,
    sequence: int,
    mass_g: float | None = None,
    stock_label: str = "",
    idempotency_key: str | None = None,
    **kwargs,
) -> BottleEvent:
    return BottleEvent(
        event_id=event_id,
        batch_id="a5-batch",
        event_type=event_type,
        timestamp=f"2026-07-30T00:00:{sequence:02d}Z",
        stock_label=stock_label,
        measured_mass_g=mass_g,
        confirmation=COMMITTED,
        sequence=sequence,
        idempotency_key=idempotency_key or f"a5-command-{sequence}",
        **kwargs,
    )


def test_a5_semantics_table_covers_every_declared_event_type():
    assert set(EVENT_SEMANTICS) == {
        "CREATE_BATCH",
        "TARE_CONTAINER",
        "ADD_MATERIAL",
        "DOSE_STOCK",
        "ADD_SOLVENT",
        "REMOVE_SAMPLE",
        "TRANSFER",
        "DILUTE",
        "MIX",
        "REST_START",
        "REST_END",
        "SAMPLE",
        "EVALUATE",
        "CORRECT_ENTRY",
        "CLOSE_BATCH",
    }
    assert EVENT_SEMANTICS[ADD_MATERIAL].changes_chemical_contents is True
    assert EVENT_SEMANTICS[TARE_CONTAINER].changes_chemical_contents is False
    assert EVENT_SEMANTICS[DILUTE].derived_only is True


def test_a5_add_material_separates_composition_and_solvent_is_not_odorant():
    events = [
        _committed_event(
            "material",
            ADD_MATERIAL,
            sequence=1,
            mass_g=10.0,
            stock_label="Iris stock",
            active_fraction=0.20,
            carrier_fraction=0.10,
            solvent_fraction=0.65,
            unallocated_fraction=0.05,
        ),
        _committed_event(
            "solvent",
            ADD_SOLVENT,
            sequence=2,
            mass_g=30.0,
            stock_label="Ethanol",
        ),
    ]

    state = compute_replay_state(events)

    assert state["Iris stock"] == 10.0
    assert state["_composition_mass_g"] == {
        "active": 2.0,
        "carrier": 1.0,
        "solvent": 36.5,
        "unallocated": 0.5,
    }
    assert state["_solvent_mass_g"] == 36.5


def test_a5_dilution_is_derived_from_additions_and_has_no_mass_effect():
    events = [
        _committed_event(
            "material",
            ADD_MATERIAL,
            sequence=1,
            mass_g=1.0,
            stock_label="Material",
            active_fraction=1.0,
        ),
        _committed_event(
            "solvent",
            ADD_SOLVENT,
            sequence=2,
            mass_g=9.0,
            stock_label="Ethanol",
        ),
        _committed_event(
            "dilution",
            DILUTE,
            sequence=3,
            source_event_ids=("material", "solvent"),
        ),
    ]

    state = compute_replay_state(events)

    assert state["_solvent_mass_g"] == 9.0
    assert state["_derived_concentration_fraction"] == 0.1
    assert state["_dilution_history"] == [
        {
            "event_id": "dilution",
            "source_event_ids": ("material", "solvent"),
            "concentration_fraction": 0.1,
        }
    ]


def test_a5_dilution_rejects_manually_overwritten_mass():
    event = _committed_event(
        "dilution",
        DILUTE,
        sequence=1,
        mass_g=9.0,
    )

    import pytest

    with pytest.raises(ValueError, match="derived-only"):
        compute_replay_state([event])


def test_a5_tare_event_changes_reference_metadata_not_contents():
    events = [
        _committed_event(
            "material",
            ADD_MATERIAL,
            sequence=1,
            mass_g=2.0,
            stock_label="Material",
            active_fraction=1.0,
        ),
        _committed_event(
            "tare",
            TARE_CONTAINER,
            sequence=2,
            tare_mass_g=12.25,
        ),
    ]

    state = compute_replay_state(events, container_tare_g=10.0)

    assert state["Material"] == 2.0
    assert state["_tare_g"] == 12.25


def test_a5_stream_sequence_is_contiguous_and_idempotency_keys_are_unique():
    first = _committed_event(
        "first",
        ADD_MATERIAL,
        sequence=1,
        mass_g=1.0,
        stock_label="Material",
        active_fraction=1.0,
        idempotency_key="same-command",
    )
    gap = _committed_event(
        "gap",
        ADD_SOLVENT,
        sequence=3,
        mass_g=1.0,
    )
    duplicate = _committed_event(
        "duplicate",
        ADD_SOLVENT,
        sequence=2,
        mass_g=1.0,
        idempotency_key="same-command",
    )

    import pytest

    with pytest.raises(ValueError, match="contiguous"):
        compute_replay_state([first, gap])
    with pytest.raises(ValueError, match="idempotency"):
        compute_replay_state([first, duplicate])


def test_a5_only_committed_events_change_physical_state():
    proposed = BottleEvent(
        event_id="proposal",
        batch_id="a5-batch",
        event_type=ADD_MATERIAL,
        timestamp="2026-07-30T00:00:00Z",
        stock_label="Material",
        measured_mass_g=1.0,
        active_fraction=1.0,
        confirmation=PROPOSED,
        sequence=1,
        idempotency_key="proposal",
    )

    state = compute_replay_state([proposed])

    assert "Material" not in state
    assert state["_applied_event_count"] == 0


def test_a5_closed_stream_blocks_ordinary_physical_events_but_allows_correction():
    material = _committed_event(
        "material",
        ADD_MATERIAL,
        sequence=1,
        mass_g=1.0,
        stock_label="Material",
        active_fraction=1.0,
    )
    closed = _committed_event("close", CLOSE_BATCH, sequence=2)
    addition = _committed_event(
        "late",
        ADD_SOLVENT,
        sequence=3,
        mass_g=1.0,
    )
    correction = _committed_event(
        "correction",
        CORRECT_ENTRY,
        sequence=3,
        mass_g=0.9,
        correction_ref="material",
    )

    import pytest

    with pytest.raises(ValueError, match="closed"):
        compute_replay_state([material, closed, addition])
    assert compute_replay_state([material, closed, correction])["Material"] == 0.9


def test_a5_transfer_event_requires_transaction_and_counterparty_metadata():
    import pytest

    with pytest.raises(ValueError, match="transaction_id"):
        _committed_event(
            "transfer",
            TRANSFER,
            sequence=1,
            mass_g=1.0,
            related_batch_id="destination",
        )
