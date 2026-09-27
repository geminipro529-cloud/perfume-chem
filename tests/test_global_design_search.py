"""Global experimental search contracts, using hand-defined objectives."""
import math

import pytest

from engine.optimizer import gate_aware


def authority(losses=("target",), *, endpoint="calibrated_numerical_endpoint"):
    return {
        "endpoint_capability": endpoint,
        "model_identity": "synthetic-fixture-model-v1",
        "source_identity": ["fixture-source-sha256"],
        "applicable_materials": ["a", "b", "fixed"],
        "applicable_scenarios": ["synthetic-fixed-scenario"],
        "uncertainty_intervals": {name: [0.0, 1000.0] for name in losses},
        "non_release_scope": "NON_RELEASE_COMPUTATIONAL_COMPARISON_ONLY",
        "release_authorized": False,
        "compounding_authorized": False,
        "safety_authorized": False,
        "pleasantness_authorized": False,
        "liking_authorized": False,
    }


def checkpoint2_authority(
    *,
    endpoint_id="measured_intensity_comparison",
    feature_lineage=("GAS_CURVE_INTENSITY",),
    endpoint_authority=None,
):
    return {
        "contract_version": "checkpoint2-endpoint-authority-v1",
        "endpoint_id": endpoint_id,
        "capability_ids": ["curve-capability-v1"],
        "model_id": "mixture-rule-v1",
        "source_ids": ["source-sha256"],
        "input_unit": "ug/L_air",
        "source_range_status": "IN_RANGE",
        "applicable_material_ids": ["a", "b"],
        "applicable_scenario": "fixture-gas-mixture",
        "feature_lineage": list(feature_lineage),
        "interval_method": "clustered-fixture-interval",
        "endpoint_authority": endpoint_authority
        or {
            "character": False,
            "intensity": True,
            "pleasantness": False,
            "population_liking": False,
            "personal_liking": False,
        },
        "evidence_admission_authorized": False,
        "physical_experiment_authorized": False,
        "compounding_authorized": False,
        "purchase_authorized": False,
        "inventory_mutation_authorized": False,
        "safety_authorized": False,
        "release_authorized": False,
        "formula_optimization_authority": False,
        "beauty_authorized": False,
    }


def checkpoint2_evaluator(*, overlap=True, lineage=("GAS_CURVE_INTENSITY",)):
    def evaluate(formula):
        loss = float(formula["a"])
        interval = [0.0, 100.0] if overlap else [loss, loss]
        return {
            "endpoint_id": "measured_intensity_comparison",
            "loss": loss,
            "prediction_interval": interval,
            "coverage": {"materials": ["a", "b"], "fraction": 1.0},
            "feature_lineage": list(lineage),
            "model_signs": {"strongest": 1, "partial_addition": 1},
        }

    return evaluate


def run(evaluate=None, **changes):
    function = getattr(gate_aware, "optimize_global_design", None)
    assert callable(function), "Global experimental search is missing"
    kwargs = dict(baseline={"a": 9., "b": 1., "fixed": 2.},
                  bounds={"a": (0., 10.), "b": (0., 10.), "fixed": (2., 2.)},
                  evaluate=evaluate or objective, budget=32, seed=17, max_workers=2,
                  evaluator_authority=authority())
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
        "provenance": {"id": "test-fixture"}}, budget=4,
        evaluator_authority=authority(("first", "second")))
    assert all(r["score"] == 5 for r in result["ranked_candidates"])
    assert result["ranked_candidates"][0]["evaluation"]["provenance"] == {"id": "test-fixture"}
    assert result["aggregation"] == "SUM_OF_AUTHORITY_BOUND_CALLER_SCALED_LOSSES"


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
                            "basis": "experimental_design_proxy"}, budget=8,
        evaluator_authority={
            **authority(("distance",)),
            "applicable_materials": ["a", "b"],
        })
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
    assert result["ranked_candidates"] == []
    assert result["diagnostic_frontier"]
    assert result["best_observed_candidate"] is None
    assert result["experimental_recommendation"] is None


def test_basis_string_alone_is_unordered_diagnostic_no_change():
    result = run(evaluator_authority=None, budget=8)

    assert result["status"] == "DIAGNOSTIC_ONLY_NO_CHANGE"
    assert result["ranked_candidates"] == []
    assert result["best_observed_candidate"] is None
    assert result["experimental_recommendation"] is None
    assert result["formula_action"] == "NO_CHANGE"
    assert result["diagnostic_frontier"]
    assert result["diagnostic_frontier_ordering"] == "UNORDERED_PARETO_SET"
    assert result["benchmark_equal_budget"] is True
    assert result["evaluation_counts"] == {
        "baseline": 1, "optimizer": 8, "random": 8, "total": 17}
    assert result["selection_authority"] == (
        "WITHHELD_MISSING_OR_INVALID_EVALUATOR_AUTHORITY")


def test_measured_intensity_authority_cannot_promote_hedonics_or_release():
    result = run(
        budget=8,
        evaluator_authority=authority(endpoint="measured_intensity_comparison"),
    )

    assert result["selection_authority"] == "MEASURED_INTENSITY_COMPARISON_ONLY"
    assert result["claim_scope"] == "FINITE_BUDGET_MEASURED_INTENSITY_COMPARISON_ONLY"
    assert result["formula_action"] == "COMPARE_INTENSITY_ONLY"
    assert result["experimental_recommendation"]["authorized_use"] == (
        "INTENSITY_COMPARISON_ONLY")
    assert result["experimental_recommendation"]["compounding_authorized"] is False
    assert result["predicted_liking"] is None
    assert result["pleasantness_authorized"] is False
    assert result["liking_authorized"] is False
    assert result["compounding_authorized"] is False
    assert result["safety_authorized"] is False
    assert result["release_authorized"] is False


def test_intensity_authority_missing_explicit_liking_ceiling_is_withheld():
    incomplete = authority(endpoint="measured_intensity_comparison")
    incomplete.pop("liking_authorized")
    result = run(budget=4, evaluator_authority=incomplete)

    assert result["formula_action"] == "NO_CHANGE"
    assert result["experimental_recommendation"] is None
    assert "MEASURED_INTENSITY_LIKING_AUTHORIZED_MUST_BE_FALSE" in (
        result["evaluator_authority_reasons"])


def test_checkpoint2_endpoint_matrix_replaces_endpoint_name_substring_inference():
    result = gate_aware.optimize_checkpoint2_design(
        {"a": 5.0, "b": 5.0},
        evaluate=checkpoint2_evaluator(),
        bounds={"a": (0.0, 10.0), "b": (0.0, 10.0)},
        endpoint_id="lovely_intensity_words",
        scenario="fixture-gas-mixture",
        evaluator_authority=checkpoint2_authority(
            endpoint_id="lovely_intensity_words"
        ),
        budget_per_arm=1,
        seeds=(17,),
    )

    assert result["evaluator_authority_admitted"] is False
    assert "ENDPOINT_NOT_IN_AUTHORITY_MATRIX" in result["evaluator_authority_reasons"]
    assert result["ranked_candidates"] == []
    assert result["formula_action"] == "NO_CHANGE"


def test_checkpoint2_endpoint_authorities_are_independent():
    invalid = checkpoint2_authority(
        endpoint_authority={
            "character": False,
            "intensity": True,
            "pleasantness": True,
            "population_liking": False,
            "personal_liking": False,
        }
    )
    result = gate_aware.optimize_checkpoint2_design(
        {"a": 5.0, "b": 5.0},
        evaluate=checkpoint2_evaluator(),
        bounds={"a": (0.0, 10.0), "b": (0.0, 10.0)},
        endpoint_id="measured_intensity_comparison",
        scenario="fixture-gas-mixture",
        evaluator_authority=invalid,
        budget_per_arm=1,
        seeds=(17,),
    )
    assert "ENDPOINT_AUTHORITY_INVALID:pleasantness" in result[
        "evaluator_authority_reasons"
    ]
    assert result["predicted_liking"] is None


@pytest.mark.parametrize(
    "feature",
    [
        "OAV",
        "OAV_DERIVED_STEVENS_INTENSITY",
        "HAND_ASSIGNED_VALENCE",
        "SEMANTIC_DISTANCE",
        "DESCRIPTOR_DISTANCE",
        "CONFIDENCE_SCORE",
        "RELEASE_SCORE",
        "MATERIAL_COUNT",
    ],
)
def test_checkpoint2_prohibited_features_never_enter_selection(feature):
    result = gate_aware.optimize_checkpoint2_design(
        {"a": 5.0, "b": 5.0},
        evaluate=checkpoint2_evaluator(lineage=(feature,)),
        bounds={"a": (0.0, 10.0), "b": (0.0, 10.0)},
        endpoint_id="measured_intensity_comparison",
        scenario="fixture-gas-mixture",
        evaluator_authority=checkpoint2_authority(feature_lineage=(feature,)),
        budget_per_arm=1,
        seeds=(17,),
    )
    assert result["evaluator_authority_admitted"] is False
    assert f"PROHIBITED_SELECTION_FEATURE:{feature}" in result[
        "evaluator_authority_reasons"
    ]
    assert result["ranked_candidates"] == []


def test_checkpoint2_overlapping_intervals_emit_required_unordered_no_change():
    result = gate_aware.optimize_checkpoint2_design(
        {"a": 5.0, "b": 5.0},
        evaluate=checkpoint2_evaluator(overlap=True),
        bounds={"a": (0.0, 10.0), "b": (0.0, 10.0)},
        endpoint_id="measured_intensity_comparison",
        scenario="fixture-gas-mixture",
        evaluator_authority=checkpoint2_authority(),
        budget_per_arm=1,
        seeds=(17,),
    )
    assert result["selection_status"] == "WITHHELD_NONDISCRIMINATING_EVIDENCE"
    assert result["ranked_candidates"] == []
    assert result["best_observed_candidate"] is None
    assert result["experimental_recommendation"] is None
    assert result["shortlist_ordering"] == "UNORDERED_DIVERSE_SET"
    assert result["formula_action"] == "NO_CHANGE"
    assert result["evaluation_counts"] == {
        "baseline": 1,
        "adaptive": 1,
        "random": 1,
        "simple_local": 1,
        "total": 4,
    }
    assert result["benchmark_equal_budget"] is True
    for flag in (
        "evidence_admission_authorized",
        "physical_experiment_authorized",
        "compounding_authorized",
        "purchase_authorized",
        "inventory_mutation_authorized",
        "safety_authorized",
        "release_authorized",
        "formula_optimization_authority",
        "beauty_authorized",
    ):
        assert result[flag] is False


def test_lavender_ambrox_shortlist_holds_without_common_exact_basis():
    result = gate_aware.lavender_ambrox_shortlist(
        lavender_stock_id="lavender-block-70-30",
        ambrox_stock_id="ambrox-super-unbound",
        constant_total_basis="",
        constant_total_decimal=None,
    )
    assert result["selection_status"] == "HOLD_CONSTANT_TOTAL_BASIS_UNRESOLVED"
    assert result["candidates"] == []
    assert result["formula_action"] == "NO_CHANGE"
    assert result["formula_modified"] is False
    assert result["inventory_modified"] is False


def test_basis_safe_shortlist_is_diverse_unranked_and_nonpreferential():
    result = gate_aware.lavender_ambrox_shortlist(
        lavender_stock_id="lavender-block-70-30",
        ambrox_stock_id="ambrox-stock-exact",
        constant_total_basis="active_mass_g",
        constant_total_decimal="1.000000",
        candidate_shares=(0.0, 0.25, 0.5, 0.75, 1.0),
        requested_size=5,
    )
    assert result["selection_status"] == "ADMITTED_UNRANKED_DESIGN_SHORTLIST"
    assert result["ranked_candidates"] == []
    assert len(result["candidates"]) == 5
    shares = sorted(row["lavender_share"] for row in result["candidates"])
    assert min(right - left for left, right in zip(shares, shares[1:])) >= 0.125
    assert all(row["preference_order"] is None for row in result["candidates"])
