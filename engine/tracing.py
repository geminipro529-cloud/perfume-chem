"""OpenTelemetry tracing for the perfume-chem reconstruction engine.

Exports to the AI Toolkit trace viewer via OTLP HTTP.
Default endpoint: http://localhost:4318  (AI Toolkit collector)

Usage
-----
# In your entry-point script (before running the pipeline):
    from engine.tracing import setup_tracing
    setup_tracing()          # connect to AI Toolkit on localhost:4318

# Instrumentation is a no-op until an application entry point explicitly calls
# setup_tracing(). Importing or running the reconstruction engine never starts
# an exporter by itself.

# Functions decorated with @traced("span.name") emit a span automatically.
# The root pipeline span is set by the @traced decorator on
# run_reconstruction_pipeline().
"""

from __future__ import annotations

import functools
import os
from typing import Any, Callable, TypeVar

try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.trace import StatusCode

    def _create_otlp_exporter(*args: Any, **kwargs: Any) -> Any:
        # Optional exporter/protobuf dependencies must not affect ordinary
        # engine imports. Import failures still surface on explicit opt-in.
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        return OTLPSpanExporter(*args, **kwargs)

    OTLPSpanExporter = _create_otlp_exporter
except ImportError:  # pragma: no cover - exercised in environments without optional OTEL runtime.
    class _NoopSpan:
        def set_attribute(self, *args, **kwargs):  # pragma: no cover - fallback path
            return None

        def set_status(self, *args, **kwargs):  # pragma: no cover - fallback path
            return None

        def record_exception(self, *args, **kwargs):  # pragma: no cover - fallback path
            return None

    class _NoopTracer:
        def start_as_current_span(self, name: str, **kwargs):  # pragma: no cover - fallback path
            from contextlib import contextmanager

            @contextmanager
            def _scope():
                yield _NoopSpan()

            return _scope()

    class _NoopTraceModule:
        def get_tracer(self, *args, **kwargs):  # pragma: no cover - fallback path
            return _NoopTracer()

        def set_tracer_provider(self, *args, **kwargs):  # pragma: no cover
            return None

        def get_tracer_provider(self):  # pragma: no cover
            return None

    class _NoopResource:
        @classmethod
        def create(cls, *args, **kwargs):  # pragma: no cover - fallback path
            return cls()

    class _NoopExporter:
        def __init__(self, *args, **kwargs):  # pragma: no cover - fallback path
            pass

    class _NoopBatchSpanProcessor:
        def __init__(self, *args, **kwargs):  # pragma: no cover - fallback path
            self.args = args
            self.kwargs = kwargs

    class _NoopTracerProvider:
        def __init__(self, *args, **kwargs):  # pragma: no cover - fallback path
            self.args = args
            self.kwargs = kwargs

        def add_span_processor(self, *args, **kwargs):  # pragma: no cover - fallback path
            return None

    class _NoopStatusCode:
        ERROR = "ERROR"

    _NOOP_TRACE = _NoopTraceModule()
    trace = _NOOP_TRACE  # type: ignore[assignment]
    OTLPSpanExporter = _NoopExporter  # type: ignore[assignment]
    # Runtime compatibility aliases intentionally replace the optional SDK
    # classes only when that SDK cannot be imported.
    Resource = _NoopResource  # type: ignore[assignment,misc]
    TracerProvider = _NoopTracerProvider  # type: ignore[assignment,misc]
    BatchSpanProcessor = _NoopBatchSpanProcessor  # type: ignore[assignment,misc]
    _NOOP_TRACER = _NoopTracer()
    StatusCode = _NoopStatusCode  # type: ignore[assignment,misc]

# ── Configuration ──────────────────────────────────────────────────
OTLP_ENDPOINT = "http://localhost:4318/v1/traces"
SERVICE_NAME = "perfume-chem-engine"

_provider: TracerProvider | None = None


# ══════════════════════════════════════════════════════════════════════
# Setup
# ══════════════════════════════════════════════════════════════════════

def setup_tracing(endpoint: str | None = None) -> None:
    """Initialise the global TracerProvider with OTLP HTTP export.

    This is an explicit application-level opt-in. It is safe to call multiple
    times, and ``OTEL_SDK_DISABLED=true`` keeps the SDK/exporter disabled.
    ``OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`` is honored when no endpoint argument
    is supplied.
    """
    global _provider
    if _provider is not None or os.getenv("OTEL_SDK_DISABLED", "").strip().lower() == "true":
        return

    resolved_endpoint = endpoint or os.getenv(
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
        OTLP_ENDPOINT,
    )
    resource = Resource.create({"service.name": SERVICE_NAME})
    exporter = OTLPSpanExporter(endpoint=resolved_endpoint)
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _provider = provider


def get_tracer() -> trace.Tracer:
    """Return the configured tracer or OpenTelemetry's valid no-op tracer."""
    if trace is None:
        return _NOOP_TRACER  # type: ignore[return-value]
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
