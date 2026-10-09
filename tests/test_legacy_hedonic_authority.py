"""Authority and coverage regressions for the legacy fixed-valence scorer."""

from __future__ import annotations

import pytest

from engine.hedonic_model import score_hedonic
from engine.optimizer.models import FormulaVector
from engine.optimizer.scoring import FormulaScorer


def _assert_diagnostic_only(report) -> None:
    assert report.classification == "HEURISTIC_DIAGNOSTIC_INDEX"
    assert report.ranking_status == "WITHHELD"
    assert report.formula_optimization_authority is False
    assert report.sensory_validation_status == "NOT_ESTABLISHED"
    assert report.full_formula_pleasantness_status == "NOT_ESTABLISHED"
    assert report.pleasantness_class_scope == "FIXED_VALENCE_TABLE_SUBSET_ONLY"


def test_zero_table_coverage_keeps_legacy_value_but_exposes_missingness() -> None:
    report = score_hedonic({"Citral": 100.0})

    assert report.score == 50
    assert report.pleasantness_class == "unknown"
    assert report.coverage_status == "ZERO_TABLE_COVERAGE"
    assert report.rated_active_fraction == 0.0
    assert report.unrated_active_fraction == 1.0
    assert report.rated_materials == []
    assert report.unrated_materials == ["Citral"]
    assert any("not measured full-formula pleasantness" in row for row in report.diagnostics)
    _assert_diagnostic_only(report)


def test_partial_coverage_cannot_masquerade_as_full_formula_pleasantness() -> None:
    report = score_hedonic({"Vanillin": 1.0, "Citral": 999.0})

    # Rated-subset value: Vanillin's crowd value 0.702 -> (0.702 + 1) / 2 * 100, no coherence bonus.
    assert report.score == 85.1
    assert report.pleasantness_class == "highly_pleasant"
    assert report.coverage_status == "PARTIAL_TABLE_COVERAGE"
    assert report.rated_active_fraction == pytest.approx(0.001)
    assert report.unrated_active_fraction == pytest.approx(0.999)
    assert report.rated_materials == ["Vanillin"]
    assert report.unrated_materials == ["Citral"]
    assert any("apply only to rated labels" in row for row in report.diagnostics)
    _assert_diagnostic_only(report)


def test_full_table_coverage_is_still_not_sensory_validation() -> None:
    report = score_hedonic({"Vanillin": 1.0, "Hedione": 3.0})

    assert report.coverage_status == "FULL_TABLE_COVERAGE"
    assert report.rated_active_fraction == 1.0
    assert report.unrated_active_fraction == 0.0
    assert report.rated_materials == ["Vanillin", "Hedione"]
    assert report.unrated_materials == []
    _assert_diagnostic_only(report)


def test_formula_scorer_exposes_authority_for_every_public_numeric_output() -> None:
    scores = FormulaScorer().score(
        FormulaVector(ingredients={"Vanillin": 0.1, "Citral": 99.9})
    )

    authority = scores["_score_authority"]
    public_numeric = {
        key
        for key, value in scores.items()
        if not key.startswith("_") and isinstance(value, (int, float))
    }
    assert authority["classification"] == "HEURISTIC_DIAGNOSTIC_INDEX"
    assert authority["scope"] == "ALL_NUMERIC_OUTPUTS_IN_THIS_RESULT"
    assert set(authority["axis_authority"]) == public_numeric
    assert set(authority["axis_authority"].values()) == {
        "HEURISTIC_DIAGNOSTIC_INDEX"
    }
    assert authority["ranking_status"] == "WITHHELD"
    assert authority["formula_optimization_authority"] is False
    assert authority["sensory_validation_status"] == "NOT_ESTABLISHED"
    assert authority["diagnostic_total"] == scores["total"]

    coverage = scores["_hedonic_coverage"]
    assert coverage["coverage_status"] == "PARTIAL_TABLE_COVERAGE"
    assert coverage["rated_active_fraction"] == pytest.approx(0.001)
    assert coverage["unrated_active_fraction"] == pytest.approx(0.999)
    assert coverage["rated_materials"] == ["Vanillin"]
    assert coverage["unrated_materials"] == ["Citral"]
    assert coverage["full_formula_pleasantness_status"] == "NOT_ESTABLISHED"
    assert coverage["formula_optimization_authority"] is False

    science_hedonic = scores["_science"]["hedonic"]
    assert science_hedonic["pleasantness"] == "highly_pleasant"
    assert science_hedonic["pleasantness_scope"] == "FIXED_VALENCE_TABLE_SUBSET_ONLY"
    assert science_hedonic["coverage_status"] == "PARTIAL_TABLE_COVERAGE"
    assert science_hedonic["full_formula_pleasantness_status"] == "NOT_ESTABLISHED"
    assert science_hedonic["classification"] == "HEURISTIC_DIAGNOSTIC_INDEX"
    assert science_hedonic["ranking_status"] == "WITHHELD"
    assert science_hedonic["formula_optimization_authority"] is False
