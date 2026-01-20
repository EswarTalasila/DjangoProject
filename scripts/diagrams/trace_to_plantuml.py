#!/usr/bin/env python3
"""Convert OTEL JSONL spans to PlantUML sequence diagrams."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to OTEL JSONL span export")
    parser.add_argument("--out", required=True, help="Output file or directory")
    parser.add_argument("--trace-id", default="", help="Specific trace ID to export")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of traces")
    parser.add_argument(
        "--group-by",
        choices=["trace", "route"],
        default="route",
        help="Group sequence diagrams by trace or route",
    )
    parser.add_argument(
        "--route-depth",
        type=int,
        default=1,
        help="Route segment depth to use for folder grouping",
    )
    parser.add_argument(
        "--status-folders",
        action="store_true",
        help="Split route groups into success/error folders based on HTTP status",
    )
    args = parser.parse_args()

    spans = load_spans(Path(args.input))
    traces = group_by_trace(spans)
    if args.trace_id:
        traces = {args.trace_id: traces.get(args.trace_id, [])}

    out_path = Path(args.out)
    if out_path.suffix.lower() == ".wsd":
        trace_id, trace_spans = first_trace(traces)
        if not trace_spans:
            raise SystemExit("No spans found for trace.")
        out_path.write_text(build_sequence(trace_spans), encoding="utf-8")
        print(f"Wrote {out_path}")
        return 0

    out_path.mkdir(parents=True, exist_ok=True)
    written = 0
    if args.group_by == "trace":
        for trace_id, trace_spans in sorted(traces.items()):
            if not trace_spans:
                continue
            if args.limit and written >= args.limit:
                break
            filename = f"seq-trace-{trace_id}.wsd"
            target = out_path / filename
            target.write_text(build_sequence(trace_spans), encoding="utf-8")
            written += 1
        print(f"Wrote {written} sequence diagram(s) to {out_path}")
        return 0

    grouped = group_by_route(traces)
    for group_key, trace_spans in sorted(grouped.items()):
        if not trace_spans:
            continue
        if args.limit and written >= args.limit:
            break
        method, route, status = group_key
        route_group = route_group_folder(route, args.route_depth)
        status_group = status_folder(status) if args.status_folders else ""
        target_dir = out_path / route_group
        if status_group:
            target_dir = target_dir / status_group
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = build_route_filename(method, route, status)
        target = target_dir / filename
        target.write_text(build_sequence(trace_spans), encoding="utf-8")
        written += 1
    print(f"Wrote {written} sequence diagram(s) to {out_path}")
    return 0


def load_spans(path: Path) -> list[dict]:
    spans: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            spans.append(json.loads(line))
    return spans


def group_by_trace(spans: Iterable[dict]) -> dict[str, list[dict]]:
    traces: dict[str, list[dict]] = {}
    for span in spans:
        trace_id = span.get("trace_id")
        if not trace_id:
            continue
        traces.setdefault(trace_id, []).append(span)
    return traces


def group_by_route(traces: dict[str, list[dict]]) -> dict[tuple[str, str, str], list[dict]]:
    grouped: dict[tuple[str, str, str], list[dict]] = {}
    for trace_spans in traces.values():
        if not trace_spans:
            continue
        root = find_root(trace_spans)
        method, route, status = route_signature(root)
        key = (method, route, status)
        current = grouped.get(key)
        if current is None or len(trace_spans) > len(current):
            grouped[key] = trace_spans
    return grouped


def first_trace(traces: dict[str, list[dict]]) -> tuple[str, list[dict]]:
    for trace_id, trace_spans in sorted(traces.items()):
        return trace_id, trace_spans
    return "", []


def build_sequence(spans: list[dict]) -> str:
    by_id = {span.get("span_id"): span for span in spans}
    root = find_root(spans)

    participants = {"Client"}
    root_label = span_label(root) if root else "Backend"
    participants.add(root_label)

    events: list[tuple[str, str, str]] = []
    if root:
        events.append(("Client", root_label, span_title(root)))

    for span in sorted(spans, key=lambda s: s.get("start_time_unix_nano", 0)):
        if root and span.get("span_id") == root.get("span_id"):
            continue
        attrs = span.get("attributes", {})
        label = span_label(span)
        participants.add(label)
        if attrs.get("db.system"):
            events.append((root_label, "Postgres", attrs.get("db.statement", span.get("name", "db"))))
            participants.add("Postgres")
            continue
        if attrs.get("http.method") and span.get("kind") == "CLIENT":
            url = attrs.get("http.url") or attrs.get("http.target") or span.get("name")
            events.append((root_label, label, f"{attrs.get('http.method')} {url}"))
            continue
        parent = by_id.get(span.get("parent_span_id"))
        if parent:
            events.append((span_label(parent), label, span.get("name", "call")))

    lines = ["@startuml", "autonumber"]
    for participant in sorted(participants):
        if participant == "Postgres":
            lines.append(f"database {participant}")
        else:
            lines.append(f"participant {participant}")
    lines.append("")

    for src, dst, msg in events:
        safe_msg = msg.replace("\n", " ").strip()
        lines.append(f"{src} ->> {dst}: {safe_msg}")

    lines.append("@enduml")
    return "\n".join(lines) + "\n"


def route_signature(span: dict | None) -> tuple[str, str, str]:
    if not span:
        return ("UNKNOWN", "/unknown", "unknown")
    attrs = span.get("attributes", {})
    method = attrs.get("http.method") or attrs.get("http.request.method") or "UNKNOWN"
    route = (
        attrs.get("http.route")
        or attrs.get("http.target")
        or attrs.get("url.path")
        or attrs.get("http.url")
        or span.get("name")
        or "/unknown"
    )
    status_value = (
        attrs.get("http.status_code")
        or attrs.get("http.response.status_code")
        or attrs.get("http.status")
    )
    status = normalize_status(status_value, span.get("status"))
    return (str(method).upper(), str(route), status)


def normalize_status(value: object, status_payload: object) -> str:
    if value is not None:
        try:
            return str(int(value))
        except (TypeError, ValueError):
            return str(value)
    if isinstance(status_payload, dict):
        code = status_payload.get("code")
        if code is not None:
            return str(code)
    return "unknown"


def status_folder(status: str) -> str:
    try:
        code = int(status)
    except (TypeError, ValueError):
        return "unknown"
    return "error" if code >= 400 else "success"


def route_group_folder(route: str, depth: int) -> str:
    cleaned = route.split("?")[0].strip("/")
    if not cleaned:
        return "root"
    parts = [p for p in cleaned.split("/") if p]
    if parts and parts[0].lower() == "api" and len(parts) > 1:
        parts = parts[1:]
    if parts and parts[0].lower().startswith("v") and parts[0][1:].isdigit():
        parts = parts[1:]
    if depth <= 0:
        depth = 1
    return sanitize("-".join(parts[:depth]))


def build_route_filename(method: str, route: str, status: str) -> str:
    cleaned = route.split("?")[0]
    slug = sanitize(cleaned.strip("/")) or "root"
    return f"seq-{method.lower()}-{slug}-{status}.wsd"


def span_label(span: dict | None) -> str:
    if not span:
        return "Backend"
    attrs = span.get("attributes", {})
    resource = span.get("resource", {})
    if attrs.get("db.system"):
        return "Postgres"
    if attrs.get("peer.service"):
        return sanitize(str(attrs["peer.service"]))
    if resource.get("service.name"):
        return sanitize(str(resource["service.name"]))
    return "Backend"


def span_title(span: dict) -> str:
    attrs = span.get("attributes", {})
    if attrs.get("http.method"):
        path = attrs.get("http.route") or attrs.get("http.target") or attrs.get("http.url")
        return f"{attrs.get('http.method')} {path}"
    return span.get("name", "request")


def find_root(spans: list[dict]) -> dict | None:
    by_id = {span.get("span_id"): span for span in spans}
    for span in sorted(spans, key=lambda s: s.get("start_time_unix_nano", 0)):
        parent_id = span.get("parent_span_id")
        if not parent_id or parent_id not in by_id:
            return span
    return None


def sanitize(value: str) -> str:
    cleaned = value.replace("/", "-").replace(" ", "-").replace("{", "").replace("}", "")
    cleaned = cleaned.replace(":", "-").replace(".", "-")
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
