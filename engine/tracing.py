"""OpenTelemetry tracing for the perfume-chem reconstruction engine.

Exports to the AI Toolkit trace viewer via OTLP HTTP.
Default endpoint: http://localhost:4318  (AI Toolkit collector)

Usage
-----
# In your entry-point script (before running the pipeline):
    from engine.tracing import setup_tracing
    setup_tracing()          # connect to AI Toolkit on localhost:4318

# The pipeline auto-initialises tracing on first use if setup_tracing()
# was not called explicitly (useful during tests / ad-hoc runs).

# Functions decorated with @traced("span.name") emit a span automatically.
# The root pipeline span is set by the @traced decorator on
# run_reconstruction_pipeline().
"""

from __future__ import annotations

import functools
from typing import Any, Callable, TypeVar

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.trace import StatusCode

# ── Configuration ──────────────────────────────────────────────────
OTLP_ENDPOINT = "http://localhost:4318/v1/traces"
SERVICE_NAME = "perfume-chem-engine"

_provider: TracerProvider | None = None


# ══════════════════════════════════════════════════════════════════════
# Setup
# ══════════════════════════════════════════════════════════════════════

def setup_tracing(endpoint: str = OTLP_ENDPOINT) -> None:
    """Initialise the global TracerProvider with OTLP HTTP export.

    Safe to call multiple times — subsequent calls are no-ops.
    """
    global _provider
    if _provider is not None:
        return

    resource = Resource.create({"service.name": SERVICE_NAME})
    exporter = OTLPSpanExporter(endpoint=endpoint)
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _provider = provider


def get_tracer() -> trace.Tracer:
    """Return the shared engine tracer, auto-initialising if needed."""
    if _provider is None:
        setup_tracing()
    return trace.get_tracer(SERVICE_NAME)


# ══════════════════════════════════════════════════════════════════════
# Decorator
# ══════════════════════════════════════════════════════════════════════

F = TypeVar("F", bound=Callable[..., Any])


def traced(span_name: str) -> Callable[[F], F]:
    """Decorator that wraps a function in an OpenTelemetry span.

    If the first positional argument has a ``name`` attribute
    (i.e. is a ``FragranceSpec``), the following attributes are set
    automatically on the span:

        fragrance.name   fragrance.house   fragrance.year

    If the return value has ``overall_confidence`` and ``elapsed_seconds``
    (i.e. is a ``PipelineReport``), those are also recorded.

    Example::

        @traced("pipeline.run")
        def run_reconstruction_pipeline(spec: FragranceSpec) -> PipelineReport:
            ...
    """
    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer()
            with tracer.start_as_current_span(span_name) as span:
                # Auto-attach FragranceSpec fields
                spec = args[0] if args else kwargs.get("spec")
                if spec is not None and hasattr(spec, "name"):
                    span.set_attribute("fragrance.name", spec.name)
                    span.set_attribute("fragrance.year", getattr(spec, "year", 0))
                    span.set_attribute("fragrance.house", getattr(spec, "house", ""))
                    span.set_attribute("fragrance.perfumer", getattr(spec, "perfumer", ""))
                    span.set_attribute("fragrance.concentration_pct",
                                       getattr(spec, "concentration_pct", 0.0))

                try:
                    result = fn(*args, **kwargs)

                    # Auto-attach PipelineReport summary fields
                    if result is not None:
                        if hasattr(result, "overall_confidence"):
                            span.set_attribute("pipeline.overall_confidence",
                                               result.overall_confidence)
                        if hasattr(result, "elapsed_seconds"):
                            span.set_attribute("pipeline.elapsed_seconds",
                                               result.elapsed_seconds)
                        if hasattr(result, "category_scores"):
                            # Record each category score as a span attribute
                            for cs in result.category_scores:
                                key = f"stage.{cs.category.lower()}.score"
                                span.set_attribute(key, cs.score)
                            span.set_attribute("pipeline.n_categories",
                                               len(result.category_scores))
                        if hasattr(result, "final_materials"):
                            span.set_attribute("pipeline.n_materials",
                                               len(result.final_materials))

                    return result

                except Exception as exc:
                    span.record_exception(exc)
                    span.set_status(StatusCode.ERROR, str(exc))
                    raise

        return wrapper  # type: ignore[return-value]
    return decorator
