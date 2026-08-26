"""OpenTelemetry must be opt-in and harmless when disabled."""

import builtins
from types import SimpleNamespace

from fastapi import FastAPI

from app.core.config import Settings
from app.core.tracing import setup_tracing


def _reject_otel_imports(monkeypatch):
    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "opentelemetry" or name.startswith("opentelemetry."):
            raise AssertionError(f"unexpected OpenTelemetry import: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)


def test_tracing_export_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("OTEL_ENABLED", raising=False)

    settings = Settings(_env_file=None)

    assert settings.OTEL_ENABLED is False


def test_setup_tracing_does_not_import_sdk_when_project_flag_is_disabled(
    monkeypatch,
):
    monkeypatch.setattr(
        "app.core.config.get_settings",
        lambda: SimpleNamespace(OTEL_ENABLED=False),
    )
    _reject_otel_imports(monkeypatch)

    setup_tracing(FastAPI())


def test_setup_tracing_honors_standard_sdk_disable_switch(monkeypatch):
    monkeypatch.setattr(
        "app.core.config.get_settings",
        lambda: SimpleNamespace(OTEL_ENABLED=True),
    )
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    _reject_otel_imports(monkeypatch)

    setup_tracing(FastAPI())
