"""Matrix vapour pressure follows the simulator temperature (audit PHYS-03).

Materials are corrected to the state's temperature (305 K on skin); the declared
ethanol/water matrix used to stay at its 25 C vapour pressure. These tests pin
the temperature correction, not any absolute evaporation claim.
"""

from __future__ import annotations

import math

import pytest

from engine.pipeline import simulator
from engine.pipeline.formula_state import FormulaState, build_formula_state

SKIN_K = 305.0
MIXED = {
    "Limonene": 200.0,
    "Linalool": 200.0,
    "Hedione": 400.0,
    "Iso E Super": 400.0,
    "Galaxolide": 200.0,
}
MATRIX = {"Ethanol": 0.4, "Water": 0.05}
# NIST Chemistry WebBook Antoine parameters, log10(P / bar) = A - B / (T / K + C).
NIST_ANTOINE = {
    "ETHANOL": (5.24677, 1598.673, -46.424),  # Ambrose and Sprake 1970
    "WATER": (4.6543, 1435.264, -64.848),  # Stull 1947
}


def _antoine_pa(key: str, temperature_k: float) -> float:
    a, b, c = NIST_ANTOINE[key]
    return 1.0e5 * 10.0 ** (a - b / (temperature_k + c))


def _neat(ingredients: dict[str, float]) -> dict[str, float]:
    return {name: 1.0 for name in ingredients}


def _state(*, matrix: bool) -> FormulaState:
    if not matrix:
        return build_formula_state(MIXED, _neat(MIXED), temperature_K=SKIN_K)
    return build_formula_state(
        MIXED,
        _neat(MIXED),
        temperature_K=SKIN_K,
        matrix_moles=MATRIX,
        matrix_mass_g=19.3,
        matrix_source="explicit",
    )


def _use_25c_matrix_vp(monkeypatch) -> None:
    """Restore the pre-PHYS-03 behaviour: matrix vapour pressure fixed at 25 C."""
    monkeypatch.setattr(
        simulator,
        "_matrix_component_vp_pa",
        lambda key, temperature_K: simulator.MATRIX_COMPONENT_VP_MW[key][0],  # noqa: N803
        raising=False,
    )


@pytest.mark.parametrize(("key", "vp_25c"), [("ETHANOL", 7870.0), ("WATER", 3170.0)])
def test_matrix_vapour_pressure_follows_the_cited_antoine_relation(key, vp_25c):
    assert simulator._matrix_component_vp_pa(key, 298.15) == pytest.approx(vp_25c, rel=1e-12)
    at_skin = simulator._matrix_component_vp_pa(key, SKIN_K)
    assert at_skin == pytest.approx(_antoine_pa(key, SKIN_K), rel=0.01)
    # The 25 C anchor carries the cited temperature ratio, not a generic one.
    assert at_skin / vp_25c == pytest.approx(
        _antoine_pa(key, SKIN_K) / _antoine_pa(key, 298.15), rel=1e-9
    )


def test_declared_matrix_empties_faster_at_skin_temperature(monkeypatch):
    state = _state(matrix=True)
    assert state.temperature_K == SKIN_K
    # Loss scale on the concentrate moles (as in audit PHYS-01) keeps both
    # components below the rate cap, so the temperature correction shows.
    n0 = sum(m.moles for m in state.materials)
    dt = 300.0

    corrected = simulator._advance_state(state, dt, initial_pool_moles=n0)
    _use_25c_matrix_vp(monkeypatch)
    at_25c = simulator._advance_state(state, dt, initial_pool_moles=n0)

    assert corrected.matrix_moles < at_25c.matrix_moles * (1.0 - 1e-3)
    start = dict(state.matrix_components_moles)
    new_left = dict(corrected.matrix_components_moles)
    old_left = dict(at_25c.matrix_components_moles)
    for name, key in (("Ethanol", "ETHANOL"), ("Water", "WATER")):
        k_new = -math.log(new_left[name] / start[name]) / dt
        k_old = -math.log(old_left[name] / start[name]) / dt
        assert k_old < k_new < simulator.MAX_LOSS_RATE_PER_S
        assert k_new / k_old == pytest.approx(
            _antoine_pa(key, SKIN_K) / _antoine_pa(key, 298.15), rel=1e-9
        )


def test_materials_without_a_declared_matrix_are_unchanged(monkeypatch):
    state = _state(matrix=False)
    assert state.matrix_components_moles == ()

    corrected = simulator._advance_state(state, 14400.0)
    _use_25c_matrix_vp(monkeypatch)
    at_25c = simulator._advance_state(state, 14400.0)

    for new_row, old_row in zip(corrected.materials, at_25c.materials, strict=True):
        assert new_row.moles == pytest.approx(old_row.moles, rel=1e-12)
        assert new_row.screening_oav == pytest.approx(old_row.screening_oav, rel=1e-12)
