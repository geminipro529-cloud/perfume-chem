"""The wider-beam retry runs only when a missing role could still be filled."""

from types import SimpleNamespace

from engine.formulation_intelligence import formula_solver as solver


def _solve(monkeypatch, pool):
    calls = []

    def fake_solve(**kwargs):
        calls.append(kwargs["beam_width"])
        return (), ("Top citrus",)

    monkeypatch.setattr(solver, "_solve_assignments", fake_solve)
    monkeypatch.setattr(solver, "_unary_rank_for_role", lambda *_a, **_k: list(pool))
    role = SimpleNamespace(label="Top citrus", role_id="top")
    brief = SimpleNamespace(roles=(role,), architecture_plan={}, requested_fruits=())
    result = solver.solve_formula(
        brief=brief, index=SimpleNamespace(capabilities=()), liquid_total_ul=1000,
        explicit_quantities=(), avoid=(), beam_width=8,
    )
    assert result.missing_roles == ("Top citrus",)
    return calls


def test_retry_runs_when_a_missing_role_has_candidates(monkeypatch):
    assert _solve(monkeypatch, [(1.0, object())]) == [8, 32]


def test_retry_is_skipped_when_a_missing_role_has_no_candidates(monkeypatch):
    assert _solve(monkeypatch, []) == [8]
