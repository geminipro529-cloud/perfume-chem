from __future__ import annotations

import pytest

from engine.hedonic_model import score_hedonic
from engine.optimizer.models import (
    FormulaVector,
    LegacyObjectiveWeightsV1,
    ObjectiveWeights,
)
from engine.optimizer.scoring import FormulaScorer


def _formula() -> FormulaVector:
    return FormulaVector(
        ingredients={
            "Hedione": 40.0,
            "Iso E Super": 35.0,
            "Coumarin": 15.0,
            "Lavender EO": 10.0,
        },
        dilutions={
            "Hedione": 1.0,
            "Iso E Super": 1.0,
            "Coumarin": 0.2,
            "Lavender EO": 1.0,
        },
    )


def test_direct_legacy_hedonic_model_remains_importable() -> None:
    report = score_hedonic(_formula().ingredients, _formula().dilutions)
    assert report.pleasantness_class == "pleasant"


def test_legacy_replay_preserves_frozen_v1_payload() -> None:
    scores = FormulaScorer().score_legacy_replay(_formula())
    assert scores["hedonic"] == 85.2
    assert scores["arithmetic_total"] == 63.1
    assert scores["geometric_total"] == 50.7
    assert scores["total"] == 50.7
    assert scores["_science"]["hedonic"] == {
        "valence": 0.686,
        "pleasantness": "pleasant",
        "diagnostics": [
            "Hedonic class: pleasant (mean valence +0.69)",
            "✓ >80% of formula mass is hedonically pleasant",
        ],
    }


def test_active_score_has_no_composition_derived_hedonic_value() -> None:
    scores = FormulaScorer().score(_formula())
    assert "hedonic" not in scores
    assert scores["_hedonic_evidence"]["state"] == "NOT_TESTED"
    assert "hedonic" not in scores["_science"]


def test_active_score_does_not_call_legacy_hedonic_model(monkeypatch) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("legacy hedonic model entered active scoring")

    monkeypatch.setattr("engine.optimizer.scoring.score_hedonic", forbidden)
    scores = FormulaScorer().score(_formula())
    assert scores["_hedonic_evidence"]["state"] == "NOT_TESTED"


def test_hedonic_single_axis_is_evidence_gated() -> None:
    with pytest.raises(ValueError, match="hedonic is evidence-gated"):
        FormulaScorer().score_axis(_formula(), "hedonic")


def test_nonzero_active_hedonic_weight_is_rejected() -> None:
    with pytest.raises(ValueError, match="hedonic is evidence-gated"):
        FormulaScorer(ObjectiveWeights(hedonic=0.1)).score(_formula())


def test_active_and_legacy_weight_defaults_are_separate() -> None:
    assert ObjectiveWeights().hedonic == 0.0
    assert LegacyObjectiveWeightsV1().hedonic == 0.5
