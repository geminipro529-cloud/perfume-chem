from __future__ import annotations

from dataclasses import asdict

import scripts.verify_formula_workflow as verification_workflow
from engine.formula_recommendations import (
    Recommendation,
    generate_intervention_recommendations,
    generate_recommendations,
)
from engine.optimizer.models import FormulaVector
from engine.optimizer.scoring import FormulaScorer


def _recommendation() -> Recommendation:
    return Recommendation(
        target_axis="texture",
        baseline_score=40.0,
        action="ADD",
        material="Hedione",
        dose_pct=1.0,
        rationale="test recommendation",
        new_axis_score=41.0,
        delta=1.0,
        new_composite=41.0,
        composite_delta=1.0,
    )


def test_intervention_wrapper_forwards_supplied_scorer(monkeypatch):
    expected = [_recommendation()]
    supplied_scorer = object()
    observed = {}

    def fake_generate(*args, **kwargs):
        observed.update(kwargs)
        return expected

    monkeypatch.setattr(
        "engine.formula_recommendations.generate_recommendations",
        fake_generate,
    )

    result = generate_intervention_recommendations(
        FormulaVector(ingredients={"Hedione": 100.0}, dilutions={"Hedione": 1.0}),
        {"texture": 40.0},
        inventory=[],
        scorer=supplied_scorer,
        include_unvalidated_advisory=True,
    )

    assert result is expected
    assert observed["scorer"] is supplied_scorer
    assert observed["include_unvalidated_advisory"] is True


def test_default_intervention_recommendations_match_direct_generation():
    formula_vector = FormulaVector(
        ingredients={"Hedione": 60.0, "Iso E Super": 40.0},
        dilutions={"Hedione": 1.0, "Iso E Super": 1.0},
    )
    inventory = [
        {"name": "Vanillin", "dilution": 0.1, "category": "Gourmand", "catalog": None},
        {"name": "Coumarin", "dilution": 0.2, "category": "Gourmand", "catalog": None},
        {
            "name": "Benzyl Salicylate",
            "dilution": 1.0,
            "category": "Floral",
            "catalog": None,
        },
        {"name": "Ambrox Super", "dilution": 1.0, "category": "Base", "catalog": None},
    ]
    scores = FormulaScorer().score(formula_vector)

    direct = generate_recommendations(
        formula_vector,
        scores,
        inventory=inventory,
        top_n=5,
        scorer=FormulaScorer(),
        include_unvalidated_advisory=True,
    )
    wrapped = generate_intervention_recommendations(
        formula_vector,
        scores,
        inventory=inventory,
        top_n=5,
        scorer=FormulaScorer(),
        include_unvalidated_advisory=True,
    )

    assert [asdict(rec) for rec in wrapped] == [asdict(rec) for rec in direct]


def test_build_bundle_reuses_default_pre_mix_recommendations(monkeypatch):
    recommendation = _recommendation()
    initial_result = [recommendation]
    recommendation_calls = []
    section_inputs = []

    def fake_generate(*args, **kwargs):
        recommendation_calls.append(("default", kwargs))
        return initial_result

    def fake_intervention(*args, **kwargs):
        recommendation_calls.append((kwargs["mode"], kwargs))
        return []

    def fake_sections(*args):
        section_inputs.append(args)
        return {
            phase["key"]: {
                "title": phase["title"],
                "context": phase["context"],
                "observation_tags": phase["observation_tags"],
            }
            for phase in verification_workflow.INTERVENTION_PHASES
        }

    monkeypatch.setattr(verification_workflow, "generate_recommendations", fake_generate)
    monkeypatch.setattr(
        verification_workflow,
        "generate_intervention_recommendations",
        fake_intervention,
    )
    monkeypatch.setattr(verification_workflow, "_build_intervention_sections", fake_sections)

    formula = {
        "name": "Recommendation reuse fixture",
        "ingredients_pct": {"Hedione": 60.0, "Vanillin": 40.0},
        "dilutions": {"Hedione": 1.0, "Vanillin": 0.1},
        "ingredients_ul": {"Hedione": 600.0, "Vanillin": 400.0},
        "batch_volume_ml": 10.0,
    }

    bundle = verification_workflow.build_verification_bundle(
        formula,
        include_advisory_recommendations=True,
    )

    assert [mode for mode, _kwargs in recommendation_calls] == [
        "default",
        "between_mix",
        "post_mix",
    ]
    assert recommendation_calls[0][1]["scorer"] is recommendation_calls[1][1]["scorer"]
    assert recommendation_calls[1][1]["scorer"] is recommendation_calls[2][1]["scorer"]
    assert all(
        kwargs["include_unvalidated_advisory"] is True
        for _mode, kwargs in recommendation_calls
    )
    assert section_inputs[0][0] is initial_result
    assert section_inputs[0][1] is initial_result
    expected = asdict(recommendation)
    expected.update(
        {
            "authority_state": "UNVALIDATED_ADVISORY",
            "proposal_status": "UNVALIDATED_ADVISORY",
            "formula_optimization_authority": False,
            "compounding_action_authority": False,
            "requires_controlled_comparison": True,
            "selection_basis": "LEGACY_DIAGNOSTIC_TOTAL_NOT_ADMITTED",
        }
    )
    assert bundle["recommendations"] == [expected]
    assert bundle["ranking"]["status"] == "WITHHELD"
    assert bundle["ranking"]["value"] is None


def test_build_bundle_skips_optimizer_search_by_default(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("routine verification must not launch advisory search")

    monkeypatch.setattr(verification_workflow, "load_inventory", fail_if_called)
    monkeypatch.setattr(verification_workflow, "generate_recommendations", fail_if_called)
    monkeypatch.setattr(
        verification_workflow,
        "generate_intervention_recommendations",
        fail_if_called,
    )

    formula = {
        "name": "Fast verification fixture",
        "ingredients_pct": {"Hedione": 60.0, "Iso E Super": 40.0},
        "dilutions": {"Hedione": 1.0, "Iso E Super": 1.0},
        "ingredients_ul": {"Hedione": 600.0, "Iso E Super": 400.0},
        "compounding_rows": [],
        "compounding_row_blockers": [
            "EXPLICIT_BASKET_ASSIGNMENTS_NOT_DECLARED"
        ],
        "batch_volume_ml": 10.0,
    }

    bundle = verification_workflow.build_verification_bundle(formula)

    assert bundle["recommendations"] == []
    assert bundle["advisory_recommendation_status"] == "SKIPPED_NOT_REQUESTED"
    assert bundle["advisory_recommendations_requested"] is False
