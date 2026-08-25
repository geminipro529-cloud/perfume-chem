"""Fail-closed FormulaState construction boundary.

This helper exists so canonical consumers cannot accidentally construct a
FormulaState before the V5-bound FormulaDoseReceipt (and, for physical scope,
PreparedRun) has been authorized.

It deliberately contains no inventory parsing, chemistry inference, sensory
logic, or release logic. It is plumbing around the existing authoritative
objects and can therefore be reused by gates, OAV, simulator entry points, and
other downstream consumers without creating a second authority system.
"""

from __future__ import annotations

from typing import Callable, TypeVar

from engine.pipeline.preflight import FormulaDoseReceipt
from engine.pipeline.stock_authority_spine import (
    PreparedRun,
    require_formula_state_authority,
)


T = TypeVar("T")


def build_authorized_formula_state(
    receipt: FormulaDoseReceipt,
    builder: Callable[..., T],
    *args,
    scope: str,
    prepared_run: PreparedRun | None = None,
    **kwargs,
) -> T:
    """Authorize first, then invoke the supplied FormulaState builder exactly once.

    If authority is missing or abstained, ``builder`` is never called. This is
    the executable form of the P0 invariant that receipt failure must stop
    FormulaState, physics, OAV, safety, optimizer, and export consumers before
    they can recompute from legacy dilution assumptions.
    """

    require_formula_state_authority(
        receipt,
        scope=scope,
        prepared_run=prepared_run,
    )
    return builder(*args, **kwargs)
