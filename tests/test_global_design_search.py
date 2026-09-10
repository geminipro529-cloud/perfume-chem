"""Global experimental search contracts, using hand-defined objectives."""
import math

import pytest

from engine.optimizer import gate_aware


def run(evaluate=None, **changes):
    function = getattr(gate_aware, "optimize_global_design", None)
    assert callable(function), "Global experimental search is missing"
    kwargs = dict(baseline={"a": 9., "b": 1., "fixed": 2.},
                  bounds={"a": (0., 10.), "b": (0., 10.), "fixed": (2., 2.)},
                  evaluate=evaluate or objective, budget=32, seed=17, max_workers=2)
    kwargs.update(changes)
    return function(**kwargs)


def objective(formula):
    # The basin near b=1 has loss >=4; crossing b=5 reveals the better basin.
    b = formula["b"]
    loss = 4 + (b - 1) ** 2 if b < 5 else (b - 8) ** 2
    return {"basis": "experimental_design_proxy", "losses": {"target": loss},
            "diagnostic": "synthetic nonconvex objective"}


def test_global_search_escapes_baseline_local_basin_without_sensory_promotion():
    result = run()
    best = result["ranked_candidates"][0]
    assert best["formula"]["b"] > 5
    assert best["score"] < 1
    assert result["baseline"]["score"] == 4
    assert result["sensory_validated"] is False
    assert result["release_authorized"] is False
    assert result["global_optimum_proven"] is False
    assert result["predicted_liking"] is None
    assert {r["source"] for r in result["archive"]} == {"global", "refinement"}


def test_candidates_preserve_total_bounds_frozen_stock_and_hard_feasibility():
    result = run(feasible=lambda f: f["b"] <= 8.5)
    for record in result["archive"] + result["comparator"]["archive"]:
        formula = record["formula"]
        assert set(formula) == {"a", "b", "fixed"}
        assert sum(formula.values()) == pytest.approx(12., abs=1e-10)
        assert 0 <= formula["a"] <= 10
        assert 0 <= formula["b"] <= 8.5
        assert formula["fixed"] == 2


def test_global_stream_is_independent_of_baseline_proportions_and_key_order():
    left = run()
    right = run(baseline={"fixed": 2., "b": 7., "a": 3.})
    def stream(result):
        return [r["formula"] for r in result["archive"] if r["source"] == "global"]
    assert stream(left) == stream(right)
    assert left["comparator"]["archive"] == right["comparator"]["archive"]


def test_seed_and_worker_count_produce_identical_ranked_evaluation_results():
    assert run(max_workers=1) == run(max_workers=4)


def test_optimizer_and_independent_random_receive_equal_actual_evaluation_budgets():
    result = run(budget=21)
    assert result["evaluation_counts"] == {
        "baseline": 1, "optimizer": 21, "random": 21, "total": 43}
    assert result["benchmark_equal_budget"] is True
    assert result["search_complete"] is True
    assert result["archive"] != result["comparator"]["archive"]
    for records in (result["archive"], result["comparator"]["archive"]):
        assert len({tuple(sorted(r["formula"].items())) for r in records}) == 21


@pytest.mark.parametrize("bad", [
    {"basis": "experimental_design_proxy", "losses": {"x": math.nan}},
    {"basis": "experimental_design_proxy", "losses": {"x": -1}},
    {"basis": "experimental_design_proxy", "losses": {}},
    {"basis": "qualitative_hypothesis", "losses": {"x": 0}},
    {"basis": "experimental_design_proxy", "losses": {"x": True}},
])
def test_invalid_evaluations_are_not_ranked_or_reported_as_success(bad):
    result = run(evaluate=lambda f: bad, budget=4)
    assert result["ranked_candidates"] == []
    assert result["experimental_recommendation"] is None
    assert result["status"] == "EVALUATION_ERROR"
    assert result["search_complete"] is False
    assert all(r["error"] and r["score"] is None for r in result["archive"])


def test_singleton_domain_terminates_with_honest_actual_counts():
    result = run(bounds={"a": (9., 9.), "b": (1., 1.), "fixed": (2., 2.)}, budget=8)
    assert result["evaluation_counts"] == {
        "baseline": 1, "optimizer": 1, "random": 1, "total": 3}
    assert result["status"] == "DOMAIN_OR_ATTEMPT_LIMIT"
    assert result["search_complete"] is False
    assert result["benchmark_equal_budget"] is True


def test_invalid_baseline_and_unresolved_domain_are_rejected_before_evaluation():
    with pytest.raises(ValueError):
        run(baseline={"a": 11., "b": -1., "fixed": 2.})
    with pytest.raises(ValueError):
        run(feasible=lambda f: False)
    with pytest.raises(ValueError):
        run(budget=True)


def test_objective_components_are_explicitly_summed_and_diagnostics_survive():
    result = run(evaluate=lambda f: {
        "basis": "measured_model_prediction", "losses": {"first": 2., "second": 3.},
        "provenance": {"id": "test-fixture"}}, budget=4)
    assert all(r["score"] == 5 for r in result["ranked_candidates"])
    assert result["ranked_candidates"][0]["evaluation"]["provenance"] == {"id": "test-fixture"}
    assert result["aggregation"] == "SUM_OF_CALLER_SCALED_LOSSES"


def test_raised_evaluator_failure_is_retained_and_json_serializable():
    import json

    def broken(formula):
        raise RuntimeError("fixture unavailable")

    result = run(evaluate=broken, budget=3)
    assert result["evaluation_error_count"] == 7
    assert result["comparator"]["best_score"] is None
    assert "fixture unavailable" in result["baseline"]["error"]
    json.dumps(result, allow_nan=False)


def test_nan_evaluator_diagnostics_do_not_break_receipt_serialization():
    import json

    result = run(evaluate=lambda f: {
        "basis": "experimental_design_proxy", "losses": {"target": math.nan}}, budget=3)
    json.dumps(result, allow_nan=False)
    assert result["ranked_candidates"] == []


def test_changed_objective_schema_cannot_win_by_dropping_a_loss():
    def changing(formula):
        losses = {"target": 100., "other": 100.} if formula["b"] == 1 else {"target": 0.}
        return {"basis": "experimental_design_proxy", "losses": losses}

    result = run(evaluate=changing, budget=3)
    assert result["ranked_candidates"] == []
    assert result["status"] == "EVALUATION_ERROR"


def test_measure_zero_feasibility_ends_at_attempt_limit_without_fake_evaluations():
    result = run(feasible=lambda f: f["b"] == 1., budget=2)
    assert result["evaluation_counts"] == {
        "baseline": 1, "optimizer": 0, "random": 0, "total": 1}
    assert result["status"] == "DOMAIN_OR_ATTEMPT_LIMIT"
    assert result["attempts"]["random"] == result["attempt_limit_per_arm"]
def test_best_visited_candidate_is_not_silently_claimed_better_than_baseline():
    result = gate_aware.optimize_global_design(
        {"a": 5., "b": 5.}, bounds={"a": (0., 10.), "b": (0., 10.)},
        evaluate=lambda f: {"losses": {"distance": (f["a"] - 5.) ** 2},
                            "basis": "experimental_design_proxy"}, budget=8)
    assert result["baseline_included_in_ranking"] is False
    assert result["optimizer_minus_baseline_best"] > 0
    assert result["improves_baseline_proxy"] is False


def test_partial_evaluator_failure_keeps_observations_without_recommending():
    def partial(formula):
        if formula["a"] > 8.:
            raise ValueError("missing calibration")
        return objective(formula)
    result = run(partial)
    assert result["status"] == "EVALUATION_ERROR"
    assert result["ranked_candidates"]
    assert result["best_observed_candidate"] is not None
    assert result["experimental_recommendation"] is None
