from threading import Barrier

import pytest

from engine.optimizer import gate_aware


def run(**overrides):
    args = dict(
        baseline={"gin": 6., "wood": 4.},
        evaluate=lambda f, s: {"body": abs(f["wood"] - 6)},
        evaluator_version="v1", criteria=["body"], scenarios=["nominal"],
        lanes={"body": [("gin", "wood")], "reverse": [("wood", "gin")]},
        step_sizes=[1.], bounds={"gin": (4., 8.), "wood": (2., 6.)},
        max_rounds=3,
    )
    args.update(overrides)
    return gate_aware.optimize_concurrent_hedonic_design(**args)


def test_parallel_search_reaches_structural_target_without_liking_data():
    result = run()
    assert result["selected"] == {"gin": 4., "wood": 6.}
    assert result["status"] == "COMPUTATIONAL_TARGET_MET"
    assert result["predicted_liking"] is None
    assert result["requires_premix_trial"] is False


def test_candidate_lanes_actually_overlap_and_parent_selects_one():
    barrier = Barrier(2)

    def evaluate(formula, scenario):
        if formula["wood"] in (3., 5.):
            barrier.wait(timeout=5)
        return {"body": abs(formula["wood"] - 6)}

    result = run(evaluate=evaluate, max_rounds=1)
    assert result["selected"] == {"gin": 5., "wood": 5.}


def test_failed_revision_keeps_old_evaluator_and_records_rejection():
    result = run(revisions=[("bad", lambda f, s: {"body": 0.})],
                 admission_cases=[({"gin": 6., "wood": 4.}, "nominal", {"body": (1., 3.)})])
    assert result["evaluator_version"] == "v1"
    assert result["revision_history"][0]["accepted"] is False


def test_admitted_revision_rescores_baseline_and_shortlist():
    result = run(revisions=[("v2", lambda f, s: {"body": abs(f["wood"] - 5)})],
                 admission_cases=[({"gin": 6., "wood": 4.}, "nominal", {"body": (1., 1.)})])
    assert result["evaluator_version"] == "v2"
    assert result["selected"] == {"gin": 5., "wood": 5.}
    assert result["revision_history"][0]["rescored_candidates"] >= 2


def test_revision_can_restore_baseline_when_new_evaluator_reverses_ranking():
    result = run(revisions=[
        ("v1b", lambda f, s: {"body": abs(f["wood"] - 6)}),
        ("v2", lambda f, s: {"body": abs(f["wood"] - 4)}),
    ], admission_cases=[({"gin": 6., "wood": 4.}, "nominal", {"body": (0., 2.)})],
        max_rounds=2)
    assert result["selected"] == {"gin": 6., "wood": 4.}


def test_missing_structural_data_is_not_success():
    result = run(evaluate=lambda f, s: {})
    assert result["status"] == "EVALUATION_UNAVAILABLE"
    assert result["selected"] == {"gin": 6., "wood": 4.}


def test_broken_initial_evaluator_can_be_replaced_before_search_resumes():
    result = run(evaluate=lambda f, s: {},
                 revisions=[("repaired", lambda f, s: {"body": abs(f["wood"] - 6)})],
                 admission_cases=[({"gin": 6., "wood": 4.}, "nominal", {"body": (2., 2.)})])
    assert result["status"] == "COMPUTATIONAL_TARGET_MET"
    assert result["evaluator_version"] == "repaired"
    assert result["error"] is None


def test_hard_identity_constraint_cannot_be_bought_by_body():
    result = run(feasible=lambda f: f["gin"] >= 6.)
    assert result["status"] == "PLATEAU"
    assert result["selected"] == {"gin": 6., "wood": 4.}


def test_revisions_require_fixed_admission_cases():
    with pytest.raises(ValueError):
        run(revisions=[("v2", lambda f, s: {"body": 0.})])


def test_parent_compares_each_lane_to_same_incumbent_not_previous_winner():
    def evaluate(f, s):
        return {4.: {"body": 3., "texture": 3.},
                5.: {"body": 1., "texture": 2.},
                3.: {"body": 2., "texture": 0.}}[f["wood"]]
    result = run(evaluate=evaluate, criteria=["body", "texture"], max_rounds=1)
    assert result["selected"] == {"gin": 7., "wood": 3.}


def test_structural_adapter_does_not_impute_liking_or_accept_broken_identity():
    from engine.hedonic_model import structural_design_losses

    report = {"target_identity": {"status": "PASS_DESIGN_CONSTRAINTS", "violations": []},
              "predicted_liking": {"status": "EVIDENCE_UNAVAILABLE", "score": None}}
    assert structural_design_losses(report, {"body": 2.}) == {"body": 2.}
    report["target_identity"]["violations"] = [{"kind": "required_anchor_missing"}]
    with pytest.raises(ValueError):
        structural_design_losses(report, {"body": 0.})


@pytest.mark.parametrize("losses", [{}, {"body": float("nan")}, {"body": -1.}])
def test_structural_adapter_rejects_missing_or_invalid_objectives(losses):
    from engine.hedonic_model import structural_design_losses
    report = {"target_identity": {"status": "PASS_DESIGN_CONSTRAINTS", "violations": []}}
    with pytest.raises(ValueError):
        structural_design_losses(report, losses)
