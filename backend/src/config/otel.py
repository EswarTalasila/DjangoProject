"""OpenTelemetry configuration for Django."""

from __future__ import annotations

import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor

from core.otel_exporter import FileSpanExporter

_CONFIGURED = False


def configure_tracing() -> None:
    """Configure tracing."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    if os.environ.get("OTEL_ENABLED", "false").lower() not in ("true", "1", "yes"):
        return

    service_name = os.environ.get("OTEL_SERVICE_NAME", "eel-backend")
    resource = Resource(attributes={SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    headers = _parse_headers(os.environ.get("OTEL_EXPORTER_OTLP_HEADERS", ""))
    if endpoint:
        exporter = OTLPSpanExporter(endpoint=endpoint, headers=headers)
        provider.add_span_processor(BatchSpanProcessor(exporter))

    trace_file = os.environ.get("OTEL_TRACE_FILE")
    if trace_file:
        provider.add_span_processor(SimpleSpanProcessor(FileSpanExporter(trace_file)))

    DjangoInstrumentor().instrument()
    PsycopgInstrumentor().instrument()
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
