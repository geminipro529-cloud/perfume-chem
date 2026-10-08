"""Behavior tests for uncertainty-aware, computer-only candidate search."""
import json

import pytest

from engine.optimizer import gate_aware
from tests.historical_snapshots import bind_gin_design_test_plan


def test_plan_path(root, tmp_path):
    """Bind an isolated algorithm fixture, not the superseded canonical plan."""
    plan = bind_gin_design_test_plan(json.loads(
        (root / "data/design_briefs/gin_vetiver_edp_evidence_v1.json").read_bytes()
    ))
    path = tmp_path / "gin-stock-contract-fixture.json"
    path.write_text(json.dumps(plan), encoding="utf-8")
    return path


test_plan_path.__test__ = False


def run(evaluate, **overrides):
    function = getattr(gate_aware, "optimize_evidence_portfolio", None)
    assert callable(function), "Evidence portfolio search is not implemented"
    args = dict(
        baseline={"a": 6., "b": 4.}, evaluate=evaluate,
        evaluator_version="fixture-v1", criteria=["body"], scenarios=["nominal"],
        lanes={"forward": [("a", "b")], "reverse": [("b", "a")]},
        bounds={"a": (3., 7.), "b": (3., 7.)}, step_sizes=[1.],
        max_rounds=4, max_candidates=30, max_workers=2,
    )
    args.update(overrides)
    return function(**args)


def row(intervals, scenario="nominal"):
    return dict(loss_intervals=intervals, sources=["test://hand-derived"],
                context=scenario, basis="design_proxy")


def test_zero_baseline_still_enumerates_and_does_not_claim_liking_success():
    result = run(lambda f, s: row({"body": [0., 0.]}))
    assert len(result["archive"]) == 3
    assert result["status"] == "UNRESOLVED_COMPARISONS"
    assert result["selected"] == {"a": 6., "b": 4.}
    assert result["predicted_liking"] is None


def test_robust_improvements_recurse_and_preserve_total():
    result = run(lambda f, s: row({"body": [abs(f["b"]-7)] * 2}))
    assert result["selected"] == {"a": 3., "b": 7.}
    assert len([r for r in result["history"] if r["advanced"]]) == 3
    assert result["status"] == "LOCAL_PARETO_PLATEAU"
    assert all(sum(r["formula"].values()) == 10 for r in result["archive"])


def test_overlapping_uncertainty_is_not_a_robust_improvement():
    result = run(lambda f, s: row({"body": [3., 5.] if f["b"] == 4 else [2., 4.]}))
    assert result["selected"]["b"] == 4
    assert result["status"] == "UNRESOLVED_COMPARISONS"
    assert len(result["frontier"]) == 3


def test_tradeoffs_survive_without_summed_loss_winner():
    values = {4: {"body": [3, 3], "texture": [3, 3]},
              5: {"body": [1, 1], "texture": [2, 2]},
              3: {"body": [2, 2], "texture": [0, 0]}}
    result = run(lambda f, s: row(values[f["b"]]),
                 criteria=["body", "texture"], max_rounds=1)
    assert {r["formula"]["b"] for r in result["frontier"]} == {3, 5}
    assert result["selection_authority"] == "DETERMINISTIC_SEARCH_REPRESENTATIVE"


def test_missing_data_retains_hypotheses_without_inventing_zero_losses():
    result = run(lambda f, s: dict(loss_intervals=None, sources=["test://roles"],
                                  context=s, basis="qualitative_hypothesis",
                                  hypothesis="woody fullness versus transparency"))
    assert result["status"] == "EVIDENCE_BOUNDARY"
    assert len(result["archive"]) == 3
    assert result["frontier"] == []
    assert result["requires_premix_trial"] is False
    assert all(r["evaluations"]["nominal"]["loss_intervals"] is None
               for r in result["archive"])


@pytest.mark.parametrize("bad", [
    {"body": [2, 1]}, {"body": [float("nan"), 1]}, {}, {"body": [0, 1], "extra": [0, 0]},
])
def test_invalid_or_partial_intervals_are_unavailable_not_pass(bad):
    result = run(lambda f, s: row(bad))
    assert result["status"] == "EVIDENCE_BOUNDARY"
    assert all(r["error"] for r in result["archive"])


def test_hard_feasibility_rejects_before_evaluation():
    def evaluate(f, s):
        assert f["a"] >= 6
        return row({"body": [abs(f["b"]-7)] * 2})
    result = run(evaluate, feasible=lambda f: f["a"] >= 6)
    assert result["selected"]["a"] == 6
    assert result["rejected_counts"]["composition_constraint"] > 0


def test_budget_is_exact_and_does_not_claim_exhaustive_neighborhood():
    result = run(lambda f, s: row({"body": [1, 1]}), max_candidates=2)
    assert len(result["archive"]) == 2
    assert result["status"] == "BUDGET_EXHAUSTED"
    assert result["neighborhood_exhausted"] is False


def test_scenario_regression_cannot_be_hidden_by_other_scenario_gain():
    def evaluate(f, s):
        loss = abs(f["b"] - (7 if s == "nominal" else 4))
        return row({"body": [loss, loss]}, s)
    result = run(evaluate, scenarios=["nominal", "alternative"])
    assert result["selected"]["b"] == 4
    assert result["status"] == "UNRESOLVED_COMPARISONS"


def test_role_evidence_distinguishes_direction_but_never_invents_dose_response():
    from engine import hedonic_model
    function = getattr(hedonic_model, "evaluate_design_roles", None)
    assert callable(function), "Source-linked design-role evaluator missing"
    roles = {"a": {"roles": ["transparent support"], "sources": ["test://a"]},
             "b": {"roles": ["woody fullness"], "sources": ["test://b"]}}
    baseline = {"a": 6., "b": 4.}
    kwargs = dict(baseline=baseline, profiles=roles, context="nominal")
    forward = function({"a": 5., "b": 5.}, **kwargs)
    reverse = function({"a": 7., "b": 3.}, **kwargs)
    larger = function({"a": 4., "b": 6.}, **kwargs)
    assert forward["increased_material_roles"] == {"b": ["woody fullness"]}
    assert reverse["increased_material_roles"] == {"a": ["transparent support"]}
    assert larger["increased_material_roles"] == forward["increased_material_roles"]
    assert forward["loss_intervals"] is None
    assert forward["predicted_liking"] is None


def test_role_evidence_reports_missing_material_instead_of_silently_dropping_it():
    from engine import hedonic_model
    function = getattr(hedonic_model, "evaluate_design_roles", None)
    assert callable(function), "Source-linked design-role evaluator missing"
    result = function({"a": 5., "b": 5.}, baseline={"a": 6., "b": 4.},
                      profiles={"a": {"roles": ["air"], "sources": ["test://a"]}},
                      context="nominal")
    assert result["missing_profiles"] == ["b"]
    assert result["dose_ranking_authorized"] is False


def test_equal_uncertainty_ranges_do_not_prove_equal_latent_values():
    result = run(lambda f, s: row({"body": [abs(f["b"]-7)] * 2,
                                   "texture": [0, 10]}), criteria=["body", "texture"])
    assert result["selected"]["b"] == 4


def test_gin_stock_contract_fixture_runs_via_cli_without_formula_change(tmp_path):
    import hashlib
    from pathlib import Path

    from scripts import verify_formula_workflow as cli
    function = getattr(cli, "run_design_portfolio", None)
    assert callable(function), "Existing CLI has no design portfolio adapter"
    root = Path(__file__).resolve().parents[1]
    formula = root / "formulas/records/Gin_Vetiver_Cypress_Air_30mL_v4_EDP.json"
    before = hashlib.sha256(formula.read_bytes()).hexdigest()
    result = function(formula, test_plan_path(root, tmp_path))
    assert result["status"] == "EVIDENCE_BOUNDARY"
    assert result["evaluated_candidates"] == 72
    assert result["selected"] == result["baseline"]
    assert result["stock_checks_passed"] == 18
    assert result["source_hashes"]["engine/optimizer/gate_aware.py"] == hashlib.sha256(
        (root / "engine/optimizer/gate_aware.py").read_bytes()).hexdigest()
    assert hashlib.sha256(formula.read_bytes()).hexdigest() == before


def test_complete_role_coverage_gap_survives_in_archive():
    from engine.hedonic_model import evaluate_design_roles
    result = run(lambda f, s: evaluate_design_roles(
        f, baseline={"a": 6., "b": 4.}, profiles={}, context=s))
    assert result["archive"][0]["evaluations"]["nominal"]["missing_profiles"] == ["a", "b"]


@pytest.mark.parametrize("change", ["formula_sha256", "inventory_sha256"])
def test_cli_rejects_stale_formula_or_inventory_binding(tmp_path, change):
    import json
    from pathlib import Path

    from scripts.verify_formula_workflow import run_design_portfolio
    root = Path(__file__).resolve().parents[1]
    plan = json.loads(test_plan_path(root, tmp_path).read_text())
    plan[change] = "0" * 64
    path = tmp_path / "stale.json"
    path.write_text(json.dumps(plan))
    with pytest.raises(ValueError, match="source drift"):
        run_design_portfolio(root / "formulas/records/Gin_Vetiver_Cypress_Air_30mL_v4_EDP.json", path)


def test_cli_rejects_changing_diluted_stock_without_carrier_mass_model(tmp_path):
    import json
    from pathlib import Path

    from scripts.verify_formula_workflow import run_design_portfolio
    root = Path(__file__).resolve().parents[1]
    plan = json.loads(test_plan_path(root, tmp_path).read_text())
    plan["bounds"]["Ambrettolide"] = [200, 300]
    path = tmp_path / "carrier.json"
    path.write_text(json.dumps(plan))
    with pytest.raises(ValueError, match="carrier/active-dose"):
        run_design_portfolio(root / "formulas/records/Gin_Vetiver_Cypress_Air_30mL_v4_EDP.json", path)


def reviewed_evaluators(disposition="QUALITATIVE_ONLY"):
    return {"expected_proposals": ["roles"], "proposals": [{
        "id": "roles", "disposition": disposition,
        "evaluator_version": "fixture-v1", "reason": "No mixture response labels",
        "evidence": ["fixture-evidence"],
    }]}


def finalize(result, review=None):
    function = getattr(gate_aware, "finalize_design_portfolio", None)
    assert callable(function), "No final decision contract exists"
    return function(result, review=review or reviewed_evaluators())


def qualitative_result():
    return run(lambda f, s: dict(loss_intervals=None, sources=["test://roles"],
                                 context=s, basis="qualitative_hypothesis",
                                 missing_profiles=[]))


def test_final_no_change_closes_bounded_run_without_claiming_optimization_success():
    result = qualitative_result()
    decision = finalize(result)
    assert decision["disposition"] == "NO_SUPPORTED_CHANGE"
    assert decision["bounded_run_complete"] is True
    assert decision["hedonic_optimization_achieved"] is False
    assert decision["selected_formula"] == {"a": 6., "b": 4.}
    assert result["status"] == "EVIDENCE_BOUNDARY"
    assert decision["requires_premix_trial"] is False


def test_final_budget_exhaustion_is_not_completion():
    result = run(lambda f, s: row({"body": [1, 1]}), max_candidates=2)
    decision = finalize(result)
    assert decision["disposition"] == "INCOMPLETE_BUDGET"
    assert decision["bounded_run_complete"] is False


def test_final_evaluator_exception_cannot_be_closed_as_no_change():
    decision = finalize(run(lambda f, s: row({"body": [2, 1]})))
    assert decision["disposition"] == "EVALUATION_ERROR"
    assert decision["bounded_run_complete"] is False


def test_final_missing_profiles_are_unfinished_work_not_excluded_evidence():
    result = qualitative_result()
    result["archive"][0]["evaluations"]["nominal"]["missing_profiles"] = ["a"]
    assert finalize(result)["disposition"] == "EVALUATION_ERROR"


def test_final_pending_evaluator_review_remains_incomplete():
    decision = finalize(qualitative_result(), reviewed_evaluators("PENDING"))
    assert decision["disposition"] == "INCOMPLETE_REVIEW"
    assert decision["bounded_run_complete"] is False


def test_final_cannot_accept_numerical_changes_with_only_role_authority():
    result = run(lambda f, s: row({"body": [abs(f["b"]-7)] * 2}))
    assert finalize(result)["disposition"] == "INCOMPLETE_REVIEW"
    decision = finalize(result, reviewed_evaluators("ADMITTED_NUMERIC"))
    assert decision["disposition"] == "SUPPORTED_COMPUTATIONAL_CHANGE"
    assert decision["selected_formula"] == {"a": 3., "b": 7.}
    assert decision["hedonic_optimization_achieved"] is False


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "unexplained", "unknown"])
def test_final_review_cannot_omit_proposals_or_invent_dispositions(mutation):
    review = reviewed_evaluators()
    if mutation == "missing":
        review["expected_proposals"].append("other")
    elif mutation == "duplicate":
        review["proposals"].append(dict(review["proposals"][0]))
    elif mutation == "unexplained":
        review["proposals"][0]["reason"] = ""
    else:
        review["proposals"][0]["disposition"] = "TRUST_ME"
    with pytest.raises(ValueError):
        finalize(qualitative_result(), review)


@pytest.mark.parametrize("drift", [None, "evidence", "plan"])
def test_final_cli_binds_review_and_evidence_before_closing(tmp_path, drift):
    import hashlib
    import json
    from pathlib import Path

    from scripts.verify_formula_workflow import run_design_portfolio
    root = Path(__file__).resolve().parents[1]
    plan = test_plan_path(root, tmp_path)
    formula = root / "formulas/records/Gin_Vetiver_Cypress_Air_30mL_v4_EDP.json"
    def digest(p):
        return hashlib.sha256(p.read_bytes()).hexdigest()
    review = reviewed_evaluators()
    review.update(schema="design_evaluator_review_v1", formula_sha256=digest(formula),
                  plan_sha256=digest(plan), evidence_files={"fixture-evidence": {
                      "path": "docs/COMPUTER_ONLY_HEDONIC_LOOP.md",
                      "sha256": digest(root / "docs/COMPUTER_ONLY_HEDONIC_LOOP.md")}})
    review["proposals"][0]["evaluator_version"] = "gin-vetiver-material-role-hypotheses-v1"
    if drift == "evidence":
        review["evidence_files"]["fixture-evidence"]["sha256"] = "0" * 64
    elif drift == "plan":
        review["plan_sha256"] = "0" * 64
    path = tmp_path / "review.json"
    path.write_text(json.dumps(review))
    if drift:
        with pytest.raises(ValueError, match="review.*drift"):
            run_design_portfolio(formula, plan, review_path=path)
    else:
        result = run_design_portfolio(formula, plan, review_path=path)
        assert result["final_decision"]["disposition"] == "NO_SUPPORTED_CHANGE"
        assert result["review_sha256"] == digest(path)
        assert result["formula_modified"] is False


def test_ledger_accounts_for_bounds_duplicates_and_budget_without_losing_origins():
    result = run(lambda f, s: row({"body": [1, 1]}),
                 lanes={"one": [("a", "b")], "two": [("a", "b"), ("b", "a")]},
                 step_sizes=[1., 4.], max_candidates=2)
    ledger = result.get("proposal_ledger", [])
    assert len(ledger) == 6
    assert [r["disposition"] for r in ledger] == [
        "EVALUATED", "STOCK_BOUNDS", "DUPLICATE_PENDING", "STOCK_BOUNDS",
        "BUDGET_LIMIT", "STOCK_BOUNDS"]
    assert ledger[0]["archive_index"] == ledger[2]["archive_index"] == 1
    assert ledger[2]["origin"]["lane"] == "two"
    assert ledger[4]["candidate"] == {"a": 7., "b": 3.}
    assert result["pending_proposals"] == 0


def test_fixture_plan_ledger_explains_all_three_clearwood_steps(tmp_path):
    from pathlib import Path

    from scripts.verify_formula_workflow import run_design_portfolio
    root = Path(__file__).resolve().parents[1]
    result = run_design_portfolio(
        root / "formulas/records/Gin_Vetiver_Cypress_Air_30mL_v4_EDP.json",
        test_plan_path(root, tmp_path))
    assert len(result.get("proposal_ledger", [])) == 156
    rows = [r for r in result["proposal_ledger"]
            if r["origin"]["donor"] == "Hedione" and r["origin"]["receiver"] == "Clearwood"]
    assert [(r["origin"]["amount"], r["disposition"]) for r in rows] == [
        (50., "STOCK_BOUNDS"), (25., "EVALUATED"), (10., "EVALUATED")]


@pytest.mark.parametrize("mutation", ["pending", "queued", "ids", "counts"])
def test_final_rejects_unfinished_or_inconsistent_proposal_ledger(mutation):
    result = qualitative_result()
    if mutation == "pending":
        result["pending_proposals"] = 1
    elif mutation == "queued":
        result["proposal_ledger"][0]["disposition"] = "QUEUED"
    elif mutation == "ids":
        result["proposal_ledger"][0]["proposal_id"] = 99
    else:
        result["proposal_counts"] = {}
    decision = finalize(result)
    assert decision["disposition"] == "INCOMPLETE_SEARCH"
    assert decision["bounded_run_complete"] is False


def test_final_ledger_budget_event_overrides_nonbudget_summary():
    from collections import Counter
    result = qualitative_result()
    result["proposal_ledger"][0]["disposition"] = "BUDGET_LIMIT"
    result["proposal_counts"] = dict(Counter(
        e["disposition"] for e in result["proposal_ledger"]))
    decision = finalize(result)
    assert decision["disposition"] == "INCOMPLETE_BUDGET"
    assert decision["bounded_run_complete"] is False


@pytest.mark.parametrize("field", ["source_workbook_sha256", "snapshot_sha256", "overlay_sha256"])
def test_cli_rejects_materialized_authority_drift_with_unchanged_inventory_text(monkeypatch, tmp_path, field):
    from dataclasses import replace
    from pathlib import Path

    from engine import inventory_parser
    from scripts.verify_formula_workflow import run_design_portfolio
    root = Path(__file__).resolve().parents[1]
    plan_path = test_plan_path(root, tmp_path)
    materialized = inventory_parser.materialize_current_inventory()
    monkeypatch.setattr(inventory_parser, "materialize_current_inventory",
                        lambda *args, **kwargs: replace(materialized, **{field: "0" * 64}))
    with pytest.raises(ValueError, match="source drift"):
        run_design_portfolio(
            root / "formulas/records/Gin_Vetiver_Cypress_Air_30mL_v4_EDP.json",
            plan_path)
