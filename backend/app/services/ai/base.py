"""Base AI service interface"""

import asyncio
import functools
import inspect
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional, Dict, Any


def _make_complete_tracer(method):
    """Wrap a coroutine ``complete()`` method with an OTel span."""
    @functools.wraps(method)
    async def wrapper(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7, **kwargs):
        with self._tracer.start_as_current_span("ai.complete") as span:
            span.set_attribute("ai.provider", type(self).__name__)
            span.set_attribute("ai.model", getattr(self, "model", "unknown"))
            span.set_attribute("ai.prompt_length", len(prompt))
            span.set_attribute("ai.max_tokens", max_tokens)
            span.set_attribute("ai.temperature", temperature)
            try:
                result = await method(self, prompt, max_tokens=max_tokens, temperature=temperature, **kwargs)
                span.set_attribute("ai.completion_length", len(result) if isinstance(result, str) else 0)
                return result
            except Exception as exc:
                try:
                    from opentelemetry.trace import StatusCode
                    span.record_exception(exc)
                    span.set_status(StatusCode.ERROR, str(exc))
                except Exception:
                    pass
                raise
    return wrapper


def _make_stream_tracer(method):
    """Wrap an async-generator ``stream()`` method with an OTel span."""
    @functools.wraps(method)
    async def wrapper(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7, **kwargs):
        with self._tracer.start_as_current_span("ai.stream") as span:
            span.set_attribute("ai.provider", type(self).__name__)
            span.set_attribute("ai.model", getattr(self, "model", "unknown"))
            span.set_attribute("ai.prompt_length", len(prompt))
            span.set_attribute("ai.max_tokens", max_tokens)
            span.set_attribute("ai.temperature", temperature)
            chunk_count = 0
            try:
                async for chunk in method(self, prompt, max_tokens=max_tokens, temperature=temperature, **kwargs):
                    chunk_count += 1
                    yield chunk
                span.set_attribute("ai.stream_chunks", chunk_count)
            except Exception as exc:
                try:
                    from opentelemetry.trace import StatusCode
                    span.record_exception(exc)
                    span.set_status(StatusCode.ERROR, str(exc))
                except Exception:
                    pass
                raise
    return wrapper


class BaseAIService(ABC):
    """Abstract base class for AI services"""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for method_name, make_tracer in (
            ("complete", _make_complete_tracer),
            ("stream", _make_stream_tracer),
        ):
            method = cls.__dict__.get(method_name)
            if method is not None and callable(method):
                setattr(cls, method_name, make_tracer(method))

    @property
    def _tracer(self):
        """Get a tracer scoped to the concrete provider class."""
        from app.core.tracing import get_tracer
        return get_tracer(f"ai.{self.__class__.__name__.lower()}")

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Complete a prompt and return the response"""
        pass

    @abstractmethod
    async def stream(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream completion tokens"""
        pass

    async def analyze_perfume(
        self,
        name: str,
        ingredients: list,
        concentration: float = 15.0
    ) -> Dict[str, Any]:
        """Analyze a perfume composition"""
        raise NotImplementedError

    async def suggest_modifications(
        self,
        formula: Dict[str, Any],
        goal: str
    ) -> Dict[str, Any]:
        """Suggest formula modifications"""
        raise NotImplementedError

    async def suggest_pairings(
        self,
        ingredient: str,
        cas_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """Suggest ingredient pairings"""
        raise NotImplementedError

