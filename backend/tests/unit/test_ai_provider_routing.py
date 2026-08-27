from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.ai import enhanced_factory, factory


@pytest.mark.parametrize(
    ("detector", "model"),
    [
        (factory.AIModelDetector, "deepseek-v4-pro"),
        (factory.AIModelDetector, "deepseek/deepseek-v4-flash"),
        (enhanced_factory.ScientificAIModelDetector, "deepseek-v4-pro"),
        (
            enhanced_factory.ScientificAIModelDetector,
            "deepseek/deepseek-v4-flash",
        ),
    ],
)
def test_deepseek_models_route_explicitly(detector: object, model: str) -> None:
    assert detector.detect_provider(model) == "deepseek"


@pytest.mark.parametrize(
    "detector",
    [
        factory.AIModelDetector,
        enhanced_factory.ScientificAIModelDetector,
    ],
)
def test_unknown_models_fail_closed(detector: object) -> None:
    with pytest.raises(ValueError, match="Unknown"):
        detector.detect_provider("unregistered-provider/model")


def test_unknown_forced_provider_fails_closed() -> None:
    with pytest.raises(ValueError, match="Unknown AI provider"):
        factory.create_ai_service(force_provider="unregistered")

    with pytest.raises(ValueError, match="Unknown scientific AI provider"):
        enhanced_factory.create_scientific_ai_service(
            force_provider="unregistered",
        )


def test_scientific_factory_supports_configured_deepseek(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StubDeepSeekService:
        def __init__(self, cache: object = None) -> None:
            self.cache = cache

    settings = SimpleNamespace(
        AI_PROVIDER="deepseek",
        DEEPSEEK_MODEL="deepseek-v4-pro",
    )
    monkeypatch.setattr(enhanced_factory, "get_settings", lambda: settings)
    monkeypatch.setattr(enhanced_factory, "get_model_registry", object)
    monkeypatch.setattr(
        enhanced_factory,
        "DeepSeekService",
        StubDeepSeekService,
    )

    cache = object()
    service = enhanced_factory.create_scientific_ai_service(cache=cache)

    assert isinstance(service, StubDeepSeekService)
    assert service.cache is cache
