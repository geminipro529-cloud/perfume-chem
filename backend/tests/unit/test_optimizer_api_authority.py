"""Optimizer API contract must match the engine and remain fail closed."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from engine.optimizer.models import FormulaVector, ObjectiveWeights
from pydantic import ValidationError

from app.api.v1.endpoints import optimizer as endpoint
from app.services.validation_pipeline import PipelineReport


def test_api_weight_schema_exactly_matches_engine_contract() -> None:
    api_fields = set(endpoint.WeightsInput.model_fields)
    engine_fields = set(ObjectiveWeights().as_dict())

    assert api_fields == engine_fields
    assert ObjectiveWeights(**endpoint.WeightsInput().model_dump()).as_dict() == (
        ObjectiveWeights().as_dict()
    )

    with pytest.raises(ValidationError):
        endpoint.WeightsInput(balance=1.0)


def test_optimize_endpoint_uses_single_fail_closed_result(monkeypatch) -> None:
    class FakeOptimizer:
        def __init__(self, **_kwargs) -> None:
            pass

        def score(self, _formula):
            raise AssertionError("endpoint must not score the unchanged formula twice")

        def optimize(self, formula):
            return SimpleNamespace(
                formula=FormulaVector(
                    ingredients=dict(formula.ingredients),
                    dilutions=dict(formula.dilutions),
                ),
                scores={"total": 12.3},
                total_score=12.3,
                reasoning=["NO_CHANGE"],
                suggestions=["NO_CHANGE"],
                ranking_status="WITHHELD",
                formula_optimization_authority=False,
                selection_basis="LEGACY_DIAGNOSTIC_TOTAL_NOT_ADMITTED",
            )

    monkeypatch.setattr(endpoint, "FormulaOptimizer", FakeOptimizer)
    monkeypatch.setattr(
        endpoint,
        "validate_formula",
        lambda _ingredients: PipelineReport(),
    )
    durable_calls = []

    async def fake_enqueue(session, report, ingredients, *, scope):
        durable_calls.append((session, dict(ingredients), scope))
        return report

    monkeypatch.setattr(
        endpoint,
        "enqueue_formula_analysis_compatibility",
        fake_enqueue,
    )
    fake_session = object()

    payload = asyncio.run(
        endpoint.optimize_formula(
            endpoint.OptimizeRequest(
                formula=endpoint.FormulaInput(ingredients={"Hedione": 100.0})
            ),
            session=fake_session,
        )
    )

    assert payload["optimized_formula"] == {"Hedione": 100.0}
    assert payload["improvement"] == 0.0
    assert payload["ranking_status"] == "WITHHELD"
    assert payload["formula_optimization_authority"] is False
    assert durable_calls == [
        (fake_session, {"Hedione": 100.0}, "optimizer.optimize")
    ]
