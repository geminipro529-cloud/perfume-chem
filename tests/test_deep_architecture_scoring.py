"""Phase 2/3 scoring tests: the Deep Architecture block must be strictly opt-in."""
from __future__ import annotations

from engine.knowledge.deep_architecture import DIMENSIONS, DeepArchitectureConfig
from engine.optimizer.models import FormulaVector
from engine.optimizer.scoring import FormulaScorer

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


def test_default_config_is_disabled_and_adds_no_block():
    scores = FormulaScorer().score(_fv(), deep_architecture=DeepArchitectureConfig())
    assert "deep_architecture" not in scores


def test_disabled_is_identical_to_no_config():
    without = FormulaScorer().score(_fv())
    disabled = FormulaScorer().score(_fv(), deep_architecture=DeepArchitectureConfig(enabled=False))
    assert disabled == without


def test_enabled_adds_block_and_does_not_change_any_axis():
    base = FormulaScorer().score(_fv())
    enabled = FormulaScorer().score(
        _fv(), deep_architecture=DeepArchitectureConfig(enabled=True, profile="woody")
    )
    assert "deep_architecture" in enabled
    for key, value in base.items():
        assert enabled[key] == value, key


def test_block_shape_authority_and_evidence_counts():
    enabled = FormulaScorer().score(
        _fv(), deep_architecture=DeepArchitectureConfig(enabled=True, profile="woody")
    )
    block = enabled["deep_architecture"]
    assert set(block["dimensions"]) == set(DIMENSIONS)
    for dim, entry in block["dimensions"].items():
        assert 0.0 <= entry["score"] <= 100.0, dim
        assert entry["min"] <= entry["target"] <= entry["max"], dim
        assert entry["authority"] in {"STRUCTURAL_ARCHITECTURE", "PREDICTED_PHYSICAL"}
        assert entry["evidence_refs"] >= 10, dim
    assert block["dimensions"]["spatial_projection"]["authority"] == "PREDICTED_PHYSICAL"
    assert "predicted physical" in block["authority_note"]


def test_enabled_scoring_is_deterministic():
    first = FormulaScorer().score(_fv(), deep_architecture=DeepArchitectureConfig(enabled=True))
    second = FormulaScorer().score(_fv(), deep_architecture=DeepArchitectureConfig(enabled=True))
    assert first["deep_architecture"] == second["deep_architecture"]


def test_auto_profile_resolves():
    enabled = FormulaScorer().score(
        _fv(), deep_architecture=DeepArchitectureConfig(enabled=True, profile="auto")
    )
    profile = enabled["deep_architecture"]["profile"]
    assert profile["key"]
    assert profile["level"] in {"family", "subfamily", "archetype", "generic"}


def test_flatten_promotes_deep_architecture_dimensions():
    from engine.formula_recommendations import (
        flatten_deep_architecture_scores,
        identify_weak_axes,
    )

    base = {"geometric_total": 50.0, "longevity": 70.0}
    assert flatten_deep_architecture_scores(base) == base  # no-op without the block

    tagged = {
        **base,
        "deep_architecture": {
            "dimensions": {
                "temporal_layering": {"score": 12.0},
                "function_balance": {"score": 90.0},
            }
        },
    }
    flat = flatten_deep_architecture_scores(tagged)
    assert flat["temporal_layering"] == 12.0
    assert flat["function_balance"] == 90.0
    weakest = identify_weak_axes(flat, n=2)
    assert ("temporal_layering", 12.0) in weakest


def test_score_axis_supports_deep_dimensions():
    scorer = FormulaScorer()
    for axis in (
        "depth_stacking",
        "temporal_layering",
        "spatial_projection",
        "integration_capacity",
        "function_balance",
        "legibility_coherence",
    ):
        value = scorer.score_axis(_fv(), axis)
        assert 0.0 <= value <= 100.0, axis
    assert scorer.score_axis(_fv(), "depth_stacking") > 0.0


def test_deep_axis_recommendations_fire_when_opt_in():
    from engine.formula_recommendations import generate_recommendations

    # Heart-only chassis: no blender/fixative stack — depth/structure axes are weak.
    fv = FormulaVector(
        ingredients={"Alpha Isomethyl Ionone": 70.0, "Coumarin": 20.0, "Birch Tar": 10.0}
    )
    scores = FormulaScorer().score(
        fv, deep_architecture=DeepArchitectureConfig(enabled=True, profile="woody")
    )
    recommendations = generate_recommendations(
        fv, scores, inventory=None, top_n=6, mode="pre_mix"
    )
    deep_axes = {
        "depth_stacking",
        "temporal_layering",
        "spatial_projection",
        "integration_capacity",
        "function_balance",
        "legibility_coherence",
    }
    assert any(r.target_axis in deep_axes for r in recommendations)
    # And default-off scores expose no deep axes to the recommender.
    plain = FormulaScorer().score(_fv())
    assert "deep_architecture" not in plain


def _gate_formula():
    from engine.pipeline.gates import ReleaseGateConfig, gate_formula

    formula = {
        "number": 1,
        "name": "Deep architecture wiring",
        "ingredients_ul": {
            "Iso E Super": 1600.0,
            "Hedione": 1200.0,
            "Galaxolide": 800.0,
            "Alpha Isomethyl Ionone": 700.0,
            "Ethylene Brassylate": 700.0,
            "Bergamot FCF": 500.0,
            "Vanillin": 300.0,
            "Birch Tar": 50.0,
        },
        "dilutions": {},
        "body": "Deep architecture wiring",
    }
    off = gate_formula(formula, ReleaseGateConfig(expected_concentrate_ul=6000.0, brief="generic"))
    on = gate_formula(
        formula,
        ReleaseGateConfig(
            expected_concentrate_ul=6000.0,
            brief="generic",
            family_archetype="iris_amber_woody.classic",
            deep_architecture_enabled=True,
        ),
    )
    return off, on


def test_deep_architecture_gate_is_opt_in():
    off, on = _gate_formula()
    assert "deep_architecture" not in {g.gate for g in off.gates}
    gate = next(g for g in on.gates if g.gate == "deep_architecture")
    assert gate.status in {"PASS", "WARN"}
    assert set(gate.data["dimensions"]) == set(DIMENSIONS)
    assert on.config_summary["deep_architecture_enabled"] is True
    assert off.config_summary["deep_architecture_enabled"] is False


def test_deep_architecture_gate_never_changes_formula_status_off():
    off, _ = _gate_formula()
    from engine.pipeline.gates import ReleaseGateConfig, gate_formula

    formula = {
        "number": 1,
        "name": "Deep architecture wiring",
        "ingredients_ul": {
            "Iso E Super": 1600.0,
            "Hedione": 1200.0,
            "Galaxolide": 800.0,
            "Alpha Isomethyl Ionone": 700.0,
            "Ethylene Brassylate": 700.0,
            "Bergamot FCF": 500.0,
            "Vanillin": 300.0,
            "Birch Tar": 50.0,
        },
        "dilutions": {},
        "body": "Deep architecture wiring",
    }
    plain = gate_formula(formula, ReleaseGateConfig(expected_concentrate_ul=6000.0, brief="generic"))
    assert plain.status == off.status
