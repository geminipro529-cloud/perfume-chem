"""Regression tests for the DeepSeek provider adapter."""

from unittest.mock import AsyncMock

import pytest

from app.services.ai.deepseek_service import DeepSeekService


class StubContextBuilder:
    def build_context(self, query, ingredients=None, include_validation=True):
        return {
            "dosage_guidelines": "dose context",
            "inventory": "inventory context",
            "relevant_knowledge": "knowledge context",
            "similar_formulations": "formula context",
            "validation_context": "validation context",
        }


class StubIssue:
    def to_dict(self):
        return {"severity": "warning", "message": "check dilution"}


class StubValidator:
    def __init__(self):
        self.received = None

    def validate_formula(self, ingredients):
        self.received = ingredients
        return [StubIssue()]


def make_service(response: str = "{}") -> DeepSeekService:
    service = object.__new__(DeepSeekService)
    service.context_builder = StubContextBuilder()
    service.validator = StubValidator()
    service.complete = AsyncMock(return_value=response)
    return service


@pytest.mark.asyncio
async def test_analyze_perfume_builds_template_prompt_and_parses_json():
    service = make_service('{"scent_profile": {"top_notes": ["Bergamot"]}}')

    result = await service.analyze_perfume(
        name="Citrus Test",
        ingredients=[{"name": "Bergamot", "percentage": 100.0}],
        concentration=15.0,
    )

    assert result["scent_profile"]["top_notes"] == ["Bergamot"]
    prompt = service.complete.await_args.args[0]
    assert "Perfume Name: Citrus Test" in prompt
    assert "$dosage_guidelines" not in prompt


@pytest.mark.asyncio
async def test_validate_chemistry_serializes_synchronous_validator_results():
    service = make_service()
    ingredients = [{"name": "Alpha Irone", "percentage": 1.0}]

    result = await service.validate_chemistry({"ingredients": ingredients})

    assert service.validator.received == ingredients
    assert result == {
        "issues": [{"severity": "warning", "message": "check dilution"}],
        "total_issues": 1,
    }
