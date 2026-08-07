"""Live batch console. Propose -> Confirm -> Measure -> Commit pipeline.

Pre-action gate checks safety before any irreversible action.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from engine.bottle.events import (
    BottleBatch,
    BottleEvent,
    DOSE_STOCK,
    confirm_action,
    propose_action,
)


# ── BatchAction dataclass ────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class BatchAction:
    """A proposed batch action with full risk disclosure.

    Parameters
    ----------
    action_type : str
        One of DOSE_STOCK, ADD_SOLVENT, REMOVE_SAMPLE, DILUTE, MIX, RESTART.
    material_label : str
        Human-readable label for the material being acted upon.
    stock_id : str | None
        Identity ID of the stock bottle, if applicable.
    amount_ul : float
        Proposed volume in microlitres.
    amount_g : float | None
        Proposed mass in grams, if known.
    reason : str
        Why this action is being taken (intended role / purpose).
    expected_effect : str
        What olfactive or structural change is expected.
    main_risk : str
        The single most important risk to watch for.
    evaluation_time_minutes : int
        How long to wait before evaluating the result.
    stop_condition : str
        Condition under which the action should be aborted or reversed.
    """

    action_type: str
    material_label: str
    stock_id: str | None = None
    amount_ul: float = 0.0
    amount_g: float | None = None
    reason: str = ""
    expected_effect: str = ""
    main_risk: str = ""
    evaluation_time_minutes: int = 30
    stop_condition: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Pre-action gate ──────────────────────────────────────────────────────────


def pre_action_gate(action: BatchAction, batch: BottleBatch) -> list[str]:
    """Verify safety before allowing any irreversible action.

    Parameters
    ----------
    action : BatchAction
        The proposed action to gate.
    batch : BottleBatch
        The batch the action would apply to.

    Returns
    -------
    list[str]
        List of violation strings. An empty list means the gate PASSES.
    """
    violations: list[str] = []

    if not batch.batch_id:
        violations.append("batch_id is not set")

    if batch.event_count() == 0:
        violations.append("bottle ledger is empty — no events recorded")

    if action.action_type in (DOSE_STOCK, "REMOVE_SAMPLE", "DILUTE"):
        if not action.stock_id:
            violations.append("stock identity is not known (stock_id is None or empty)")

    if action.action_type in (DOSE_STOCK, "ADD_SOLVENT", "DILUTE"):
        if action.amount_ul <= 0 and (action.amount_g is None or action.amount_g <= 0):
            violations.append("amount is not measurable (amount_ul <= 0 and amount_g is None/<=0)")

    if not action.reason:
        violations.append("intended role is not declared (reason is empty)")

    if not action.main_risk:
        violations.append("main_risk is not stated")

    if action.evaluation_time_minutes <= 0:
        violations.append("evaluation_time is not set (<= 0)")

    if not action.stop_condition:
        violations.append("stop_condition is not stated")

    return violations


# ── Propose addition ─────────────────────────────────────────────────────────


def propose_addition(
    batch: BottleBatch,
    material: str,
    amount_ul: float,
    reason: str,
    expected_effect: str = "",
    main_risk: str = "",
    evaluation_minutes: int = 30,
    stop_condition: str = "",
) -> BottleEvent:
    """Propose a DOSE_STOCK addition to the batch.

    Never commits — always returns a PROPOSED event. The caller must
    explicitly add the event to the batch via ``batch.add_event()``.

    Parameters
    ----------
    batch : BottleBatch
        The batch to propose the addition for.
    material : str
        Material label (used as stock_label).
    amount_ul : float
        Proposed volume in microlitres.
    reason : str
        Why this material is being added.
    expected_effect : str
        Expected olfactive or structural effect.
    main_risk : str
        Primary risk to monitor.
    evaluation_minutes : int
        Evaluation window in minutes (default 30).
    stop_condition : str
        Condition under which to abort.

    Returns
    -------
    BottleEvent
        A PROPOSED event. Not yet added to the batch.
    """
    notes_parts = []
    if expected_effect:
        notes_parts.append(f"Expected effect: {expected_effect}")
    if main_risk:
        notes_parts.append(f"Main risk: {main_risk}")
    if stop_condition:
        notes_parts.append(f"Stop condition: {stop_condition}")
    notes_parts.append(f"Evaluation time: {evaluation_minutes} min")
    notes = " | ".join(notes_parts)

    event = propose_action(
        batch=batch,
        action_type=DOSE_STOCK,
        stock_label=material,
        intended_mass_g=None,
        volume_ul=amount_ul,
        notes=notes,
        operator="",
    )
    return event


# ── Confirm addition ─────────────────────────────────────────────────────────


def confirm_addition(
    batch: BottleBatch,
    event_id: str,
    measured_mass_g: float | None = None,
    operator: str = "",
) -> BottleEvent:
    """Confirm a proposed addition, advancing it through the lifecycle.

    Delegates to ``engine.bottle.events.confirm_action`` which moves the
    event from PROPOSED -> CONFIRMED (or MEASURED if a mass is provided).

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
        A new CONFIRMED or MEASURED event. The caller must explicitly add
        it to the batch via ``batch.add_event()``.
    """
    return confirm_action(
        batch=batch,
        event_id=event_id,
        measured_mass_g=measured_mass_g,
        operator=operator,
    )


# ── Format action output ─────────────────────────────────────────────────────


def format_action_output(action: BatchAction, event: BottleEvent) -> str:
    """Return a human-readable summary of the action and its ledger state.

    Parameters
    ----------
    action : BatchAction
        The proposed batch action.
    event : BottleEvent
        The event created from the action.

    Returns
    -------
    str
        Formatted multi-line summary.
    """
    stock_info = action.stock_id or action.material_label
    amount = f"{action.amount_ul} uL"
    if action.amount_g is not None:
        amount += f" ({action.amount_g:.4f} g)"

    lines = [
        f"Action type: {action.action_type}",
        f"Material and stock: {stock_info}",
        f"Amount: {amount}",
        f"Reason: {action.reason}",
        f"Expected effect: {action.expected_effect}",
        f"Main risk: {action.main_risk}",
        f"Evaluation time: {action.evaluation_time_minutes} minutes",
        f"Stop condition: {action.stop_condition}",
        f"Ledger state after confirmation: {event.confirmation}",
    ]
    return "\n".join(lines)


# ── Rescue addition ──────────────────────────────────────────────────────────


def create_rescue_addition(
    batch: BottleBatch,
    material: str,
    amount_ul: float,
    reason: str,
) -> BottleEvent:
    """Create a BATCH_RESCUE addition event.

    Same as ``propose_addition`` but marks the action as a rescue
    operation in the notes. Rescue additions are corrective actions
    applied to an already-mixed batch.

    Parameters
    ----------
    batch : BottleBatch
        The batch to propose the rescue for.
    material : str
        Material label.
    amount_ul : float
        Proposed volume in microlitres.
    reason : str
        Why this rescue addition is needed.

    Returns
    -------
    BottleEvent
        A PROPOSED event with rescue context in the notes.
    """
    notes = f"RESCUE OPERATION: {reason}"
    event = propose_action(
        batch=batch,
        action_type=DOSE_STOCK,
        stock_label=material,
        intended_mass_g=None,
        volume_ul=amount_ul,
        notes=notes,
        operator="",
    )
    return event


__all__ = [
    "BatchAction",
    "confirm_addition",
    "create_rescue_addition",
    "format_action_output",
    "pre_action_gate",
    "propose_addition",
]
