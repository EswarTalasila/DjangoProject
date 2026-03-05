"""Unit tests for local OpenTelemetry file exporter."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from opentelemetry.sdk.trace.export import SpanExportResult

from core.otel_exporter import (
    FileSpanExporter,
    _coerce_attributes,
    _format_id,
    _format_time,
    _span_to_dict,
)

pytestmark = pytest.mark.unit



class _NonSerializable:
    def __str__(self):
        return "non-serializable"


def _fake_span():
    return SimpleNamespace(
        context=SimpleNamespace(trace_id=1234, span_id=5678),
        parent=SimpleNamespace(span_id=1111),
        name="SELECT users",
        kind=SimpleNamespace(name="CLIENT"),
        start_time=1_700_000_000_000_000_000,
        end_time=1_700_000_000_100_000_000,
        attributes={"db.system": "postgresql", "raw": _NonSerializable()},
        resource=SimpleNamespace(attributes={"service.name": "eel-backend"}),
    )


def test_export_writes_jsonl_and_returns_success(tmp_path):
    """Exporter writes one JSON line per span and returns SUCCESS."""
    path = tmp_path / "traces" / "spans.jsonl"
    exporter = FileSpanExporter(str(path))

    result = exporter.export([_fake_span()])

    assert result == SpanExportResult.SUCCESS
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["name"] == "SELECT users"
    assert payload["kind"] == "CLIENT"
    assert payload["trace_id"] == _format_id(1234, 32)
    assert payload["span_id"] == _format_id(5678, 16)
    assert payload["parent_span_id"] == _format_id(1111, 16)
    assert payload["attributes"]["raw"] == "non-serializable"


def test_span_to_dict_and_helpers_cover_edge_cases():
    """Helper functions normalize span data and edge-case values."""
    span_dict = _span_to_dict(_fake_span())
    assert span_dict["resource"]["service.name"] == "eel-backend"
    assert span_dict["start_time_iso"] is not None
    assert span_dict["end_time_iso"] is not None

    assert _coerce_attributes({}) == {}
    assert _coerce_attributes(None) == {}
    assert _format_id(15, 4) == "000f"
    assert _format_time(None) is None


def test_exporter_shutdown_and_force_flush_are_noops(tmp_path):
    """Shutdown and force_flush satisfy exporter interface contracts."""
    exporter = FileSpanExporter(str(tmp_path / "trace.jsonl"))
    assert exporter.shutdown() is None
    assert exporter.force_flush() is True
