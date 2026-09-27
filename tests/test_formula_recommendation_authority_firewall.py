from __future__ import annotations

from dataclasses import asdict

import scripts.intervention_recommend as intervention_cli
from engine.formula_recommendations import (
    Recommendation,
    generate_intervention_recommendations,
    generate_recommendations,
)
from engine.optimizer.models import FormulaVector
from engine.pipeline.interventions import build_intervention_contract


def _formula_vector() -> FormulaVector:
    return FormulaVector(
        ingredients={"Hedione": 100.0},
        dilutions={"Hedione": 1.0},
    )


def _recommendation() -> Recommendation:
    return Recommendation(
        target_axis="texture",
        baseline_score=40.0,
        action="ADD",
        material="Hedione",
        dose_pct=1.0,
        rationale="legacy diagnostic hypothesis",
        new_axis_score=41.0,
        delta=1.0,
        new_composite=41.0,
        composite_delta=1.0,
    )


def test_public_recommendation_generation_fails_closed_before_inventory(monkeypatch):
    def unexpected_inventory_load():
        raise AssertionError("default recommendation call must not load inventory")

    monkeypatch.setattr(
        "engine.formula_recommendations.load_inventory",
        unexpected_inventory_load,
    )

    assert generate_recommendations(_formula_vector(), {"texture": 40.0}) == []
    assert generate_recommendations(
        _formula_vector(),
        {"texture": 40.0},
        include_unvalidated_advisory=1,
    ) == []


def test_intervention_wrapper_requires_literal_advisory_opt_in(monkeypatch):
    calls: list[dict[str, object]] = []
    expected = [_recommendation()]

    def fake_generate(*_args, **kwargs):
        calls.append(kwargs)
        return expected

    monkeypatch.setattr(
        "engine.formula_recommendations.generate_recommendations",
        fake_generate,
    )

    assert generate_intervention_recommendations(
        _formula_vector(),
        {"texture": 40.0},
    ) == []
    assert calls == []

    result = generate_intervention_recommendations(
        _formula_vector(),
        {"texture": 40.0},
        include_unvalidated_advisory=True,
    )
    assert result is expected
    assert calls[0]["include_unvalidated_advisory"] is True


def test_recommendation_carries_non_authoritative_selection_contract():
    payload = asdict(_recommendation())

    assert payload["authority_state"] == "UNVALIDATED_ADVISORY"
    assert payload["proposal_status"] == "UNVALIDATED_ADVISORY"
    assert payload["formula_optimization_authority"] is False
    assert payload["compounding_action_authority"] is False
    assert payload["requires_controlled_comparison"] is True
    assert payload["selection_basis"] == "LEGACY_DIAGNOSTIC_TOTAL_NOT_ADMITTED"


def test_cli_serialization_forces_authority_ceiling_and_labels_ul_hypothesis():
    serialized = intervention_cli._recommendation_to_dict(
        {
            "material": "Hedione",
            "dose_pct": 1.0,
            "authority_state": "AUTHORIZED",
            "formula_optimization_authority": True,
            "compounding_action_authority": True,
            "requires_controlled_comparison": False,
            "selection_basis": "ADMITTED",
        },
        batch_ml=30.0,
    )

    assert serialized["authority_state"] == "UNVALIDATED_ADVISORY"
    assert serialized["formula_optimization_authority"] is False
    assert serialized["compounding_action_authority"] is False
    assert serialized["requires_controlled_comparison"] is True
    assert serialized["selection_basis"] == "LEGACY_DIAGNOSTIC_TOTAL_NOT_ADMITTED"
    assert serialized["approx_add_ul"] == 300.0
    assert serialized["approx_add_ul_is_hypothesis"] is True
    assert serialized["approx_add_ul_label"] == (
        "HYPOTHESIS_ONLY_NOT_A_COMPOUNDING_INSTRUCTION"
    )

    markdown = "\n".join(
        intervention_cli._format_recommendation_block(serialized, batch_ml=30.0, index=1)
    )
    assert "Dose hypothesis only" in markdown
    assert "not a compounding instruction" in markdown


def test_report_ranking_cannot_promote_legacy_hypothesis_to_swap(monkeypatch):
    monkeypatch.setattr(
        "engine.pipeline.interventions.generate_intervention_recommendations",
        lambda *_args, **_kwargs: [_recommendation()],
    )
    formula = {
        "name": "Authority fixture",
        "ingredients_ul": {"Hedione": 1000.0},
        "dilutions": {"Hedione": 1.0},
    }
    report = {
        "scores": {"texture": 40.0},
        "ranking": {
            "status": "ADMITTED",
            "formula_optimization_authority": True,
        },
    }

    contract = build_intervention_contract(
        formula,
        report,
        include_advisory_recommendations=True,
    )

    assert contract["advisory_repairs"][0]["authority_state"] == "UNVALIDATED_ADVISORY"
    assert contract["advisory_repairs"][0]["formula_optimization_authority"] is False
    assert contract["advisory_repairs"][0]["compounding_action_authority"] is False
    assert contract["swap_candidates"] == []
