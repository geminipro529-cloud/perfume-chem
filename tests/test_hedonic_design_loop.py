"""Computer-only search contracts; synthetic objectives are not scent evidence."""

import pytest

from engine.optimizer import gate_aware


def run(evaluate, **kwargs):
    assert hasattr(gate_aware, "optimize_hedonic_design")
    return gate_aware.optimize_hedonic_design(
        {"anchor": 50., "support": 50.}, evaluate=evaluate,
        criteria=("identity", "body"), scenarios=("nominal", "perturbed"),
        transfers=(("support", "anchor"), ("anchor", "support")),
        step_sizes=(10., 5.), bounds={"anchor": (20., 80.), "support": (20., 80.)},
        **kwargs,
    )


def test_search_reaches_pattern_without_sensory_input_or_mutating_baseline():
    result = run(lambda f, s: {"identity": abs(70-f["anchor"]), "body": 0.})
    assert result["status"] == "COMPUTATIONAL_TARGET_MET"
    assert result["selected"] == {"anchor": 70., "support": 30.}
    assert result["sensory_validated"] is False
    assert result["requires_premix_trial"] is False
    assert [h["candidate"]["anchor"] for h in result["history"] if h["accepted"]] == [60., 70.]


def test_nominal_improvement_cannot_hide_perturbed_regression():
    result = run(lambda f, s: {
        "identity": abs((70 if s == "nominal" else 50)-f["anchor"]), "body": 0.})
    assert result["selected"]["anchor"] == 50.
    assert result["status"] == "PLATEAU"
    assert any(h["reason"] == "criterion_regression" for h in result["history"])


def test_body_improvement_cannot_buy_identity_loss():
    result = run(lambda f, s: {"identity": abs(50-f["anchor"]), "body": 100-f["anchor"]})
    assert result["selected"]["anchor"] == 50.


@pytest.mark.parametrize("value", [None, float("nan"), float("inf"), -1.])
def test_invalid_evidence_never_becomes_success(value):
    result = run(lambda f, s: {"identity": value, "body": 0.})
    assert result["status"] == "EVALUATION_UNAVAILABLE"
    assert result["selected"]["anchor"] == 50.


def test_missing_criterion_is_not_zero_loss():
    assert run(lambda f, s: {"body": 0.})["status"] == "EVALUATION_UNAVAILABLE"


def test_evaluator_exception_preserves_incumbent():
    def evaluate(f, s):
        if f["anchor"] != 50.:
            raise RuntimeError("model unavailable")
        return {"identity": 20., "body": 0.}
    result = run(evaluate)
    assert result["selected"]["anchor"] == 50.
    assert result["status"] == "EVALUATION_UNAVAILABLE"


def test_budget_terminates_even_with_improving_candidates():
    result = run(lambda f, s: {"identity": 100-f["anchor"], "body": 0.}, max_rounds=1)
    assert result["status"] == "BUDGET_EXHAUSTED"
    assert result["selected"]["anchor"] == 60.


def test_external_gate_scores_are_not_an_objective():
    result = run(lambda f, s: {"identity": 10., "body": 10., "ifra": f["anchor"]})
    assert result["status"] == "PLATEAU"
    assert result["selected"]["anchor"] == 50.


def test_composition_constraint_blocks_a_better_scoring_candidate():
    result = run(lambda f, s: {"identity": 100-f["anchor"], "body": 0.},
                 feasible=lambda f: f["anchor"] <= 50.)
    assert result["selected"]["anchor"] == 50.
    assert any(h["reason"] == "composition_constraint" for h in result["history"])


def test_cached_candidates_are_not_evaluated_again():
    seen = set()
    def evaluate(f, s):
        key = (f["anchor"], s)
        assert key not in seen
        seen.add(key)
        return {"identity": abs(65-f["anchor"]), "body": 0.}
    result = run(evaluate)
    assert result["status"] == "COMPUTATIONAL_TARGET_MET"
    assert result["selected"]["anchor"] == 65.


@pytest.mark.parametrize("budget", [0, -1, 1.5, True])
def test_invalid_budget_is_rejected_before_evaluation(budget):
    with pytest.raises(ValueError):
        run(lambda f, s: {"identity": 0., "body": 0.}, max_rounds=budget)


def test_evaluator_cannot_mutate_the_selected_formula():
    def evaluate(f, s):
        f["anchor"] = 999.
        return {"identity": 0., "body": 0.}
    assert run(evaluate)["selected"] == {"anchor": 50., "support": 50.}


def test_trials_keep_total_and_bounds_for_every_evaluated_candidate():
    def evaluate(f, s):
        assert sum(f.values()) == 100.
        assert 20. <= f["anchor"] <= 80.
        return {"identity": 100-f["anchor"], "body": 0.}
    result = run(evaluate)
    assert result["selected"] == {"anchor": 80., "support": 20.}
    assert result["status"] == "PLATEAU"
