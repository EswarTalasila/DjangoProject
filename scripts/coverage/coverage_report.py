#!/usr/bin/env python3
"""Coverage breakdown and FR test-ID progress report for backend tests.

This script is report-only. It reads pre-existing coverage artifacts
(`coverage.json`, `coverage.junit.xml`) and prints coverage / FR summary
tables. It does not invoke pytest. Backend test orchestration belongs to
`scripts/tasks/test.sh` and `scripts/tasks/lib/pytest_runner.py`.
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]


@dataclass(frozen=True)
class FrSpec:
    """Functional requirement specification mapping."""

    fr: str
    domain: str
    requirements_file: str


FR_SPECS: tuple[FrSpec, ...] = (
    FrSpec("FR-01", "AUTH", "Docs/Wiki/requirements/FR-01-Auth.md"),
    FrSpec("FR-02", "REG", "Docs/Wiki/requirements/FR-02-Registration.md"),
    FrSpec("FR-03", "SUDO", "Docs/Wiki/requirements/FR-03-Sudo.md"),
    FrSpec("FR-04", "USER", "Docs/Wiki/requirements/FR-04-User.md"),
    FrSpec("FR-05", "CRS", "Docs/Wiki/requirements/FR-05-Courses.md"),
    FrSpec("FR-06", "ATMPL", "Docs/Wiki/requirements/FR-06-Assignment-Templates.md"),
    FrSpec("FR-07", "ASGN", "Docs/Wiki/requirements/FR-07-Assignments.md"),
    FrSpec("FR-08", "SUB", "Docs/Wiki/requirements/FR-08-Submissions.md"),
    FrSpec("FR-09", "VIZ", "Docs/Wiki/requirements/FR-09-Visualization.md"),
    FrSpec("FR-10", "EXP", "Docs/Wiki/requirements/FR-10-Export.md"),
    FrSpec("FR-12", "ENV", "Docs/Wiki/requirements/FR-12-Environment.md"),
    FrSpec("FR-13", "INFRA", "Docs/Wiki/requirements/FR-13-Infrastructure.md"),
    FrSpec("FR-14", "ARCH", "Docs/Wiki/requirements/FR-14-Lifecycle-Archival.md"),
    FrSpec("FR-15", "IMG", "Docs/Wiki/requirements/FR-15-Image-Upload.md"),
)


MODULE_DESCRIPTIONS: dict[str, str] = {
    "accounts": "Auth/registration domain logic and APIs",
    "courses": "Course and enrollment domain logic",
    "assignment_templates": "AssignmentTemplate domain",
    "assignments": "Assignment domain",
    "submissions": "Submission domain",
    "visualizations": "Visualization domain",
    "exports": "Export/report domain",
    "core": "Shared core infrastructure/permissions",
    "config": "Environment/settings/runtime config",
    "manage.py": "Django entrypoint script",
    "<other>": "Other source files",
}


def _repo_root() -> Path:
    """Return the repository root directory."""
    return Path(__file__).resolve().parents[2]


def _find_pyproject(root: Path) -> Path | None:
    """Locate pyproject.toml in repo root or backend subdirectory."""
    for candidate in (root / "pyproject.toml", root / "backend" / "pyproject.toml"):
        if candidate.exists():
            return candidate
    return None


def _read_global_fail_under(root: Path, fallback: float = 80.0) -> float:
    """Read coverage fail_under threshold from pyproject.toml."""
    pyproject = _find_pyproject(root)
    if not pyproject or tomllib is None:
        return fallback
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except Exception:
        return fallback
    return float(
        data.get("tool", {})
        .get("coverage", {})
        .get("report", {})
        .get("fail_under", fallback)
    )


def _safe_int(value: Any, default: int = 0) -> int:
    """Coerce *value* to int, returning *default* on failure."""
    try:
        return int(value)
    except Exception:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Coerce *value* to float, returning *default* on failure."""
    try:
        return float(value)
    except Exception:
        return default


def _module_from_source_path(path: str) -> str:
    """Extract top-level module name from a `src/<module>/...` path."""
    normalized = path.replace("\\", "/")
    if normalized == "src/manage.py":
        return "manage.py"
    if normalized.startswith("src/"):
        parts = normalized.split("/")
        if len(parts) > 1:
            return parts[1]
    return "<other>"


def _aggregate_module_coverage(coverage_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Group per-file coverage data into per-module summary rows."""
    files = coverage_data.get("files", {})
    modules: dict[str, dict[str, int]] = {}
    for path, payload in files.items():
        module = _module_from_source_path(path)
        summary = payload.get("summary", {})
        row = modules.setdefault(
            module,
            {"statements": 0, "missing": 0, "branches": 0, "branch_missing": 0},
        )
        row["statements"] += _safe_int(summary.get("num_statements"))
        row["missing"] += _safe_int(summary.get("missing_lines"))
        row["branches"] += _safe_int(summary.get("num_branches"))
        row["branch_missing"] += _safe_int(summary.get("missing_branches"))

    result: list[dict[str, Any]] = []
    for module in sorted(modules):
        row = modules[module]
        statements = row["statements"]
        covered = statements - row["missing"]
        coverage_pct = (covered / statements * 100.0) if statements else 0.0
        branches = row["branches"]
        branch_cov = (
            (branches - row["branch_missing"]) / branches * 100.0 if branches else 0.0
        )
        result.append(
            {
                "name": module,
                "statements": statements,
                "missing": row["missing"],
                "coverage_pct": coverage_pct,
                "branches": branches,
                "branch_missing": row["branch_missing"],
                "branch_coverage_pct": branch_cov,
            }
        )
    return result


def _normalize_test_id(value: str) -> str:
    """Strip trailing wildcard underscores from test IDs."""
    return value.rstrip("_")


def _extract_expected_ids(requirements_path: Path, domain: str) -> set[str]:
    """Scan a requirements markdown file for expected test IDs."""
    if not requirements_path.exists():
        return set()
    text = requirements_path.read_text(encoding="utf-8")
    import re

    pattern = re.compile(rf"\btest_{re.escape(domain)}_[A-Z0-9_]+\b")
    return {_normalize_test_id(match.group(0)) for match in pattern.finditer(text)}


def _parse_junit_test_ids(junit_xml: Path) -> tuple[set[str], set[str]]:
    """Return `(seen_ids, passed_ids)` parsed from junit xml."""
    if not junit_xml.exists():
        return set(), set()
    try:
        root = ET.parse(junit_xml).getroot()
    except ET.ParseError:
        return set(), set()

    import re

    pattern = re.compile(r"\btest_[A-Z0-9_]+\b")
    seen: set[str] = set()
    passed: set[str] = set()

    for testcase in root.iter("testcase"):
        name = testcase.attrib.get("name", "")
        classname = testcase.attrib.get("classname", "")
        haystack = f"{classname}::{name}"
        matched = {_normalize_test_id(m.group(0)) for m in pattern.finditer(haystack)}
        if not matched:
            continue
        seen.update(matched)
        failed = (
            testcase.find("failure") is not None or testcase.find("error") is not None
        )
        skipped = testcase.find("skipped") is not None
        if not failed and not skipped:
            passed.update(matched)
    return seen, passed


def _build_fr_progress(
    root: Path, passed_ids: set[str], seen_ids: set[str]
) -> list[dict[str, Any]]:
    """Build per-FR progress rows from docs and junit results."""
    rows: list[dict[str, Any]] = []
    for spec in FR_SPECS:
        expected = _extract_expected_ids(root / spec.requirements_file, spec.domain)
        matched_seen = expected & seen_ids
        matched_passed = expected & passed_ids
        missing = expected - matched_passed
        expected_count = len(expected)
        pass_rate = (
            (len(matched_passed) / expected_count * 100.0) if expected_count else 0.0
        )
        if expected_count == 0:
            status = "NO-IDS"
        elif not missing:
            status = "PASS"
        else:
            status = "FAIL"
        rows.append(
            {
                "fr": spec.fr,
                "domain": spec.domain,
                "expected": expected_count,
                "seen": len(matched_seen),
                "passed": len(matched_passed),
                "missing": len(missing),
                "pass_rate": pass_rate,
                "status": status,
            }
        )
    return rows


def _fmt_pct(value: float) -> str:
    """Format a percentage value as a right-aligned string."""
    return f"{value:6.2f}%"


def _coverage_status(value: float, threshold: float = 80.0) -> str:
    """Map coverage percentage to a status label."""
    if value >= threshold:
        return "PASS"
    if value >= 60.0:
        return "WARN"
    return "FAIL"


def _module_path_label(module_name: str) -> str:
    """Return path-style label for module coverage rows."""
    if module_name == "manage.py":
        return "src/manage.py"
    if module_name == "<other>":
        return "src/<other>"
    return f"src/{module_name}/*"


def _print_table(title: str, headers: list[str], rows: list[list[str]]) -> None:
    """Print a formatted ASCII table with auto-sized columns."""
    print(f"\n{title}")
    print("-" * len(title))
    widths = [len(h) for h in headers]
    for row in rows:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], len(value))

    header = " | ".join(h.ljust(widths[idx]) for idx, h in enumerate(headers))
    sep = "-+-".join("-" * widths[idx] for idx in range(len(headers)))
    print(header)
    print(sep)
    for row in rows:
        print(" | ".join(row[idx].ljust(widths[idx]) for idx in range(len(headers))))


def _evaluate_gate(
    *,
    gate_mode: str,
    min_pct: float,
    domain: str | None,
    global_total_pct: float,
    fr_rows: list[dict[str, Any]],
    global_threshold: float,
) -> tuple[bool, str]:
    """Evaluate the coverage gate and return `(passed, description)`."""
    if gate_mode == "none":
        return True, "gate=none (report-only)"
    if gate_mode == "global":
        ok = global_total_pct >= global_threshold
        msg = f"gate=global total={global_total_pct:.2f}% threshold={global_threshold:.2f}%"
        return ok, msg

    if not domain:
        return False, "gate=domain requires --domain"
    row = next((item for item in fr_rows if item["fr"] == domain), None)
    if row is None:
        return False, f"domain {domain} not found"
    ok = row["pass_rate"] >= min_pct
    msg = f"gate=domain {domain} pass_rate={row['pass_rate']:.2f}% threshold={min_pct:.2f}%"
    return ok, msg


def _print_coverage_report(
    root: Path,
    coverage_json: Path,
    junit_xml: Path,
    *,
    gate_mode: str,
    gate_domain: str | None,
    gate_min_pct: float,
) -> int:
    """Read pre-existing artifacts and print summary tables."""
    if not coverage_json.exists():
        print(f"\nERROR: coverage json not found at {coverage_json}", file=sys.stderr)
        return 1

    coverage_data = json.loads(coverage_json.read_text(encoding="utf-8"))
    module_rows = _aggregate_module_coverage(coverage_data)
    totals = coverage_data.get("totals", {})
    total_statements = _safe_int(totals.get("num_statements"))
    total_missing = _safe_int(totals.get("missing_lines"))
    total_pct = _safe_float(totals.get("percent_covered"))
    if total_statements and total_pct == 0.0:
        total_pct = (total_statements - total_missing) / total_statements * 100.0

    seen_ids, passed_ids = _parse_junit_test_ids(junit_xml)
    fr_rows = _build_fr_progress(root, passed_ids=passed_ids, seen_ids=seen_ids)
    global_threshold = _read_global_fail_under(root)

    module_table = [
        [
            _module_path_label(row["name"]),
            MODULE_DESCRIPTIONS.get(row["name"], "Module coverage summary"),
            _coverage_status(row["coverage_pct"], global_threshold),
            _fmt_pct(row["coverage_pct"]),
        ]
        for row in module_rows
    ]
    module_table.append(
        [
            "src/* (TOTAL)",
            "All backend source modules",
            _coverage_status(total_pct, global_threshold),
            _fmt_pct(total_pct),
        ]
    )
    _print_table(
        "Coverage Breakdown",
        ["Path/Name", "Description", "Status", "Coverage %"],
        module_table,
    )

    fr_table = [
        [
            row["fr"],
            row["domain"],
            str(row["expected"]),
            str(row["seen"]),
            str(row["passed"]),
            str(row["missing"]),
            _fmt_pct(row["pass_rate"]),
            row["status"],
        ]
        for row in fr_rows
    ]
    _print_table(
        "FR Test-ID Progress",
        ["FR", "Domain", "Expected", "Seen", "Passed", "Missing", "Pass %", "Status"],
        fr_table,
    )

    gate_ok, gate_msg = _evaluate_gate(
        gate_mode=gate_mode,
        min_pct=gate_min_pct,
        domain=gate_domain,
        global_total_pct=total_pct,
        fr_rows=fr_rows,
        global_threshold=global_threshold,
    )
    print(f"\nGate: {gate_msg}")
    if not gate_ok:
        print("Result: gate failed.", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    """CLI entry point for report-only coverage output."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gate",
        choices=("none", "global", "domain"),
        default="none",
        help="Gating mode for exit status.",
    )
    parser.add_argument(
        "--domain",
        help="FR domain gate target (e.g., FR-01, FR-02) when --gate=domain.",
    )
    parser.add_argument(
        "--min",
        type=float,
        default=80.0,
        help="Minimum pass-rate threshold for --gate=domain.",
    )
    parser.add_argument(
        "--coverage-json",
        default="coverage.json",
        help="Coverage json output path (default: coverage.json).",
    )
    parser.add_argument(
        "--junit-xml",
        default="coverage.junit.xml",
        help="JUnit xml output path (default: coverage.junit.xml).",
    )
    args = parser.parse_args()

    root = _repo_root()
    coverage_json = Path(args.coverage_json)
    if not coverage_json.is_absolute():
        coverage_json = root / coverage_json
    junit_xml = Path(args.junit_xml)
    if not junit_xml.is_absolute():
        junit_xml = root / junit_xml

    rc = _print_coverage_report(
        root,
        coverage_json,
        junit_xml,
        gate_mode=args.gate,
        gate_domain=args.domain,
        gate_min_pct=args.min,
    )
    if rc == 0:
        print("Result: success.")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
