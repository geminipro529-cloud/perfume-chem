"""The final beam is re-ranked by IFRA class, then named-note detection misses."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from engine.formulation_intelligence import composition_checks as cc
from engine.formulation_intelligence import formula_solver as solver


def _candidate(stock: str) -> tuple:
    return (SimpleNamespace(
        role=SimpleNamespace(role_id="r"), capability=SimpleNamespace(stock_id=stock, candidate=stock),
        score=1.0, alternatives=(),
    ),)


def _setup(monkeypatch, classes: dict[str, str], misses: dict[str, list[str]] | None = None,
           unmet: dict[str, int] | None = None):
    misses = misses or {}
    unmet = unmet or {}
    monkeypatch.setattr(solver, "_role_spec", lambda role: role)
    monkeypatch.setattr(solver, "Choice", lambda role, candidate, score, alternatives: SimpleNamespace(stock=candidate))
    monkeypatch.setattr(solver, "_allocation_choices", lambda a, choices, *args: choices)

    def rows(choices, **_kw):
        stock = choices[0].stock
        return [{"stock": stock}], {}, ["CROWDING_CAP_UNMET:x:40.0"] * unmet.get(stock, 0)

    monkeypatch.setattr(solver, "_formula_rows", rows)
    monkeypatch.setattr(
        cc, "composition_checks",
        lambda formula, formula_name: {"checks": [{"check": "ifra", "status": classes[formula["rows"][0]["stock"]]}]},
    )
    monkeypatch.setattr(
        solver, "_named_note_detection",
        lambda rows, choices: (misses.get(rows[0]["stock"], []), []),
    )


def _rerank(finalists):
    brief = SimpleNamespace(normalized_request="x")
    return solver._rerank_finalists(
        finalists, brief=brief, liquid_total_ul=6000, explicit_quantities=(), exact_material_count=False,
    )


def test_when_the_first_candidate_fails_ifra_the_second_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    finalists = [_candidate("a"), _candidate("b")]
    _setup(monkeypatch, {"a": "FAIL", "b": "PASS"})
    chosen, receipt = _rerank(finalists)

    assert chosen is finalists[1]
    assert receipt["chosen_position"] == 1


def test_fewer_named_note_misses_then_fewer_unmet_caps_break_an_ifra_tie(monkeypatch: pytest.MonkeyPatch) -> None:
    finalists = [_candidate("a"), _candidate("b"), _candidate("c")]
    _setup(monkeypatch, {"a": "WARN", "b": "PASS", "c": "PASS"}, {"a": ["n"], "b": ["n"]}, {"c": 1})
    assert _rerank(finalists)[0] is finalists[2]
    _setup(monkeypatch, {"a": "WARN", "b": "PASS", "c": "PASS"}, {"a": ["n"], "b": ["n"], "c": ["n"]}, {"a": 1, "c": 1})
    assert _rerank(finalists)[0] is finalists[1]


def test_when_all_candidates_fail_todays_winner_stays_and_is_flagged(monkeypatch: pytest.MonkeyPatch) -> None:
    finalists = [_candidate("a"), _candidate("b")]
    _setup(monkeypatch, {"a": "FAIL", "b": "FAIL"}, {"a": ["n"]})
    chosen, receipt = _rerank(finalists)

    assert chosen is finalists[0]
    assert receipt["all_candidates_ifra_fail"] is True


def test_the_receipt_lists_every_candidate(monkeypatch: pytest.MonkeyPatch) -> None:
    finalists = [_candidate("a"), _candidate("b"), _candidate("c")]
    _setup(monkeypatch, {"a": "FAIL", "b": "MISSING", "c": "PASS"}, {"b": ["note"]})
    _chosen, receipt = _rerank(finalists)

    assert [c["stock_ids"] for c in receipt["candidates"]] == [["a"], ["b"], ["c"]]
    assert [c["ifra_class"] for c in receipt["candidates"]] == ["FAIL", "MISSING", "PASS"]
    assert receipt["candidates"][1]["named_note_detection_misses"] == ["note"]
    assert "named_note_detection_unknown" in receipt["candidates"][0]


def test_a_composed_brief_carries_the_candidate_table_in_its_solver_receipt(monkeypatch: pytest.MonkeyPatch) -> None:
    from engine.formulation_intelligence import formula_design_runtime as runtime

    results = []
    real = runtime.solve_formula
    monkeypatch.setattr(runtime, "solve_formula", lambda **kw: results.append(real(**kw)) or results[-1])
    runtime.design_formula(idea="a modern chypre with rose, patchouli and oakmoss")
    receipt = results[0].solver_receipt
    rerank = receipt["finalist_rerank"]

    assert 1 < len(rerank["candidates"]) <= solver.FINALIST_COUNT
    assert len({tuple(c["stock_ids"]) for c in rerank["candidates"]}) == len(rerank["candidates"])
    assert rerank["candidates"][rerank["chosen_position"]]["stock_ids"] == receipt["selected_stock_ids"]
