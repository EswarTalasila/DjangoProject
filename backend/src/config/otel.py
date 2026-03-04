"""OpenTelemetry configuration for Django."""

from __future__ import annotations

import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.textmap import W3CTraceContextTextMapPropagator
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor

from config.env import env
from core.otel_exporter import FileSpanExporter

_CONFIGURED = False


def configure_tracing() -> None:
    """Configure tracing."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    if not env.effective_otel_enabled:
        return

    service_name = os.environ.get("OTEL_SERVICE_NAME", "eel-backend")
    resource = Resource(attributes={SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    set_global_textmap(W3CTraceContextTextMapPropagator())

    endpoint = env.otel_exporter_otlp_endpoint
    headers = _parse_headers(os.environ.get("OTEL_EXPORTER_OTLP_HEADERS", ""))
    if endpoint:
        exporter = OTLPSpanExporter(endpoint=endpoint, headers=headers)
        provider.add_span_processor(BatchSpanProcessor(exporter))

    trace_file = env.otel_trace_file
    if trace_file and not env.is_production:
        provider.add_span_processor(SimpleSpanProcessor(FileSpanExporter(trace_file)))

    DjangoInstrumentor().instrument()
    PsycopgInstrumentor().instrument()
    LoggingInstrumentor().instrument()
    _CONFIGURED = True


def _parse_headers(raw: str) -> dict[str, str]:
    """Parse headers."""
    headers: dict[str, str] = {}
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if "=" not in entry:
            continue
        key, value = entry.split("=", 1)
        headers[key.strip()] = value.strip()
    return headers
