"""OpenTelemetry tracing configuration"""

import logging
from fastapi import FastAPI

logger = logging.getLogger(__name__)


def setup_tracing(app: FastAPI) -> None:
    """Initialize OpenTelemetry tracing. Safe to call even if OTEL is disabled."""
    from app.core.config import get_settings
    settings = get_settings()

    if not settings.OTEL_ENABLED:
        logger.info("OpenTelemetry tracing disabled (OTEL_ENABLED=False)")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        resource = Resource.create({
            SERVICE_NAME: settings.OTEL_SERVICE_NAME,
            SERVICE_VERSION: settings.APP_VERSION,
            "deployment.environment": settings.ENVIRONMENT,
        })

        provider = TracerProvider(resource=resource)

        otlp_exporter = OTLPSpanExporter(
            endpoint=f"{settings.OTEL_OTLP_ENDPOINT}/v1/traces",
        )
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

        if settings.DEBUG:
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

        trace.set_tracer_provider(provider)

        FastAPIInstrumentor.instrument_app(app)
        SQLAlchemyInstrumentor().instrument()
        HTTPXClientInstrumentor().instrument()

        try:
            from opentelemetry.instrumentation.redis import RedisInstrumentor
            RedisInstrumentor().instrument()
        except ImportError:
            pass

        logger.info(
            f"OpenTelemetry tracing initialized: service={settings.OTEL_SERVICE_NAME}, "
            f"endpoint={settings.OTEL_OTLP_ENDPOINT}"
        )

    except Exception as exc:
        logger.warning(f"OpenTelemetry tracing setup failed (continuing without tracing): {exc}")


def get_tracer(name: str):
    """Get a tracer instance. Returns a no-op tracer if OTEL is not configured."""
    try:
        from opentelemetry import trace
        return trace.get_tracer(name)
    except ImportError:
        class _NoopSpan:
            def set_attribute(self, *a, **k): pass
            def record_exception(self, *a, **k): pass
            def set_status(self, *a, **k): pass
            def add_event(self, *a, **k): pass

        class _NoopTracer:
            def start_as_current_span(self, name, **kwargs):
                from contextlib import contextmanager

                @contextmanager
                def _noop():
                    yield _NoopSpan()

                return _noop()

        return _NoopTracer()
