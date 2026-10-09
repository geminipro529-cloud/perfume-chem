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


# --- Declared matrix evaporates by the same law (diagnosis M1a) ---

MATRIX = {"Ethanol": 0.4, "Water": 0.05}


def _matrix_state(ingredients: dict[str, float]) -> FormulaState:
    return build_formula_state(
        ingredients,
        _neat(ingredients),
        matrix_moles=MATRIX,
        matrix_mass_g=19.3,
        matrix_source="explicit",
    )


def _per_step_frames(state: FormulaState, ingredients: dict[str, float], steps: int):
    dt = simulator.MAX_INTEGRATION_STEP_SECONDS
    windows = tuple((f"step_{i}", i * dt) for i in range(steps + 1))
    return simulator.simulate_formula(
        ingredients, _neat(ingredients), initial_state=state, windows=windows
    )


def _frozen_matrix_frames(state: FormulaState, windows):
    """The b92e000 integration: materials deplete, the matrix is copied unchanged."""
    n0 = simulator._pool_total_moles(state)
    frames = []
    current, now = state, 0.0
    for label, seconds in windows:
        remaining_seconds = float(seconds) - now
        while remaining_seconds > 0.0:
            step = min(simulator.MAX_INTEGRATION_STEP_SECONDS, remaining_seconds)
            raw = simulator._remaining_raw_ul(current, step, initial_pool_moles=n0)
            current = FormulaState.from_base(current, new_raw_ul=raw)
            remaining_seconds -= step
        now = float(seconds)
        frames.append((label, current))
    return frames


def test_declared_matrix_moles_strictly_decrease_and_mostly_leave_by_7200_s():
    state = _matrix_state(MIXED)
    frames = simulator.simulate_formula(MIXED, _neat(MIXED), initial_state=state)
    matrix = [frame.state.matrix_moles for frame in frames]
    assert matrix[0] == pytest.approx(sum(MATRIX.values()), rel=1e-12)
    assert all(later < earlier for earlier, later in zip(matrix, matrix[1:]))
    late_heart = next(frame for frame in frames if frame.t_seconds == 7200.0)
    assert late_heart.state.matrix_moles < 0.1 * matrix[0]
    # Component identities are kept; only their amounts fall.
    for frame in frames:
        assert [name for name, _ in frame.state.matrix_components_moles] == list(MATRIX)


def test_formula_without_matrix_matches_the_frozen_matrix_integration_exactly():
    state = _state(MIXED)
    assert state.matrix_components_moles == ()
    frames = simulator.simulate_formula(MIXED, _neat(MIXED), initial_state=state)
    expected = _frozen_matrix_frames(state, simulator.DEFAULT_WINDOWS)
    for frame, (label, old_state) in zip(frames, expected, strict=True):
        assert frame.label == label
        assert frame.state.matrix_components_moles == ()
        for new_row, old_row in zip(frame.state.materials, old_state.materials, strict=True):
            assert new_row.raw_ul == old_row.raw_ul
            assert new_row.moles == old_row.moles
            assert new_row.screening_oav == old_row.screening_oav


def test_declared_matrix_differs_from_the_frozen_matrix_integration():
    state = _matrix_state(MIXED)
    frames = simulator.simulate_formula(MIXED, _neat(MIXED), initial_state=state)
    expected = _frozen_matrix_frames(state, simulator.DEFAULT_WINDOWS)
    drydown, (_, frozen) = frames[-1], expected[-1]
    assert frozen.matrix_moles == pytest.approx(sum(MATRIX.values()), rel=1e-12)
    assert drydown.state.matrix_moles < 1e-3 * frozen.matrix_moles
    new_total = sum(m.raw_ul for m in drydown.state.materials)
    assert new_total < sum(m.raw_ul for m in frozen.materials)


def test_heavy_material_rate_rises_as_the_matrix_leaves():
    state = _matrix_state(MIXED)
    n0 = simulator._pool_total_moles(state)
    dt = simulator.MAX_INTEGRATION_STEP_SECONDS
    frames = _per_step_frames(state, MIXED, 12)

    rates, ratios = [], []
    for before, after in zip(frames, frames[1:]):
        row_before = next(m for m in before.state.materials if m.name == "Galaxolide")
        row_after = next(m for m in after.state.materials if m.name == "Galaxolide")
        k = -math.log(row_after.moles / row_before.moles) / dt
        ratio = n0 / simulator._pool_total_moles(before.state)
        # Per unit escaping tendency the rate is scale * N0/N(t) / sqrt(MW);
        # gamma itself also falls as ethanol leaves, so k is compared per unit.
        escaping = row_before.partial_pressure_pa / row_before.mole_fraction
        assert k / escaping == pytest.approx(
            simulator.LOSS_RATE_SCALE * ratio / math.sqrt(row_before.mw_g_mol), rel=1e-9
        )
        rates.append(k)
        ratios.append(ratio)
    assert all(later > earlier for earlier, later in zip(ratios, ratios[1:]))
    assert ratios[-1] > 16.0
    assert all(later > earlier for earlier, later in zip(rates[:6], rates[1:6]))
    assert rates[-1] < simulator.MAX_LOSS_RATE_PER_S
    assert rates[-1] > 3.0 * rates[0]


def test_removed_moles_track_headspace_with_the_matrix_in_the_pool():
    state = _matrix_state(MIXED)
    n0 = simulator._pool_total_moles(state)
    assert n0 == pytest.approx(
        sum(m.moles for m in state.materials) + sum(MATRIX.values()), rel=1e-12
    )
    expected_a = 2.0e-5 * n0
    dt = simulator.MAX_INTEGRATION_STEP_SECONDS
    frames = _per_step_frames(state, MIXED, 36)

    for before, after in zip(frames, frames[1:]):
        n_now = simulator._pool_total_moles(before.state)
        for before_row, after_row in zip(
            before.state.materials, after.state.materials, strict=True
        ):
            # x_i is n_i over materials plus matrix, the pool the law uses.
            assert before_row.mole_fraction == pytest.approx(before_row.moles / n_now, rel=1e-12)
            k_applied = -math.log(after_row.moles / before_row.moles) / dt
            if k_applied < simulator.MAX_LOSS_RATE_PER_S * (1.0 - 1e-9):
                removal_rate = k_applied * before_row.moles
                assert removal_rate / _gas_side_term(before_row) == pytest.approx(
                    expected_a, rel=1e-9
                )
        matrix_after = dict(after.state.matrix_components_moles)
        for name, moles in before.state.matrix_components_moles:
            _vp_25c, mw = simulator.MATRIX_COMPONENT_VP_MW[name.upper()]
            vp = simulator._matrix_component_vp_pa(name.upper(), before.state.temperature_K)
            x_j = moles / n_now
            gas_term = simulator.MATRIX_COMPONENT_GAMMA * x_j * vp / math.sqrt(mw)
            k_applied = -math.log(matrix_after[name] / moles) / dt
            assert k_applied == pytest.approx(
                min(simulator.MAX_LOSS_RATE_PER_S, expected_a * gas_term / moles), rel=1e-9
            )
