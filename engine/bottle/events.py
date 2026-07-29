"""Event-sourced bottle ledger.

Physical bottle state is reconstructed from immutable events. Never delete an
event — correct it with a compensating event. AI can only propose actions; the
user confirms and measures to commit.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, cast

from engine.domain_errors import EventStreamError, ReconstructionInputError

# ── Event type constants ────────────────────────────────────────────────────

CREATE_BATCH = "CREATE_BATCH"
TARE_CONTAINER = "TARE_CONTAINER"
DOSE_STOCK = "DOSE_STOCK"
ADD_SOLVENT = "ADD_SOLVENT"
REMOVE_SAMPLE = "REMOVE_SAMPLE"
TRANSFER = "TRANSFER"
DILUTE = "DILUTE"
MIX = "MIX"
REST_START = "REST_START"
REST_END = "REST_END"
SAMPLE = "SAMPLE"
EVALUATE = "EVALUATE"
CORRECT_ENTRY = "CORRECT_ENTRY"
CLOSE_BATCH = "CLOSE_BATCH"

_ALL_EVENT_TYPES = frozenset(
    {
        CREATE_BATCH,
        TARE_CONTAINER,
        DOSE_STOCK,
        ADD_SOLVENT,
        REMOVE_SAMPLE,
        TRANSFER,
        DILUTE,
        MIX,
        REST_START,
        REST_END,
        SAMPLE,
        EVALUATE,
        CORRECT_ENTRY,
        CLOSE_BATCH,
    }
)


# ── Confirmation status constants ───────────────────────────────────────────

PROPOSED = "PROPOSED"  # AI or user suggested
CONFIRMED = "CONFIRMED"  # user approved
MEASURED = "MEASURED"  # actual measurement recorded
COMMITTED = "COMMITTED"  # final, immutable except via CORRECT_ENTRY

_ALL_CONFIRMATION_STATUSES = frozenset(
    {
        PROPOSED,
        CONFIRMED,
        MEASURED,
        COMMITTED,
    }
)


# ── BottleEvent dataclass ───────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class BottleEvent:
    """One immutable event in the bottle ledger.

    Parameters
    ----------
    event_id : str
        UUID string uniquely identifying this event.
    batch_id : str
        Identifier of the batch this event belongs to.
    event_type : str
        One of the event type constants defined above.
    timestamp : str
        ISO 8601 formatted timestamp.
    operator : str
        Who performed the action (default "").
    stock_id : str | None
        Material identity ID from ``engine.identity.resolver`` (default None).
    stock_label : str
        What the label on the stock bottle says (default "").
    measured_mass_g : float | None
        Actual measured mass in grams (default None).
    intended_mass_g : float | None
        Intended target mass in grams (default None).
    concentration : float | None
        Stock concentration as a mass fraction (default None).
    volume_ul : float | None
        Volume in microlitres if measured volumetrically (default None).
    notes : str
        Free-text notes (default "").
    confirmation : str
        One of PROPOSED, CONFIRMED, MEASURED, COMMITTED (default PROPOSED).
    confirmed_by : str
        Name or identifier of the person who confirmed (default "").
    correction_ref : str | None
        If this is a CORRECT_ENTRY, references the ``event_id`` of the
        original event being corrected (default None).
    """

    event_id: str
    batch_id: str
    event_type: str
    timestamp: str
    operator: str = ""
    stock_id: str | None = None
    stock_label: str = ""
    measured_mass_g: float | None = None
    intended_mass_g: float | None = None
    concentration: float | None = None
    volume_ul: float | None = None
    notes: str = ""
    confirmation: str = PROPOSED
    confirmed_by: str = ""
    correction_ref: str | None = None
    sequence: int | None = None

    def __post_init__(self) -> None:
        if self.event_type not in _ALL_EVENT_TYPES:
            raise ValueError(
                f"Unknown event_type {self.event_type!r}. Must be one of {sorted(_ALL_EVENT_TYPES)}"
            )
        if self.confirmation not in _ALL_CONFIRMATION_STATUSES:
            raise ValueError(
                f"Unknown confirmation {self.confirmation!r}. "
                f"Must be one of {sorted(_ALL_CONFIRMATION_STATUSES)}"
            )
        if self.sequence is not None and self.sequence <= 0:
            raise EventStreamError(
                f"event sequence must be positive, got {self.sequence!r}"
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "batch_id": self.batch_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "operator": self.operator,
            "stock_id": self.stock_id,
            "stock_label": self.stock_label,
            "measured_mass_g": self.measured_mass_g,
            "intended_mass_g": self.intended_mass_g,
            "concentration": self.concentration,
            "volume_ul": self.volume_ul,
            "notes": self.notes,
            "confirmation": self.confirmation,
            "confirmed_by": self.confirmed_by,
            "correction_ref": self.correction_ref,
            "sequence": self.sequence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BottleEvent:
        return cls(
            event_id=str(data["event_id"]),
            batch_id=str(data["batch_id"]),
            event_type=str(data["event_type"]),
            timestamp=str(data["timestamp"]),
            operator=str(data.get("operator") or ""),
            stock_id=str(data["stock_id"]) if data.get("stock_id") else None,
            stock_label=str(data.get("stock_label") or ""),
            measured_mass_g=float(data["measured_mass_g"])
            if data.get("measured_mass_g") is not None
            else None,
            intended_mass_g=float(data["intended_mass_g"])
            if data.get("intended_mass_g") is not None
            else None,
            concentration=float(data["concentration"])
            if data.get("concentration") is not None
            else None,
            volume_ul=float(data["volume_ul"]) if data.get("volume_ul") is not None else None,
            notes=str(data.get("notes") or ""),
            confirmation=str(data.get("confirmation", PROPOSED)),
            confirmed_by=str(data.get("confirmed_by") or ""),
            correction_ref=str(data["correction_ref"]) if data.get("correction_ref") else None,
            sequence=int(data["sequence"]) if data.get("sequence") is not None else None,
        )

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), indent=2, default=str)


# ── BottleBatch class ───────────────────────────────────────────────────────


@dataclass(slots=True)
class BottleBatch:
    """An event-sourced bottle batch.

    The physical state of the bottle is reconstructed by replaying all events
    in order. Events are never deleted — corrections are applied via
    ``CORRECT_ENTRY`` compensating events.
    """

    batch_id: str
    batch_name: str = ""
    container_tare_g: float = 0.0
    _events: list[BottleEvent] = field(default_factory=list)

    # ── Event management ────────────────────────────────────────────────

    @property
    def is_closed(self) -> bool:
        """Return True if a CLOSE_BATCH event exists in the event log."""
        return any(e.event_type == CLOSE_BATCH for e in self._events)

    def add_event(self, event: BottleEvent) -> None:
        """Append an event to the event log.

        Raises
        ------
        ValueError
            If the batch is already closed (a CLOSE_BATCH event exists).
            Use CORRECT_ENTRY for corrections to closed batches.
        """
        for existing in self._events:
            if existing.event_id == event.event_id:
                if existing == event:
                    return
                raise EventStreamError(
                    f"conflicting duplicate event_id {event.event_id!r}"
                )
        if self.is_closed:
            raise ValueError(
                "Batch is closed — cannot add events. Use CORRECT_ENTRY for corrections."
            )
        if event.batch_id != self.batch_id:
            raise ValueError(
                f"Event batch_id {event.batch_id!r} does not match "
                f"this batch's batch_id {self.batch_id!r}"
            )
        if self._events:
            previous = self._events[-1]
            if (previous.sequence is None) != (event.sequence is None):
                raise EventStreamError(
                    "event stream cannot mix sequenced and unsequenced events"
                )
            if (
                previous.sequence is not None
                and event.sequence is not None
                and event.sequence <= previous.sequence
            ):
                raise EventStreamError(
                    f"stale sequence {event.sequence!r}; "
                    f"latest sequence is {previous.sequence!r}"
                )
        self._events.append(event)

    def event_count(self) -> int:
        """Return the total number of events in the log."""
        return len(self._events)

    def last_event(self) -> BottleEvent | None:
        """Return the most recent event, or None if the log is empty."""
        if not self._events:
            return None
        return self._events[-1]

    # ── State reconstruction ────────────────────────────────────────────

    def replay(self) -> dict[str, object]:
        """Recompute current bottle state from all events.

        Returns a dictionary with keys:
            - batch_id
            - batch_name
            - container_tare_g
            - total_mass_g : float
            - materials : dict[str, float]  (material label -> mass in grams)
            - event_count : int
            - last_event_type : str | None
            - is_empty : bool
            - _solvent_mass_g : float
            - _dilution_history : list
            - _tare_g : float
            - _batch_closed : bool
        """
        state = compute_replay_state(self._events, container_tare_g=self.container_tare_g)
        # Extract only material masses (non-underscore keys) for total calculation.
        material_masses = {k: v for k, v in state.items() if not k.startswith("_")}
        total_mass = sum(cast(list[float], list(material_masses.values())))
        last_ev = self.last_event()

        return {
            "batch_id": self.batch_id,
            "batch_name": self.batch_name,
            "container_tare_g": self.container_tare_g,
            "total_mass_g": total_mass,
            "materials": material_masses,
            "event_count": len(self._events),
            "last_event_type": last_ev.event_type if last_ev else None,
            "is_empty": total_mass <= 0.0,
            "_solvent_mass_g": state.get("_solvent_mass_g", 0.0),
            "_dilution_history": state.get("_dilution_history", []),
            "_tare_g": state.get("_tare_g", 0.0),
            "_batch_closed": state.get("_batch_closed", False),
        }

    def replay_full(self) -> dict[str, Any]:
        """Recompute full bottle state including all metadata.

        Returns the raw dict from ``compute_replay_state`` with all material
        masses and underscore-prefixed metadata keys (solvent mass, dilution
        history, tare, closed status).
        """
        return compute_replay_state(self._events, container_tare_g=self.container_tare_g)

    def current_materials(self) -> dict[str, float]:
        """Return a mapping of material label -> current mass in grams."""
        state = compute_replay_state(self._events, container_tare_g=self.container_tare_g)
        return {k: v for k, v in state.items() if not k.startswith("_")}

    def current_total_mass_g(self) -> float:
        """Return the total mass of all materials currently in the bottle."""
        return sum(self.current_materials().values())

    def is_empty(self) -> bool:
        """Return True if the bottle contains no measurable mass."""
        return self.current_total_mass_g() <= 0.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BottleBatch:
        events_raw = data.get("_events") or data.get("events") or ()
        events = [BottleEvent.from_dict(e) if isinstance(e, dict) else e for e in events_raw]
        return cls(
            batch_id=str(data["batch_id"]),
            batch_name=str(data.get("batch_name") or ""),
            container_tare_g=float(data.get("container_tare_g", 0.0)),
            _events=events,
        )


# ── Action lifecycle helpers ────────────────────────────────────────────────


def propose_action(
    batch: BottleBatch,
    action_type: str,
    *,
    stock_id: str | None = None,
    stock_label: str = "",
    intended_mass_g: float | None = None,
    concentration: float | None = None,
    volume_ul: float | None = None,
    notes: str = "",
    operator: str = "",
) -> BottleEvent:
    """Create a proposed event (confirmation=PROPOSED).

    Parameters
    ----------
    batch : BottleBatch
        The batch this action applies to.
    action_type : str
        One of the event type constants (e.g. ``DOSE_STOCK``).
    stock_id : str | None
        Material identity ID.
    stock_label : str
        Label on the stock bottle.
    intended_mass_g : float | None
        Intended mass in grams.
    concentration : float | None
        Stock concentration as mass fraction.
    volume_ul : float | None
        Volume in microlitres.
    notes : str
        Free-text notes.
    operator : str
        Who is proposing the action.

    Returns
    -------
    BottleEvent
        A new event with confirmation set to PROPOSED. The caller must
        explicitly add it to the batch via ``batch.add_event()``.
    """
    event = BottleEvent(
        event_id=str(uuid.uuid4()),
        batch_id=batch.batch_id,
        event_type=action_type,
        timestamp=datetime.now(timezone.utc).isoformat(),
        operator=operator,
        stock_id=stock_id,
        stock_label=stock_label,
        intended_mass_g=intended_mass_g,
        concentration=concentration,
        volume_ul=volume_ul,
        notes=notes,
        confirmation=PROPOSED,
    )
    return event


def confirm_action(
    batch: BottleBatch,
    event_id: str,
    measured_mass_g: float | None = None,
    operator: str = "",
) -> BottleEvent:
    """Confirm a proposed action with an optional measurement.

    Looks up the proposed event by ``event_id`` in the batch's event log.
    Creates a new event with the same parameters but with confirmation
    advanced:

    - If ``measured_mass_g`` is provided: confirmation becomes **MEASURED**
      and the measured mass is recorded.
    - If ``measured_mass_g`` is *not* provided: confirmation becomes
      **CONFIRMED** (user approved without recording a measurement).

    The original proposed event remains in the log unchanged.

    Parameters
    ----------
    batch : BottleBatch
        The batch containing the proposed event.
    event_id : str
        The ``event_id`` of the proposed event to confirm.
    measured_mass_g : float | None
        Actual measured mass in grams, if available.
    operator : str
        Who confirmed the action.

    Returns
    -------
    BottleEvent
        A new confirmed/measured event. The caller must explicitly add it
        to the batch via ``batch.add_event()``.

    Raises
    ------
    ValueError
        If no event with the given ``event_id`` exists in the batch.
    """
    proposed = _find_event(batch, event_id)
    if proposed.confirmation != PROPOSED:
        raise ValueError(
            f"Event {event_id} has confirmation {proposed.confirmation!r}, expected PROPOSED"
        )

    if measured_mass_g is not None:
        new_confirmation = MEASURED
    else:
        new_confirmation = CONFIRMED

    event = BottleEvent(
        event_id=str(uuid.uuid4()),
        batch_id=batch.batch_id,
        event_type=proposed.event_type,
        timestamp=datetime.now(timezone.utc).isoformat(),
        operator=operator or proposed.operator,
        stock_id=proposed.stock_id,
        stock_label=proposed.stock_label,
        measured_mass_g=measured_mass_g,
        intended_mass_g=proposed.intended_mass_g,
        concentration=proposed.concentration,
        volume_ul=proposed.volume_ul,
        notes=proposed.notes,
        confirmation=new_confirmation,
        confirmed_by=operator,
    )
    return event


def correct_entry(
    batch: BottleBatch,
    event_id: str,
    corrected_mass_g: float,
    reason: str,
    operator: str = "",
) -> BottleEvent:
    """Create a compensating CORRECT_ENTRY event.

    Never deletes the original event. The correction references the original
    event's ``event_id`` via ``correction_ref`` and records the corrected
    mass. During replay, the original event's mass contribution is replaced
    by the correction.

    Parameters
    ----------
    batch : BottleBatch
        The batch containing the event to correct.
    event_id : str
        The ``event_id`` of the event being corrected.
    corrected_mass_g : float
        The corrected mass in grams.
    reason : str
        Why the correction is being made.
    operator : str
        Who performed the correction.

    Returns
    -------
    BottleEvent
        A new CORRECT_ENTRY event. The caller must explicitly add it to
        the batch via ``batch.add_event()``.

    Raises
    ------
    ValueError
        If no event with the given ``event_id`` exists in the batch.
    """
    _find_event(batch, event_id)  # validate existence

    event = BottleEvent(
        event_id=str(uuid.uuid4()),
        batch_id=batch.batch_id,
        event_type=CORRECT_ENTRY,
        timestamp=datetime.now(timezone.utc).isoformat(),
        operator=operator,
        stock_id=None,
        stock_label="",
        measured_mass_g=corrected_mass_g,
        intended_mass_g=None,
        notes=reason,
        confirmation=COMMITTED,
        confirmed_by=operator,
        correction_ref=event_id,
    )
    return event


# ── Pure replay function ────────────────────────────────────────────────────


def _validated_event_stream(events: list[BottleEvent]) -> list[BottleEvent]:
    if not events:
        raise ReconstructionInputError("ordered bottle event list cannot be empty")

    unique: list[BottleEvent] = []
    by_id: dict[str, BottleEvent] = {}
    for event in events:
        existing = by_id.get(event.event_id)
        if existing is not None:
            if existing == event:
                continue
            raise EventStreamError(
                f"conflicting duplicate event_id {event.event_id!r}"
            )
        by_id[event.event_id] = event
        unique.append(event)

    batch_ids = {event.batch_id for event in unique}
    if len(batch_ids) != 1:
        raise EventStreamError(
            "cross-stream event or correction reference is not supported"
        )

    has_sequences = [event.sequence is not None for event in unique]
    if any(has_sequences) and not all(has_sequences):
        raise EventStreamError(
            "event stream cannot mix sequenced and unsequenced events"
        )
    if all(has_sequences):
        previous_sequence = 0
        for event in unique:
            assert event.sequence is not None
            if event.sequence <= previous_sequence:
                raise EventStreamError(
                    f"stale sequence {event.sequence!r}; "
                    f"latest sequence is {previous_sequence!r}"
                )
            previous_sequence = event.sequence

    correction_refs: dict[str, str] = {}
    for event in unique:
        if event.event_type != CORRECT_ENTRY:
            continue
        if not event.correction_ref:
            raise EventStreamError(
                f"correction {event.event_id!r} has missing correction_ref"
            )
        if event.correction_ref not in by_id:
            raise EventStreamError(
                f"correction {event.event_id!r} references missing event "
                f"{event.correction_ref!r}"
            )
        correction_refs[event.event_id] = event.correction_ref

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(event_id: str) -> None:
        if event_id in visiting:
            raise EventStreamError(
                f"cycle detected in correction chain at {event_id!r}"
            )
        if event_id in visited:
            return
        visiting.add(event_id)
        target = correction_refs.get(event_id)
        if target in correction_refs:
            visit(target)
        visiting.remove(event_id)
        visited.add(event_id)

    for correction_id in correction_refs:
        visit(correction_id)

    positions = {event.event_id: index for index, event in enumerate(unique)}
    for correction_id, target_id in correction_refs.items():
        if positions[target_id] >= positions[correction_id]:
            raise EventStreamError(
                f"stale sequence/reference: correction {correction_id!r} "
                f"must follow target {target_id!r}"
            )

    return unique


def compute_replay_state(
    events: list[BottleEvent],
    container_tare_g: float = 0.0,
) -> dict[str, Any]:
    """Replay a sequence of events to compute current bottle state.

    This is a pure function — it does not modify any batch state.

    Replay rules
    ------------
    - ``DOSE_STOCK``: adds ``measured_mass_g`` (or ``intended_mass_g``) to
      the material identified by ``stock_label``.
    - ``REMOVE_SAMPLE``: subtracts ``measured_mass_g`` (or
      ``intended_mass_g``) from the material identified by ``stock_label``.
    - ``CORRECT_ENTRY``: finds the original event referenced by
      ``correction_ref`` and replaces its mass contribution with the
      correction's ``measured_mass_g``.
    - ``ADD_SOLVENT``: accumulates solvent mass into ``_solvent_mass_g``
      (tracked separately from odorant materials).
    - ``DILUTE``: appends ``(solvent_added_g, concentration_before,
      concentration_after)`` to ``_dilution_history``.
    - ``TARE_CONTAINER``: records the tare mass from the batch parameter
      as ``_tare_g``.
    - ``CLOSE_BATCH``: sets ``_batch_closed`` to ``True``.
    - ``TRANSFER``: no-op in single-batch scope (see TODO).
    - All other event types are structural (MIX, REST_START, etc.) and do
      not affect material masses.

    Parameters
    ----------
    events : list[BottleEvent]
        Ordered list of events to replay.
    container_tare_g : float
        Tare mass of the empty container in grams.

    Returns
    -------
    dict[str, Any]
        Mapping of material label -> current mass in grams, plus metadata
        keys prefixed with underscore:
        - ``_solvent_mass_g`` : float
        - ``_dilution_history`` : list[tuple[float, float, float]]
        - ``_tare_g`` : float
        - ``_batch_closed`` : bool
    """
    validated_events = _validated_event_stream(events)

    materials: dict[str, float] = {}
    corrections: dict[str, float] = {}
    solvent_mass_g: float = 0.0
    dilution_history: list[tuple[float, float, float]] = []
    batch_closed: bool = False

    # Build a map from CORRECT_ENTRY event_id -> resolved original event_id.
    # Follow chains of CORRECT_ENTRY -> CORRECT_ENTRY to find the ultimate
    # original event (e.g. DOSE_STOCK).  Detect cycles via visited set.
    correction_target_map: dict[str, str] = {}
    event_map: dict[str, BottleEvent] = {
        event.event_id: event for event in validated_events
    }

    for event in validated_events:
        if event.event_type == CORRECT_ENTRY and event.correction_ref:
            visited: set[str] = set()
            current_ref = event.correction_ref
            while current_ref in event_map and event_map[current_ref].event_type == CORRECT_ENTRY:
                if current_ref in visited:
                    raise EventStreamError(
                        f"Cycle detected in correction chain: event_id={event.event_id!r}, "
                        f"correction_ref={event.correction_ref!r}"
                    )
                visited.add(current_ref)
                next_ref = event_map[current_ref].correction_ref
                if next_ref is None:
                    break
                current_ref = next_ref
            correction_target_map[event.event_id] = current_ref

    # First pass: collect all corrections, keyed by the resolved original.
    correction_trace: dict[str, list[str]] = {}
    for event in validated_events:
        if event.event_type == CORRECT_ENTRY and event.correction_ref:
            mass = _resolve_mass(event)
            if mass is not None:
                target = correction_target_map.get(event.event_id, event.correction_ref)
                corrections[target] = mass
                correction_trace.setdefault(target, []).append(event.event_id)

    # Second pass: apply events, respecting corrections.
    # Only CONFIRMED, MEASURED, and COMMITTED events affect state.
    # PROPOSED events are suggestions that have not been executed.
    for event in validated_events:
        if event.confirmation == PROPOSED:
            continue

        if event.event_type == DOSE_STOCK:
            mass = corrections.get(event.event_id, _resolve_mass(event))
            if mass is not None:
                label = event.stock_label or "unknown"
                materials[label] = materials.get(label, 0.0) + mass

        elif event.event_type == REMOVE_SAMPLE:
            mass = corrections.get(event.event_id, _resolve_mass(event))
            if mass is not None:
                label = event.stock_label or "unknown"
                materials[label] = materials.get(label, 0.0) - mass

        elif event.event_type == CORRECT_ENTRY:
            # The correction itself is already consumed in the first pass;
            # do not double-count it as a material addition.
            pass

        elif event.event_type == ADD_SOLVENT:
            mass = corrections.get(event.event_id, _resolve_mass(event))
            if mass is not None:
                solvent_mass_g += mass

        elif event.event_type == DILUTE:
            mass = corrections.get(event.event_id, _resolve_mass(event))
            if mass is not None:
                total_odorant = sum(v for v in materials.values() if v > 0)
                conc_before = (
                    total_odorant / (total_odorant + solvent_mass_g)
                    if (total_odorant + solvent_mass_g) > 0
                    else 1.0
                )
                solvent_mass_g += mass
                conc_after = (
                    total_odorant / (total_odorant + solvent_mass_g)
                    if (total_odorant + solvent_mass_g) > 0
                    else 1.0
                )
                dilution_history.append((mass, conc_before, conc_after))

        elif event.event_type == CLOSE_BATCH:
            batch_closed = True

        # TRANSFER: TODO — multi-batch transfer requires atomic source +
        # destination batch access. In single-batch scope this is a no-op.
        # TARE_CONTAINER, MIX, REST_START, REST_END, SAMPLE, EVALUATE,
        # CREATE_BATCH: structural events, no mass effect.

    # Build result dict with material masses and metadata.
    result: dict[str, Any] = {k: v for k, v in materials.items() if v > 0}
    result["_solvent_mass_g"] = solvent_mass_g
    result["_dilution_history"] = dilution_history
    result["_tare_g"] = container_tare_g
    result["_batch_closed"] = batch_closed
    result["_correction_trace"] = {
        event_id: tuple(correction_ids)
        for event_id, correction_ids in correction_trace.items()
    }
    result["_applied_event_count"] = len(validated_events)
    return result


# ── Internal helpers ────────────────────────────────────────────────────────


def _resolve_mass(event: BottleEvent) -> float | None:
    """Return the effective mass for an event.

    Prefers ``measured_mass_g`` over ``intended_mass_g``. Returns None if
    neither is set.
    """
    if event.measured_mass_g is not None:
        return event.measured_mass_g
    return event.intended_mass_g


def _find_event(batch: BottleBatch, event_id: str) -> BottleEvent:
    """Find an event by ID in the batch's event log.

    Raises ValueError if not found.
    """
    for event in batch._events:
        if event.event_id == event_id:
            return event
    raise ValueError(f"Event {event_id!r} not found in batch {batch.batch_id!r}")


__all__ = [
    "ADD_SOLVENT",
    "BottleBatch",
    "BottleEvent",
    "CLOSE_BATCH",
    "COMMITTED",
    "CONFIRMED",
    "CORRECT_ENTRY",
    "CREATE_BATCH",
    "DILUTE",
    "DOSE_STOCK",
    "EVALUATE",
    "MEASURED",
    "MIX",
    "PROPOSED",
    "REMOVE_SAMPLE",
    "REST_END",
    "REST_START",
    "SAMPLE",
    "TARE_CONTAINER",
    "TRANSFER",
    "compute_replay_state",
    "confirm_action",
    "correct_entry",
    "propose_action",
]
