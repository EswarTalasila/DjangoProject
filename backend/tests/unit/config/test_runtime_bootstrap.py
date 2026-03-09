"""Unit tests for runtime bootstrap and tracing wiring."""

from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace

import pytest

import config.otel as otel

pytestmark = pytest.mark.unit



def test_configure_tracing_noop_when_disabled(monkeypatch):
    """Tracing setup exits early when effective_otel_enabled is false."""
    otel._CONFIGURED = False
    monkeypatch.setattr(
        otel,
        "env",
        SimpleNamespace(
            effective_otel_enabled=False,
            otel_exporter_otlp_endpoint="",
            otel_trace_file="",
            is_production=False,
        ),
    )

    called = {"provider": False}
    monkeypatch.setattr(otel, "TracerProvider", lambda resource=None: called.update(provider=True))

    otel.configure_tracing()

    assert called["provider"] is False
    assert otel._CONFIGURED is False


def test_configure_tracing_adds_otlp_and_file_processors(monkeypatch, tmp_path):
    """Tracing setup attaches OTLP and file exporters when configured."""
    otel._CONFIGURED = False
    trace_file = tmp_path / "otel-trace.jsonl"
    monkeypatch.setattr(
        otel,
        "env",
        SimpleNamespace(
            effective_otel_enabled=True,
            otel_exporter_otlp_endpoint="http://otel-collector:4318/v1/traces",
            otel_trace_file=str(trace_file),
            is_production=False,
        ),
    )
    monkeypatch.setenv("OTEL_SERVICE_NAME", "eel-backend")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_HEADERS", "Authorization=Bearer token, x=abc")

    class FakeProvider:
        def __init__(self, resource=None):
            self.resource = resource
            self.processors = []

        def add_span_processor(self, processor):
            self.processors.append(processor)

    state = {"provider": None, "django": 0, "psycopg": 0}

    monkeypatch.setattr(otel, "TracerProvider", lambda resource=None: FakeProvider(resource))
    monkeypatch.setattr(
        otel.trace, "set_tracer_provider", lambda provider: state.update(provider=provider)
    )
    monkeypatch.setattr(
        otel, "OTLPSpanExporter", lambda endpoint, headers: ("otlp", endpoint, headers)
    )
    monkeypatch.setattr(otel, "BatchSpanProcessor", lambda exporter: ("batch", exporter))
    monkeypatch.setattr(otel, "FileSpanExporter", lambda path: ("file", path))
    monkeypatch.setattr(otel, "SimpleSpanProcessor", lambda exporter: ("simple", exporter))

    class FakeDjangoInstrumentor:
        def instrument(self):
            state["django"] += 1

    class FakePsycopgInstrumentor:
        def instrument(self):
            state["psycopg"] += 1

    monkeypatch.setattr(otel, "DjangoInstrumentor", lambda: FakeDjangoInstrumentor())
    monkeypatch.setattr(otel, "PsycopgInstrumentor", lambda: FakePsycopgInstrumentor())

    otel.configure_tracing()

    provider = state["provider"]
    assert provider is not None
    assert len(provider.processors) == 2
    assert provider.processors[0][0] == "batch"
    assert provider.processors[0][1][0] == "otlp"
    assert provider.processors[0][1][1] == "http://otel-collector:4318/v1/traces"
    assert provider.processors[0][1][2]["Authorization"] == "Bearer token"
    assert provider.processors[1] == ("simple", ("file", str(trace_file)))
    assert state["django"] == 1
    assert state["psycopg"] == 1
    assert otel._CONFIGURED is True


def test_configure_tracing_is_idempotent(monkeypatch):
    """Second configure_tracing call is guarded by _CONFIGURED."""
    otel._CONFIGURED = True
    called = {"provider": False}
    monkeypatch.setattr(otel, "TracerProvider", lambda resource=None: called.update(provider=True))

    otel.configure_tracing()

    assert called["provider"] is False


def test_parse_headers_skips_invalid_entries():
    """Header parser keeps key=value entries and ignores malformed items."""
    parsed = otel._parse_headers("Authorization=Bearer token, invalid, x-test=abc")

    assert parsed == {"Authorization": "Bearer token", "x-test": "abc"}


def test_wsgi_and_asgi_modules_call_tracing_and_build_application(monkeypatch):
    """ASGI/WSGI modules invoke configure_tracing before creating application."""
    asgi_calls = {"trace": 0}
    wsgi_calls = {"trace": 0}

    monkeypatch.setattr("config.otel.configure_tracing", lambda: asgi_calls.update(trace=1))
    monkeypatch.setattr("django.core.asgi.get_asgi_application", lambda: "asgi-app")
    sys.modules.pop("config.asgi", None)
    asgi_module = importlib.import_module("config.asgi")
    assert asgi_calls["trace"] == 1
    assert asgi_module.application == "asgi-app"

    monkeypatch.setattr("config.otel.configure_tracing", lambda: wsgi_calls.update(trace=1))
    monkeypatch.setattr("django.core.wsgi.get_wsgi_application", lambda: "wsgi-app")
    sys.modules.pop("config.wsgi", None)
    wsgi_module = importlib.import_module("config.wsgi")
    assert wsgi_calls["trace"] == 1
    assert wsgi_module.application == "wsgi-app"
