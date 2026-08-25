from __future__ import annotations

import pytest

from engine.pipeline.simulator import SimulationAuthorityError, simulate_formula


class DummyState:
    pass


def test_canonical_simulator_requires_authorized_initial_state(monkeypatch):
    calls: list[object] = []
    monkeypatch.setattr(
        "engine.pipeline.simulator._legacy_simulate",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    with pytest.raises(SimulationAuthorityError):
        simulate_formula({"Hedione": 20.0})
    assert calls == []


def test_explicit_exploratory_mode_can_use_legacy_builder(monkeypatch):
    calls: list[object] = []

    def fake(*args, **kwargs):
        calls.append((args, kwargs))
        return ["ok"]

    monkeypatch.setattr("engine.pipeline.simulator._legacy_simulate", fake)
    result = simulate_formula(
        {"Hedione": 20.0},
        allow_unbound_exploratory=True,
    )
    assert result == ["ok"]
    assert len(calls) == 1
    assert calls[0][1]["initial_state"] is None


def test_authorized_initial_state_is_forwarded_exactly(monkeypatch):
    calls: list[object] = []
    state = DummyState()

    def fake(*args, **kwargs):
        calls.append((args, kwargs))
        return ["ok"]

    monkeypatch.setattr("engine.pipeline.simulator._legacy_simulate", fake)
    result = simulate_formula(
        {"Hedione": 20.0},
        initial_state=state,
    )
    assert result == ["ok"]
    assert len(calls) == 1
    assert calls[0][1]["initial_state"] is state
