from __future__ import annotations

from pathlib import Path

from engine.family_scorer import FAMILY_WEIGHT_PRESETS
from engine.formula_analyzer import format_scores
from engine.optimizer.models import FormulaVector
from engine.optimizer.scoring import FormulaScorer
from scripts import (
    optimize_cobalt_cedar_air,
    score_collection_formulas,
    score_designer_prestige_18,
    verify_formula_workflow,
)

ROOT = Path(__file__).resolve().parents[1]


def _formula() -> FormulaVector:
    return FormulaVector(
        ingredients={"Hedione": 60.0, "Iso E Super": 40.0},
        dilutions={"Hedione": 1.0, "Iso E Super": 1.0},
    )


def test_every_family_profile_disables_composition_derived_hedonic_weight() -> None:
    for profile in FAMILY_WEIGHT_PRESETS.values():
        if isinstance(profile, str):
            continue
        assert profile.hedonic == 0.0


def test_collection_and_optimizer_axis_lists_exclude_hedonic() -> None:
    assert "hedonic" not in optimize_cobalt_cedar_air.AXES
    assert optimize_cobalt_cedar_air.CUSTOM_WEIGHTS.hedonic == 0.0
    assert "hedonic" not in score_collection_formulas.AXES
    assert "hedonic" not in score_designer_prestige_18.AXES


def test_formula_analyzer_renders_liking_as_evidence_state() -> None:
    rendered = format_scores(FormulaScorer().score(_formula()))
    assert "LIKING EVIDENCE" in rendered
    assert "NOT_TESTED" in rendered
    assert "hedonic" not in rendered.lower()


def test_workflow_complexity_does_not_use_a_synthetic_hedonic_default() -> None:
    base = FormulaScorer().score(_formula())
    radar = base["_radar"]
    low = verify_formula_workflow._normalize_legacy_score_axes(
        _formula(), {**base, "hedonic": 0.0}, radar
    )
    high = verify_formula_workflow._normalize_legacy_score_axes(
        _formula(), {**base, "hedonic": 100.0}, radar
    )
    assert low["complexity"] == high["complexity"]


def test_c0_optimizer_fixture_uses_explicit_legacy_replay() -> None:
    source = (ROOT / "scripts" / "verify_c0_physical_model_inventory.py").read_text(
        encoding="utf-8"
    )
    assert "FormulaScorer(ObjectiveWeights()).score_legacy_replay(vector)" in source


def test_active_recommendation_path_has_no_hedonic_axis_mapping() -> None:
    source = (ROOT / "engine" / "formula_recommendations.py").read_text(
        encoding="utf-8"
    )
    assert '"hedonic": ["character_balance"]' not in source


def test_legacy_hedonic_function_call_census_is_closed() -> None:
    calls: list[str] = []
    for base in (ROOT / "engine", ROOT / "scripts"):
        for path in base.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if "score_hedonic(" in text:
                calls.append(path.relative_to(ROOT).as_posix())
    assert sorted(calls) == [
        "engine/hedonic_model.py",
        "engine/optimizer/scoring.py",
        "scripts/verify_c0_physical_model_inventory.py",
    ]
