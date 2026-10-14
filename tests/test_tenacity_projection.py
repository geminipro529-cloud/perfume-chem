"""The tenacity screen counts measured musks as long-lasting and lets oil strength show.

Until Oct 2026 the screen compared the run-temperature VP (305 K) with 0.01 Pa,
so Galaxolide (0.0727 Pa at 25 C) and Habanolide did not count and a musk-led
formula read "weak longevity". The cutoffs now use VP at 25 C: long-lasting
below 0.1 Pa (the base tier in docs/agents/science-reference.md), deep below
0.01 Pa.
"""

from __future__ import annotations

import dataclasses

import pytest

from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.gates import ReleaseGateConfig, _gate_tenacity_projection


def _neat(ingredients: dict[str, float]) -> dict[str, float]:
    return {name: 1.0 for name in ingredients}


def _screen(ingredients: dict[str, float], batch_volume_ml: float = 30.0):
    state = build_formula_state(
        ingredients, _neat(ingredients), batch_volume_ml=batch_volume_ml, temperature_K=305.0
    )
    return _gate_tenacity_projection(state, ReleaseGateConfig())


MUSK_LED = {
    "Galaxolide": 300.0,
    "Habanolide": 300.0,
    "Ambrettolide": 60.0,
    "Hedione": 200.0,
    "Linalool": 140.0,
}

COLOGNE = {
    "Limonene": 500.0,
    "Linalool": 300.0,
    "Linalyl Acetate": 150.0,
    "Hedione": 50.0,
}


def test_measured_musks_count_as_long_lasting():
    result = _screen(MUSK_LED)

    assert result.status == "PASS", result.detail
    assert "weak longevity" not in result.detail
    # Galaxolide + Habanolide + Ambrettolide = 660 of 1000 uL, plus Hedione
    # when its 25 C VP sits under 0.1 Pa.
    assert result.data["long_lasting_pct"] >= 66.0
    assert result.data["deep_pct"] == pytest.approx(6.0, abs=0.01)
    assert result.data["vp_basis"] == "pure_component_vp_at_25C"


def test_a_cologne_still_reads_weak_longevity():
    result = _screen(COLOGNE)

    assert result.status == "WARN"
    assert "weak longevity" in result.detail
    assert result.data["long_lasting_pct"] < 10.0


def test_a_stronger_oil_carries_more_long_lasting_material_per_ml():
    at_15 = _screen({name: ul * 4.5 for name, ul in MUSK_LED.items()})  # 4500 uL in 30 mL
    at_18 = _screen({name: ul * 5.4 for name, ul in MUSK_LED.items()})  # 5400 uL in 30 mL

    assert at_15.data["concentrate_pct"] == pytest.approx(15.0, abs=0.01)
    assert at_18.data["concentrate_pct"] == pytest.approx(18.0, abs=0.01)
    assert at_15.data["long_lasting_pct"] == pytest.approx(at_18.data["long_lasting_pct"], abs=0.01)
    assert at_18.data["long_lasting_ul_per_ml"] > at_15.data["long_lasting_ul_per_ml"]
    assert at_18.data["long_lasting_ul_per_ml"] / at_15.data[
        "long_lasting_ul_per_ml"
    ] == pytest.approx(1.2, rel=1e-6)
    assert "per mL of perfume at 18.0% oil" in at_18.detail


def test_a_row_without_vapour_pressure_is_reported_not_counted():
    state = build_formula_state(
        MUSK_LED, _neat(MUSK_LED), batch_volume_ml=30.0, temperature_K=305.0
    )
    unknown = dataclasses.replace(state.materials[0], vp_pure_pa=None)
    stripped = dataclasses.replace(state, materials=[unknown, *state.materials[1:]])

    result = _gate_tenacity_projection(stripped, ReleaseGateConfig())

    assert result.data["unknown_vp_pct"] == pytest.approx(
        unknown.active_ul / state.total_active_ul * 100.0, abs=0.01
    )
    assert "not counted" in result.detail
