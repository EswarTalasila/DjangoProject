"""Simple file exporter for OpenTelemetry spans."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult


class FileSpanExporter(SpanExporter):
    """Append span data as JSON lines for offline diagram generation."""

    def __init__(self, path: str):
        """Initialize a span exporter that writes JSONL to disk."""
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def export(self, spans: Iterable) -> SpanExportResult:
        """Serialize and append spans to the trace file."""
        with self._path.open("a", encoding="utf-8") as handle:
            for span in spans:
                handle.write(json.dumps(_span_to_dict(span), ensure_ascii=True) + "\n")
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:  # pragma: no cover - required by interface
        """Finalize exporter resources (no-op for file exporter)."""
        return None

    def force_flush(self, timeout_millis: int = 30000) -> bool:  # pragma: no cover
        """Return True since writes are synchronous."""
        return True


def _span_to_dict(span) -> dict:
    """Convert a span to a JSON-serializable dict."""
    parent = span.parent
    return {
        "trace_id": _format_id(span.context.trace_id, 32),
        "span_id": _format_id(span.context.span_id, 16),
        "parent_span_id": _format_id(parent.span_id, 16) if parent else None,
        "name": span.name,
        "kind": span.kind.name,
        "start_time_unix_nano": span.start_time,
        "end_time_unix_nano": span.end_time,
        "start_time_iso": _format_time(span.start_time),
        "end_time_iso": _format_time(span.end_time),
        "attributes": _coerce_attributes(span.attributes),
        "resource": _coerce_attributes(getattr(span.resource, "attributes", {})),
    }


def _coerce_attributes(attrs) -> dict:
    """Normalize span attributes into JSON-friendly values."""
    if not attrs:
        return {}
    coerced = {}
    for key, value in attrs.items():
        try:
            json.dumps(value)
            coerced[key] = value
        except TypeError:
            coerced[key] = str(value)
    return coerced


def _format_id(value: int, width: int) -> str:
    """Format an OpenTelemetry identifier as hex."""
    return f"{value:0{width}x}"


def _format_time(unix_nano: int | None) -> str | None:
    """Format timestamps for trace output."""
    if unix_nano is None:
        return None
    return datetime.fromtimestamp(unix_nano / 1_000_000_000, tz=UTC).isoformat()
