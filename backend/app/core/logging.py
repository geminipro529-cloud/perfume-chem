"""Structured logging configuration with OpenTelemetry trace correlation"""

import logging
import sys
from typing import Any
from app.core.config import get_settings


class TraceContextFilter(logging.Filter):
    """Inject current OTEL trace_id and span_id into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            from opentelemetry import trace
            span = trace.get_current_span()
            ctx = span.get_span_context()
            if ctx and ctx.is_valid:
                record.trace_id = format(ctx.trace_id, "032x")
                record.span_id = format(ctx.span_id, "016x")
            else:
                record.trace_id = ""
                record.span_id = ""
        except Exception:
            record.trace_id = ""
            record.span_id = ""
        return True


def setup_logging() -> None:
    """Configure application logging"""
    settings = get_settings()

    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(TraceContextFilter())

    fmt = "%(asctime)s %(name)s %(levelname)s"
    fmt += " trace=%(trace_id)s span=%(span_id)s"
    fmt += " %(message)s"
    handler.setFormatter(logging.Formatter(fmt))

    logging.basicConfig(level=log_level, handlers=[handler], force=True)

    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name"""
    return logging.getLogger(name)
