"""Mass-balanced loss law of the temporal screening simulator (diagnosis M3).

The loss law is ``dn_i/dt = -A * gamma_i * x_i * P_i* / sqrt(MW_i)`` with
``x_i`` taken from the current pool and ``A = 2e-5 * N_0`` an unfitted
relative scale, where ``N_0`` is the t=0 concentrate moles without any declared
matrix (audit PHYS-01). These tests pin the law, not any absolute evaporation
claim.
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
    frames = simulator.simulate_formula(
        MIXED, _neat(MIXED), initial_state=state, windows=windows, default_ethanol_fill=False
    )

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
        MIXED,
        _neat(MIXED),
        initial_state=state,
        windows=(("opening", 0.0), ("top", dt)),
        default_ethanol_fill=False,
    )

    expected = _old_law_step(state, dt)
    for new_row, old_row in zip(frames[1].state.materials, expected.materials, strict=True):
        assert new_row.raw_ul == pytest.approx(old_row.raw_ul, rel=1e-12)


def test_mixed_formula_loses_more_by_drydown_and_total_strictly_decreases():
    state = _state(MIXED)
    # The concentrate-only pool, with the v5 default ethanol fill switched off.
    frames = simulator.simulate_formula(
        MIXED, _neat(MIXED), initial_state=state, default_ethanol_fill=False
    )
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
    # The concentrate-only pool, with the v5 default ethanol fill switched off.
    frames = simulator.simulate_formula(
        MIXED, _neat(MIXED), initial_state=state, default_ethanol_fill=False
    )
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
    # The matrix dilutes every material until it leaves, and the loss scale no
    # longer grows with it (PHYS-01), so the drydown keeps more than the frozen
    # integration, whose N_0 included the matrix.
    new_total = sum(m.raw_ul for m in drydown.state.materials)
    assert new_total > sum(m.raw_ul for m in frozen.materials)


def test_heavy_material_rate_rises_as_the_matrix_leaves():
    state = _matrix_state(MIXED)
    n0 = simulator._loss_scale_moles(state)
    concentrate = sum(m.moles for m in state.materials)
    assert n0 == pytest.approx(concentrate, rel=1e-12)
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
    # The matrix dilutes the pool at first; while any of it is left, no
    # material loses faster than it would without a matrix (PHYS-01).
    assert ratios[0] == pytest.approx(concentrate / (concentrate + sum(MATRIX.values())))
    assert ratios[-1] > 10.0 * ratios[0]
    assert ratios[-1] < 1.0
    assert all(later > earlier for earlier, later in zip(rates[:6], rates[1:6]))
    assert rates[-1] < simulator.MAX_LOSS_RATE_PER_S
    assert rates[-1] > 3.0 * rates[0]


def test_removed_moles_track_headspace_with_the_matrix_in_the_pool():
    state = _matrix_state(MIXED)
    # A is scaled by the concentrate moles alone; the matrix is in the pool
    # that x_i uses, not in the scale (PHYS-01).
    n0 = simulator._loss_scale_moles(state)
    assert n0 == pytest.approx(sum(m.moles for m in state.materials), rel=1e-12)
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
            vp, mw = simulator.MATRIX_COMPONENT_VP_MW[name.upper()]
            x_j = moles / n_now
            gas_term = simulator.MATRIX_COMPONENT_GAMMA * x_j * vp / math.sqrt(mw)
            k_applied = -math.log(matrix_after[name] / moles) / dt
            assert k_applied == pytest.approx(
                min(simulator.MAX_LOSS_RATE_PER_S, expected_a * gas_term / moles), rel=1e-9
            )


# --- Undeclared matrix: default ethanol fill (temporal model v5) ---

MIXED_TOTAL_UL = 1400.0
# 30 mL bottle - 1400 uL concentrate = 28600 uL ethanol at 0.789 g/mL (20 C, CRC).
EXPECTED_FILL_MASS_G = 28.6 * 0.789
EXPECTED_FILL_MOLES = EXPECTED_FILL_MASS_G / 46.07


def test_undeclared_formula_gets_the_default_ethanol_fill_with_its_mass():
    state = _state(MIXED)
    assert sum(m.raw_ul for m in state.materials) == pytest.approx(MIXED_TOTAL_UL)
    frames = simulator.simulate_formula(MIXED, _neat(MIXED), initial_state=state)

    assert simulator.TEMPORAL_MODEL == "dynamic_headspace_mass_balanced_loss_v5"
    opening = frames[0]
    assert opening.state.matrix_components_moles == (
        ("Ethanol", pytest.approx(EXPECTED_FILL_MOLES, rel=1e-12)),
    )
    assert opening.state.matrix_source == "default_ethanol_fill"
    # The fill gives no finished-product mass or ppm; only the frames carry it.
    assert opening.state.matrix_mass_g == 0.0
    assert all(m.active_finished_product_ppm_w_w is None for m in opening.state.materials)
    assert state.matrix_components_moles == ()
    for frame in frames:
        payload = frame.as_dict()
        assert payload["temporal_model"] == "dynamic_headspace_mass_balanced_loss_v5"
        assumption = payload["matrix_assumption"]
        assert assumption["basis"] == "DEFAULT_ETHANOL_FILL"
        assert assumption["bottle_volume_ml"] == 30.0
        assert assumption["concentrate_ul"] == pytest.approx(MIXED_TOTAL_UL)
        assert assumption["ethanol_volume_ul"] == pytest.approx(28600.0)
        assert assumption["ethanol_mass_g"] == pytest.approx(EXPECTED_FILL_MASS_G, rel=1e-12)
        assert assumption["ethanol_density_g_ml"] == 0.789


def test_default_fill_uses_the_bottle_volume_of_the_state():
    state = build_formula_state(MIXED, _neat(MIXED), batch_volume_ml=10.0)
    frame = simulator.simulate_formula(
        MIXED, _neat(MIXED), initial_state=state, windows=(("opening", 0.0),)
    )[0]
    assert frame.matrix_assumption["bottle_volume_ml"] == 10.0
    assert frame.matrix_assumption["ethanol_mass_g"] == pytest.approx(8.6 * 0.789, rel=1e-12)


def test_concentrate_at_or_above_the_bottle_volume_gets_no_fill():
    big = {name: amount * 25.0 for name, amount in MIXED.items()}  # 35 mL in 30 mL
    state = _state(big)
    frame = simulator.simulate_formula(
        big, _neat(big), initial_state=state, windows=(("opening", 0.0),)
    )[0]
    assert frame.matrix_assumption["basis"] == "NONE:CONCENTRATE_FILLS_BOTTLE"
    assert frame.state is state


def test_default_fill_lowers_opening_screening_oavs():
    state = _state(MIXED)
    filled = simulator.simulate_formula(MIXED, _neat(MIXED), initial_state=state)[0]
    bare = simulator.simulate_formula(
        MIXED, _neat(MIXED), initial_state=state, default_ethanol_fill=False
    )[0]
    assert bare.state is state
    assert bare.matrix_assumption["basis"] == "OMITTED:DEFAULT_FILL_DISABLED"
    for with_fill, without in zip(filled.state.materials, bare.state.materials, strict=True):
        assert without.screening_oav and without.screening_oav > 0
        assert with_fill.screening_oav < without.screening_oav


def test_default_fill_is_below_ten_percent_of_its_moles_by_7200_s():
    frames = simulator.simulate_formula(MIXED, _neat(MIXED), initial_state=_state(MIXED))
    fill = [frame.state.matrix_moles for frame in frames]
    assert fill[0] == pytest.approx(EXPECTED_FILL_MOLES, rel=1e-12)
    assert all(later < earlier for earlier, later in zip(fill, fill[1:]))
    late_heart = next(frame for frame in frames if frame.t_seconds == 7200.0)
    assert late_heart.state.matrix_moles < 0.1 * fill[0]


def test_declared_matrix_frames_are_unchanged_by_the_default_fill():
    state = _matrix_state(MIXED)
    frames = simulator.simulate_formula(MIXED, _neat(MIXED), initial_state=state)
    n0 = simulator._loss_scale_moles(state)
    current, now = state, 0.0
    assert frames[0].state is state
    for frame, (label, seconds) in zip(frames, simulator.DEFAULT_WINDOWS, strict=True):
        # The declared state advanced by the same law, with no fill added.
        current = simulator._advance_state(current, seconds - now, initial_pool_moles=n0)
        now = seconds
        assert frame.label == label
        assert frame.state == current
        assert frame.state.matrix_source == "explicit"
        assert frame.matrix_assumption == {"basis": "DECLARED", "matrix_source": "explicit"}


def test_heavy_materials_keep_the_same_drydown_with_or_without_a_declared_matrix():
    """Audit PHYS-01: declaring the solvent must not empty the base.

    With the matrix inside ``N_0`` the loss scale grew with the matrix, so once
    it had evaporated every material lost at a rate inflated by about the
    matrix-to-concentrate mole ratio. Heavy materials barely move in 4 h either
    way; the declared matrix may only slow them while it is present.
    """
    plain = simulator.simulate_formula(
        MIXED, _neat(MIXED), initial_state=_state(MIXED), default_ethanol_fill=False
    )
    with_matrix = simulator.simulate_formula(
        MIXED, _neat(MIXED), initial_state=_matrix_state(MIXED)
    )
    assert plain[-1].t_seconds == with_matrix[-1].t_seconds == 14400.0
    start = {m.name: m.moles for m in plain[0].state.materials}
    for name in ("Hedione", "Iso E Super", "Galaxolide"):
        left_plain = next(m.moles for m in plain[-1].state.materials if m.name == name)
        left_matrix = next(m.moles for m in with_matrix[-1].state.materials if m.name == name)
        assert left_plain / start[name] > 0.95
        assert left_matrix / start[name] == pytest.approx(left_plain / start[name], abs=0.02)
        assert left_matrix >= left_plain * (1.0 - 1e-9)
