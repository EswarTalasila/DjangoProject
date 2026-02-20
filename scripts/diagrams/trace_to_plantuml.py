#!/usr/bin/env python3
"""Convert OTEL JSONL spans to PlantUML sequence diagrams.

Improvements over original:
- Collapses repeated identical DB queries into ``loop Nx`` blocks
- Shortens SQL to ``OPERATION table WHERE col = ?`` form (--full-sql to override)
- Adds response arrow back to Client with HTTP status code
- Properly quotes participant names containing hyphens
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
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
    parser.add_argument(
        "--full-sql",
        action="store_true",
        help="Show full SQL statements instead of shortened form",
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
        out_path.write_text(
            build_sequence(trace_spans, full_sql=args.full_sql), encoding="utf-8"
        )
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
            target.write_text(
                build_sequence(trace_spans, full_sql=args.full_sql), encoding="utf-8"
            )
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
        target.write_text(
            build_sequence(trace_spans, full_sql=args.full_sql), encoding="utf-8"
        )
        written += 1
    print(f"Wrote {written} sequence diagram(s) to {out_path}")
    return 0


# ---------------------------------------------------------------------------
# Span loading & grouping
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Sequence diagram builder
# ---------------------------------------------------------------------------

def build_sequence(spans: list[dict], *, full_sql: bool = False) -> str:
    """Build a PlantUML sequence diagram from a list of spans in one trace."""
    by_id = {span.get("span_id"): span for span in spans}
    root = find_root(spans)

    participants: set[str] = {"Client"}
    root_label = span_label(root) if root else "Backend"
    participants.add(root_label)

    # Collect events: (src, dst, display_msg, dedup_key)
    # dedup_key is the raw SQL for DB spans so identical queries collapse
    raw_events: list[tuple[str, str, str, str]] = []
    if root:
        raw_events.append(("Client", root_label, span_title(root), ""))

    for span in sorted(spans, key=lambda s: s.get("start_time_unix_nano", 0)):
        if root and span.get("span_id") == root.get("span_id"):
            continue
        attrs = span.get("attributes", {})
        label = span_label(span)
        participants.add(label)

        if attrs.get("db.system"):
            raw_sql = attrs.get("db.statement", span.get("name", "db"))
            display = raw_sql if full_sql else shorten_sql(raw_sql)
            raw_events.append((root_label, "Postgres", display, raw_sql))
            participants.add("Postgres")
            continue

        if attrs.get("http.method") and span.get("kind") == "CLIENT":
            url = attrs.get("http.url") or attrs.get("http.target") or span.get("name")
            msg = f"{attrs.get('http.method')} {url}"
            raw_events.append((root_label, label, msg, ""))
            continue

        parent = by_id.get(span.get("parent_span_id"))
        if parent:
            msg = span.get("name", "call")
            raw_events.append((span_label(parent), label, msg, ""))

    # Collapse consecutive identical events into (count, src, dst, msg)
    collapsed = collapse_repeated(raw_events)

    # --- Emit PlantUML ---
    lines = ["@startuml", "autonumber"]
    for participant in sorted(participants):
        qp = _qp(participant)
        if participant == "Postgres":
            lines.append(f"database {qp}")
        else:
            lines.append(f"participant {qp}")
    lines.append("")

    for count, src, dst, msg in collapsed:
        qsrc, qdst = _qp(src), _qp(dst)
        safe_msg = msg.replace("\n", " ").strip()
        if count > 1:
            lines.append(f"loop {count}x")
            lines.append(f"  {qsrc} ->> {qdst}: {safe_msg}")
            lines.append("end")
        else:
            lines.append(f"{qsrc} ->> {qdst}: {safe_msg}")

    # Response arrow back to client
    if root:
        _method, _route, status = route_signature(root)
        qroot = _qp(root_label)
        try:
            code = int(status)
            if code >= 400:
                lines.append(f"{qroot} --x Client: HTTP {status}")
            else:
                lines.append(f"{qroot} -->> Client: HTTP {status}")
        except (TypeError, ValueError):
            lines.append(f"{qroot} -->> Client: response")

    lines.append("@enduml")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Event collapsing
# ---------------------------------------------------------------------------

def collapse_repeated(
    events: list[tuple[str, str, str, str]],
) -> list[tuple[int, str, str, str]]:
    """Collapse consecutive identical events into ``(count, src, dst, msg)``."""
    if not events:
        return []
    result: list[tuple[int, str, str, str]] = []
    i = 0
    while i < len(events):
        src, dst, msg, key = events[i]
        dedup = key or msg
        count = 1
        while i + count < len(events):
            nsrc, ndst, _nmsg, nkey = events[i + count]
            ndedup = nkey or _nmsg
            if nsrc == src and ndst == dst and ndedup == dedup:
                count += 1
            else:
                break
        result.append((count, src, dst, msg))
        i += count
    return result


# ---------------------------------------------------------------------------
# SQL shortening
# ---------------------------------------------------------------------------

_WHERE_COL_RE = re.compile(r'"(\w+)"(?:\."(\w+)")?\s*(?:::|[=<>!]|IN\b)')


def shorten_sql(sql: str) -> str:
    """Shorten SQL to a readable ``OPERATION table [WHERE col = ?]`` form."""
    s = sql.strip()
    u = s.upper()

    def _table(text: str) -> str:
        token = text.strip().split()[0] if text.strip() else "?"
        return token.replace('"', "")

    def _where_col(text: str) -> str:
        idx = text.upper().find(" WHERE ")
        if idx < 0:
            return ""
        clause = text[idx + 7:]
        m = _WHERE_COL_RE.search(clause)
        if m:
            return m.group(2) or m.group(1)
        return ""

    # EXISTS-style: SELECT %s AS "a" FROM ...
    if u.startswith("SELECT %S AS "):
        from_idx = u.find(" FROM ")
        if from_idx >= 0:
            table = _table(s[from_idx + 6:])
            col = _where_col(s)
            return f"EXISTS {table} ({col})" if col else f"EXISTS {table}"

    if u.startswith("SELECT"):
        from_idx = u.find(" FROM ")
        if from_idx >= 0:
            table = _table(s[from_idx + 6:])
            col = _where_col(s)
            return f"SELECT {table} WHERE {col} = ?" if col else f"SELECT {table}"

    if u.startswith("INSERT INTO"):
        table = _table(s[12:])
        return f"INSERT {table}"

    if u.startswith("UPDATE"):
        table = _table(s[7:])
        return f"UPDATE {table} SET ..."

    if u.startswith("DELETE FROM"):
        table = _table(s[12:])
        col = _where_col(s)
        return f"DELETE {table} WHERE {col} = ?" if col else f"DELETE {table}"

    return s[:50] + "..." if len(s) > 50 else s


# ---------------------------------------------------------------------------
# Participant quoting
# ---------------------------------------------------------------------------

def _qp(name: str) -> str:
    """Quote a participant name if it contains PlantUML-special characters."""
    if any(c in name for c in "-. "):
        return f'"{name}"'
    return name


# ---------------------------------------------------------------------------
# Span helpers
# ---------------------------------------------------------------------------

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
    """Sanitize a string for use in filenames across all platforms."""
    cleaned = value.replace("/", "-").replace(" ", "-").replace("{", "").replace("}", "")
    cleaned = cleaned.replace(":", "-").replace(".", "-")
    cleaned = cleaned.replace("<", "").replace(">", "")
    cleaned = cleaned.replace('"', "").replace("|", "").replace("?", "").replace("*", "")
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
