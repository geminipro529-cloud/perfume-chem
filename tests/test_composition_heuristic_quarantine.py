from __future__ import annotations

import pytest

from engine.optimizer.models import FormulaVector
from engine.optimizer.optimizer import (
    CompositionRankingProhibitedError,
    FormulaOptimizer,
)
from engine.optimizer.scoring import FormulaScorer


def _diagnostic_formula() -> FormulaVector:
    return FormulaVector(
        ingredients={
            "Hedione": 45.0,
            "Iso E Super": 35.0,
            "Coumarin": 10.0,
            "Lavender EO": 10.0,
        },
        dilutions={
            "Hedione": 1.0,
            "Iso E Super": 1.0,
            "Coumarin": 0.2,
            "Lavender EO": 1.0,
        },
    )


def test_active_composition_scores_declare_zero_ranking_authority() -> None:
    scores = FormulaScorer().score(_diagnostic_formula())

    assert scores["_decision_authority"] == {
        "state": "DIAGNOSTIC_ONLY",
        "ranking_authority": False,
        "formula_mutation_authority": False,
        "sensory_claim_authority": False,
        "basis": (
            "Composition-derived heuristic axes cannot establish target fidelity, "
            "depth, richness, liking, or beauty."
        ),
    }


def test_legacy_composite_is_replay_only_and_never_ranking_authority() -> None:
    scores = FormulaScorer().score_legacy_replay(_diagnostic_formula())

    assert scores["_decision_authority"]["state"] == "LEGACY_REPLAY_ONLY"
    assert scores["_decision_authority"]["ranking_authority"] is False
    assert scores["_decision_authority"]["formula_mutation_authority"] is False


def test_optimizer_cannot_mutate_formula_from_composition_heuristics() -> None:
    optimizer = FormulaOptimizer()

    with pytest.raises(
        CompositionRankingProhibitedError,
        match="Architectural Delta Engine",
    ):
        optimizer.optimize(_diagnostic_formula())


def test_carles_grid_cannot_rank_candidates_from_composition_heuristics() -> None:
    optimizer = FormulaOptimizer()

    with pytest.raises(
        CompositionRankingProhibitedError,
        match="blinded exact-scope evidence",
    ):
        optimizer.carles_grid_search("Hedione")
