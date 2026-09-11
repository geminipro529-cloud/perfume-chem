"""Formulator recommendation tests (#5): default behavior + determinism + cache."""
from __future__ import annotations

from engine.formula_recommendations import generate_recommendations
from engine.optimizer.models import FormulaVector
from engine.optimizer.scoring import FormulaScorer

DEEP_AXES = {
    "depth_stacking",
    "temporal_layering",
    "spatial_projection",
    "integration_capacity",
    "function_balance",
    "legibility_coherence",
}

INGREDIENTS = {
    "Iso E Super": 32.0,
    "Hedione": 22.0,
    "Galaxolide": 14.0,
    "Alpha Isomethyl Ionone": 8.0,
    "Ethylene Brassylate": 10.0,
    "Vanillin": 5.0,
    "Bergamot FCF": 5.0,
    "Birch Tar": 1.0,
    "Coumarin": 3.0,
}


def _fv() -> FormulaVector:
    return FormulaVector(ingredients=dict(INGREDIENTS))


def _scores() -> dict:
    return FormulaScorer().score(_fv())


def test_default_recommendations_are_ranked_and_typed():
    recommendations = generate_recommendations(_fv(), _scores(), top_n=5, mode="pre_mix")
    assert recommendations
    for rec in recommendations:
        assert rec.target_axis
        assert rec.material
        assert rec.delta > 0
    keys = [(r.identity_preservation or 0.0, r.composite_delta, r.delta) for r in recommendations]
    assert keys == sorted(keys, reverse=True)


def test_default_does_not_target_deep_axes():
    recommendations = generate_recommendations(_fv(), _scores(), top_n=8, mode="pre_mix")
    assert all(r.target_axis not in DEEP_AXES for r in recommendations)


def test_generate_recommendations_is_deterministic():
    first = generate_recommendations(_fv(), _scores(), top_n=5, mode="pre_mix")
    second = generate_recommendations(_fv(), _scores(), top_n=5, mode="pre_mix")
    assert [(r.target_axis, r.material) for r in first] == [
        (r.target_axis, r.material) for r in second
    ]


def test_thermodynamic_state_is_memoized_per_vector():
    scorer = FormulaScorer()
    fv = _fv()
    first = scorer._thermodynamic_state(fv)
    second = scorer._thermodynamic_state(fv)
    assert first is second
    other = FormulaVector(ingredients={"Hedione": 100.0})
    assert scorer._thermodynamic_state(other) is not first
