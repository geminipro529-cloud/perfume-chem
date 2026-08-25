from __future__ import annotations

from types import SimpleNamespace

from engine.pipeline.robustness import audit_formula_robustness


def test_robustness_without_authorized_state_never_calls_legacy(monkeypatch):
    calls: list[object] = []
    monkeypatch.setattr(
        "engine.pipeline.robustness._legacy_audit",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    report = audit_formula_robustness(
        {
            "ingredients_ul": {"Hedione": 20.0, "Iso E Super": 20.0},
            "dilutions": {"Hedione": 1.0, "Iso E Super": 1.0},
        },
        SimpleNamespace(),
    )
    assert calls == []
    assert report.status == "WARN"
    assert report.checked == 0
    assert report.issues
    assert "authorized FormulaState" in report.issues[0].detail


def test_explicit_exploratory_robustness_is_only_legacy_escape(monkeypatch):
    sentinel = object()
    calls: list[object] = []

    def fake(*args, **kwargs):
        calls.append((args, kwargs))
        return sentinel

    monkeypatch.setattr("engine.pipeline.robustness._legacy_audit", fake)
    result = audit_formula_robustness(
        {"ingredients_ul": {"Hedione": 20.0, "Iso E Super": 20.0}},
        SimpleNamespace(),
        allow_unbound_exploratory=True,
    )
    assert result is sentinel
    assert len(calls) == 1
