"""Mass-balanced loss law of the temporal screening simulator (diagnosis M3).

The loss law is ``dn_i/dt = -A * gamma_i * x_i * P_i* / sqrt(MW_i)`` with
``x_i`` taken from the current pool and ``A = 2e-5 * N_0`` an unfitted
relative scale. These tests pin the law, not any absolute evaporation claim.
"""

from __future__ import annotations

import math

import pytest

from engine.pipeline import simulator
from engine.pipeline.formula_state import FormulaState, build_formula_state

MIXED = {
    "Limonene": 200.0,
    "Linalool": 200.0,
    "Hedione": 400.0,
    "Iso E Super": 400.0,
    "Galaxolide": 200.0,
}


def _neat(ingredients: dict[str, float]) -> dict[str, float]:
    return {name: 1.0 for name in ingredients}


def _state(ingredients: dict[str, float]) -> FormulaState:
    return build_formula_state(ingredients, _neat(ingredients))


def _old_law_step(state: FormulaState, delta_seconds: float) -> FormulaState:
    """The pre-M3 per-material constant: k_i = min(2.5e-3, 2e-5 * gP/sqrt(MW))."""
    remaining = {}
    for m in state.materials:
        escaping = simulator._effective_escaping_tendency_pa(m)
        mw = max(m.mw_g_mol or 200.0, 1.0)
        k = min(2.5e-3, escaping / math.sqrt(mw) * 2.0e-5) if escaping > 0 else 0.0
        remaining[m.name] = m.active_ul * math.exp(-k * delta_seconds) / max(m.dilution, 1e-9)
    return FormulaState.from_base(state, new_raw_ul=remaining)


def _gas_side_term(m) -> float:
    """gamma_i * x_i * P_i* / sqrt(MW_i) as reported by the state row."""
    return m.partial_pressure_pa / math.sqrt(max(m.mw_g_mol or 200.0, 1.0))


def test_removed_moles_track_reported_headspace_with_one_fixed_constant():
    state = _state(MIXED)
    n0 = sum(m.moles for m in state.materials)
    expected_a = 2.0e-5 * n0
    dt = simulator.MAX_INTEGRATION_STEP_SECONDS
    # One frame per integration step over 3 h, through the public entry point.
    windows = tuple((f"step_{i}", i * dt) for i in range(37))
    frames = simulator.simulate_formula(MIXED, _neat(MIXED), initial_state=state, windows=windows)

    for before, after in zip(frames, frames[1:]):
        n_now = sum(m.moles for m in before.state.materials)
        for before_row, after_row in zip(
            before.state.materials, after.state.materials, strict=True
        ):
            # The row's mole fraction is n_i over the same pool the law uses.
            assert before_row.mole_fraction == pytest.approx(before_row.moles / n_now, rel=1e-12)
            k_applied = -math.log(after_row.moles / before_row.moles) / dt
            assert k_applied < 2.5e-3  # within the cap
            removal_rate = k_applied * before_row.moles
            assert removal_rate / _gas_side_term(before_row) == pytest.approx(expected_a, rel=1e-9)
    # The pool shrank enough that a per-step constant 2e-5 * N(t) would differ.
    assert sum(m.moles for m in frames[-1].state.materials) < 0.95 * n0


def test_first_step_rates_equal_the_previous_per_material_constant():
    state = _state(MIXED)
    dt = simulator.MAX_INTEGRATION_STEP_SECONDS

    frames = simulator.simulate_formula(
        MIXED, _neat(MIXED), initial_state=state, windows=(("opening", 0.0), ("top", dt))
    )

    expected = _old_law_step(state, dt)
    for new_row, old_row in zip(frames[1].state.materials, expected.materials, strict=True):
        assert new_row.raw_ul == pytest.approx(old_row.raw_ul, rel=1e-12)


def test_mixed_formula_loses_more_by_drydown_and_total_strictly_decreases():
    state = _state(MIXED)
    frames = simulator.simulate_formula(MIXED, _neat(MIXED), initial_state=state)
    totals = [sum(m.raw_ul for m in frame.state.materials) for frame in frames]
    assert all(later < earlier for earlier, later in zip(totals, totals[1:]))

    old = state
    steps = int(frames[-1].t_seconds / simulator.MAX_INTEGRATION_STEP_SECONDS)
    for _ in range(steps):
        old = _old_law_step(old, simulator.MAX_INTEGRATION_STEP_SECONDS)
    old_total = sum(m.raw_ul for m in old.materials)
    assert totals[-1] < old_total

    new_rows = {m.name: m.raw_ul for m in frames[-1].state.materials}
    for old_row in old.materials:
        if old_row.name in {"Hedione", "Iso E Super", "Galaxolide"}:
            assert new_rows[old_row.name] < old_row.raw_ul


def test_pure_material_loses_at_a_constant_rate():
    ingredients = {"Hedione": 400.0}
    state = _state(ingredients)
    n0 = simulator._pool_total_moles(state)
    dt = simulator.MAX_INTEGRATION_STEP_SECONDS

    losses = []
    for _ in range(48):
        after = simulator._advance_state(state, dt, initial_pool_moles=n0)
        losses.append(state.materials[0].moles - after.materials[0].moles)
        state = after
    assert max(losses) / min(losses) - 1.0 < 1e-6


def test_pure_volatile_is_zero_order_until_the_rate_cap_binds():
    ingredients = {"Limonene": 200.0}
    state = _state(ingredients)
    n0 = simulator._pool_total_moles(state)
    row = state.materials[0]
    k0 = simulator._loss_rate_per_s(
        simulator._effective_escaping_tendency_pa(row), row.mw_g_mol
    )
    cap_moles = n0 * k0 / simulator.MAX_LOSS_RATE_PER_S
    dt = 2.0

    t = 0.0
    while state.materials[0].moles > 1.05 * cap_moles:
        state = simulator._advance_state(
            state, dt, max_step_seconds=dt, initial_pool_moles=n0
        )
        t += dt
        # Zero order: n(t) = n0 - k0 * n0 * t while the cap does not bind.
        assert state.materials[0].moles == pytest.approx(n0 * (1.0 - k0 * t), rel=1e-2)
    assert t > 0.0
