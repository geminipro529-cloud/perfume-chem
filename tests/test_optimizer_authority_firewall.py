"""Regression tests for the legacy optimizer authority firewall."""

from __future__ import annotations

from engine.optimizer.models import FormulaVector
from engine.optimizer.optimizer import FormulaOptimizer


def test_optimize_preserves_baseline_when_only_legacy_total_exists(monkeypatch):
    optimizer = FormulaOptimizer()
    calls: list[dict[str, float]] = []

    def diagnostic_score(formula, **_kwargs):
        calls.append(dict(formula.ingredients))
        # A historical search would have found ever larger values and mutated
        # the formula. The value now remains a diagnostic annotation only.
        return {"total": 99.0 + len(calls)}

    monkeypatch.setattr(optimizer.scorer, "score", diagnostic_score)
    baseline = FormulaVector(
        ingredients={"Lavender EO": 60.0, "Ambrox Super": 40.0},
        dilutions={"Ambrox Super": 0.25},
    )

    result = optimizer.optimize(baseline)

    assert calls == [{"Lavender EO": 60.0, "Ambrox Super": 40.0}]
    assert result.formula is not baseline
    assert result.formula.ingredients == baseline.ingredients
    assert result.formula.dilutions == baseline.dilutions
    assert result.ranking_status == "WITHHELD"
    assert result.formula_optimization_authority is False
    assert result.selection_basis == "LEGACY_DIAGNOSTIC_TOTAL_NOT_ADMITTED"
    assert result.suggestions[0].startswith("NO_CHANGE:")
    assert any("cannot rank candidates" in reason for reason in result.reasoning)


def test_carles_candidates_keep_generation_order_not_diagnostic_score_order(monkeypatch):
    optimizer = FormulaOptimizer()
    optimizer._inventory = []
    monkeypatch.setattr(
        optimizer,
        "_load_library_accords",
        lambda: [
            ("first-generated", {"Iso E Super": 100.0}),
            ("second-generated", {"Ambrox Super": 100.0}),
        ],
    )

    def diagnostic_score(formula, **_kwargs):
        return {"total": 99.0 if "Ambrox Super" in formula.ingredients else 1.0}

    monkeypatch.setattr(optimizer.scorer, "score", diagnostic_score)

    results = optimizer.carles_grid_search("Lavender EO", n_results=2)

    assert len(results) == 2
    assert results[0].total_score == 1.0
    assert results[1].total_score == 99.0
    assert "Iso E Super" in results[0].formula.ingredients
    assert "Ambrox Super" in results[1].formula.ingredients
    assert all(result.ranking_status == "WITHHELD" for result in results)
    assert all(result.formula_optimization_authority is False for result in results)
    assert all(
        any("UNRANKED_DIAGNOSTIC_CANDIDATE" in reason for reason in result.reasoning)
        for result in results
    )


def test_suggest_is_fast_no_change_by_default(monkeypatch):
    optimizer = FormulaOptimizer()

    def unexpected_score(*_args, **_kwargs):
        raise AssertionError("default no-change suggestion path must not run legacy scoring")

    monkeypatch.setattr(optimizer.scorer, "score", unexpected_score)

    suggestions = optimizer.suggest(
        FormulaVector(ingredients={"Lavender EO": 60.0, "Ambrox Super": 40.0})
    )

    assert len(suggestions) == 1
    assert suggestions[0].startswith("NO_CHANGE:")
    assert "cannot rank candidates" in suggestions[0]
