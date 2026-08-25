"""Canonical temporal simulator with a fail-closed initial-state firewall.

The prior simulator is preserved unchanged in
``engine.pipeline.simulator_legacy``. Canonical simulation may evolve an
already-authorized FormulaState, but it may not silently construct one from raw
formula/dilution mappings. Explicit unbound exploration remains available only
through the opt-in flag and carries no additional authority.
"""

from __future__ import annotations

from engine.pipeline.simulator_legacy import *  # noqa: F401,F403
from engine.pipeline.simulator_legacy import simulate_formula as _legacy_simulate


class SimulationAuthorityError(ValueError):
    """Raised when canonical simulation lacks an authorized initial state."""


def simulate_formula(
    ingredients_ul,
    dilutions=None,
    *,
    batch_volume_ml=30.0,
    temperature_K=305.0,
    context="skin",
    windows=DEFAULT_WINDOWS,
    initial_state=None,
    allow_unbound_exploratory=False,
):
    """Simulate only from an authorized state unless explicitly exploratory."""

    if initial_state is None and not allow_unbound_exploratory:
        raise SimulationAuthorityError(
            "canonical simulation requires an authorized initial_state; "
            "set allow_unbound_exploratory=True only for explicitly "
            "non-authoritative exploratory reconstruction"
        )
    return _legacy_simulate(
        ingredients_ul,
        dilutions,
        batch_volume_ml=batch_volume_ml,
        temperature_K=temperature_K,
        context=context,
        windows=windows,
        initial_state=initial_state,
    )
