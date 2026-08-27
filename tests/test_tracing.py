from engine import tracing


def test_get_tracer_does_not_auto_initialize_exporter(monkeypatch):
    monkeypatch.setattr(tracing, "_provider", None)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("get_tracer must not initialize an exporter")

    monkeypatch.setattr(tracing, "setup_tracing", fail_if_called)

    tracer = tracing.get_tracer()
    with tracer.start_as_current_span("no-op-smoke"):
        pass

    assert tracing._provider is None


def test_setup_tracing_honors_otel_sdk_disabled(monkeypatch):
    monkeypatch.setattr(tracing, "_provider", None)
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("disabled tracing must not construct an exporter")

    monkeypatch.setattr(tracing, "OTLPSpanExporter", fail_if_called)

    tracing.setup_tracing()

    assert tracing._provider is None


def test_setup_tracing_explicitly_configures_requested_exporter(monkeypatch):
    events = {}

    class FakeExporter:
        def __init__(self, endpoint):
            events["endpoint"] = endpoint

    class FakeProcessor:
        def __init__(self, exporter):
            events["exporter"] = exporter

    class FakeProvider:
        def __init__(self, resource):
            events["resource"] = resource

        def add_span_processor(self, processor):
            events["processor"] = processor

    monkeypatch.setattr(tracing, "_provider", None)
    monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
    monkeypatch.setenv(
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
        "http://collector.example/v1/traces",
    )
    monkeypatch.setattr(tracing, "OTLPSpanExporter", FakeExporter)
    monkeypatch.setattr(tracing, "BatchSpanProcessor", FakeProcessor)
    monkeypatch.setattr(tracing, "TracerProvider", FakeProvider)
    monkeypatch.setattr(
        tracing.trace,
        "set_tracer_provider",
        lambda provider: events.__setitem__("provider", provider),
    )

    tracing.setup_tracing()

    assert events["endpoint"] == "http://collector.example/v1/traces"
    assert events["provider"] is tracing._provider
    assert events["processor"] is not None
