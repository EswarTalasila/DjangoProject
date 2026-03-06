#!/usr/bin/env python3
"""Unified coverage + FR test-ID progress report for backend tests."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]

import json


@dataclass(frozen=True)
class FrSpec:
    """Functional requirement specification mapping an FR domain to its requirements file."""

    fr: str
    domain: str
    requirements_file: str


FR_SPECS: tuple[FrSpec, ...] = (
    FrSpec("FR-01", "AUTH", "Docs/Wiki/requirements/FR-01-Auth.md"),
    FrSpec("FR-02", "REG", "Docs/Wiki/requirements/FR-02-Registration.md"),
    FrSpec("FR-03", "SUDO", "Docs/Wiki/requirements/FR-03-Sudo.md"),
    FrSpec("FR-04", "USER", "Docs/Wiki/requirements/FR-04-User.md"),
    FrSpec("FR-05", "CRS", "Docs/Wiki/requirements/FR-05-Courses.md"),
    FrSpec("FR-06", "ASMT", "Docs/Wiki/requirements/FR-06-Assessments.md"),
    FrSpec("FR-07", "ASGN", "Docs/Wiki/requirements/FR-07-Assignments.md"),
    FrSpec("FR-08", "SUB", "Docs/Wiki/requirements/FR-08-Submissions.md"),
    FrSpec("FR-09", "VIZ", "Docs/Wiki/requirements/FR-09-Visualization.md"),
    FrSpec("FR-10", "EXP", "Docs/Wiki/requirements/FR-10-Export.md"),
    FrSpec("FR-11", "OBS", "Docs/Wiki/requirements/FR-11-Observability.md"),
    FrSpec("FR-12", "ENV", "Docs/Wiki/requirements/FR-12-Environment.md"),
    FrSpec("FR-13", "INFRA", "Docs/Wiki/requirements/FR-13-Infrastructure.md"),
)

MODULE_DESCRIPTIONS: dict[str, str] = {
    "accounts": "Auth/registration domain logic and APIs",
    "courses": "Course and enrollment domain logic",
    "assessments": "Assessment domain",
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
    """Return the repository root directory (two levels up from this script)."""
    return Path(__file__).resolve().parents[2]


def _find_pyproject(root: Path) -> Path | None:
    """Locate pyproject.toml in the repo root or backend subdirectory."""
    candidates = (root / "pyproject.toml", root / "backend" / "pyproject.toml")
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _read_global_fail_under(root: Path, fallback: float = 80.0) -> float:
    """Read the coverage fail_under threshold from pyproject.toml."""
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


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_PYTEST_PROGRESS_RE = re.compile(r"\[\s*(\d+)%\]")
_PYTEST_TRAILING_PROGRESS_TOKEN_RE = re.compile(
    r"(?:\x1b\[[0-9;]*m)*\s*\[\s*\d+%\](?:\x1b\[[0-9;]*m)*\s*$"
)
_PYTEST_RESULT_LINE_RE = re.compile(
    r"^(?P<prefix>.+?)\s+(?P<status>PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)(?:\s+\[\s*\d+%\])?\s*$"
)
_PYTEST_XDIST_RESULT_LINE_RE = re.compile(
    r"^\[gw\d+\]\s+\[\s*\d+%\]\s+(?P<status>PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\s+(?P<prefix>.+?)\s*$"
)
_PYTEST_ITEM_ONLY_LINE_RE = re.compile(
    r"^(?:\[(?:gw\d+)\]\s+)?tests/.+::\S+(?:\s+-\s+.*)?\s*$"
)
_STATUS_COLORS = {
    "PASSED": "32",
    "FAILED": "31",
    "ERROR": "31",
    "SKIPPED": "33",
    "XFAIL": "33",
    "XPASS": "35",
}


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from *text*."""
    return _ANSI_RE.sub("", text)


def _progress_bar_line(percent: int, width: int) -> str:
    """Render a full-width green progress bar in the form [*****.....] [ 42%]."""
    normalized = max(0, min(100, percent))
    suffix = f" [{normalized:3d}%]"
    # Full-width line: '[' + content + ']' + suffix
    content_width = max(8, width - len(suffix) - 2)
    stars = round((normalized / 100) * content_width)
    bar = f"[{'*' * stars}{'.' * (content_width - stars)}]{suffix}"
    return f"\033[32m{bar}\033[0m"


def _extract_progress_percent(line: str) -> int | None:
    """Extract pytest progress percentage from any '[ NN% ]' token in a line."""
    plain = _strip_ansi(line.rstrip())
    matches = _PYTEST_PROGRESS_RE.findall(plain)
    if not matches:
        return None
    try:
        return max(int(value) for value in matches)
    except ValueError:
        return None


def _strip_trailing_progress_token(line: str) -> str:
    """Remove trailing pytest progress token ('[ xx%]') while preserving status text."""
    newline = ""
    body = line
    if line.endswith("\r\n"):
        body = line[:-2]
        newline = "\r\n"
    elif line.endswith("\n"):
        body = line[:-1]
        newline = "\n"

    plain = _strip_ansi(body)
    if not re.search(r"\[\s*\d+%\]\s*$", plain):
        return line

    stripped = _PYTEST_TRAILING_PROGRESS_TOKEN_RE.sub("", body)
    return f"{stripped}{newline}"


def _format_pytest_result_line(line: str, width: int) -> str | None:
    """
    Reformat a pytest result row to keep status right-aligned and remove progress token.

    Example output:
    tests/.../test_xxx - description                                  [PASSED]
    """
    newline = ""
    body = line
    if line.endswith("\r\n"):
        body = line[:-2]
        newline = "\r\n"
    elif line.endswith("\n"):
        body = line[:-1]
        newline = "\n"

    plain = _strip_ansi(body)
    match = _PYTEST_RESULT_LINE_RE.match(plain)
    if match is None:
        match = _PYTEST_XDIST_RESULT_LINE_RE.match(plain)
    if match is None:
        return None

    prefix = match.group("prefix").rstrip()
    status = match.group("status")
    status_plain = f"[{status}]"
    color = _STATUS_COLORS.get(status, "37")
    status_colored = f"\033[{color}m{status_plain}\033[0m"

    # Keep output readable: test id + centered description + right-aligned status.
    if " - " in prefix:
        test_name, description = prefix.split(" - ", 1)
    else:
        test_name, description = prefix, ""

    safe_width = max(100, width)
    separators = 6  # " | " + " | "
    available = max(30, safe_width - len(status_plain) - separators)
    test_col = max(28, int(available * 0.55))
    desc_col = max(20, available - test_col)

    def _fit(value: str, target: int) -> str:
        if len(value) <= target:
            return value
        if target <= 3:
            return value[:target]
        return f"{value[: target - 3]}..."

    test_txt = _fit(test_name, test_col).ljust(test_col)
    desc_txt = _fit(description, desc_col).center(desc_col)
    return f"{test_txt} | {desc_txt} | {status_colored}{newline}"


def _is_unfinished_test_item_line(line: str) -> bool:
    """Return True for pytest item-progress lines that have no final status yet."""
    plain = _strip_ansi(line.rstrip())
    if _PYTEST_RESULT_LINE_RE.match(plain) or _PYTEST_XDIST_RESULT_LINE_RE.match(plain):
        return False
    return bool(_PYTEST_ITEM_ONLY_LINE_RE.match(plain))


def _bannerize_line(line: str, width: int) -> str | None:
    """Render selected summary lines as full-width centered banners."""
    newline = ""
    body = line
    if line.endswith("\r\n"):
        body = line[:-2]
        newline = "\r\n"
    elif line.endswith("\n"):
        body = line[:-1]
        newline = "\n"

    plain = _strip_ansi(body).strip()
    target = None
    if "generated xml file:" in plain:
        target = plain.strip("- ").strip()
    elif plain.startswith("---------- coverage:"):
        target = plain.strip("- ").strip()
    elif plain.startswith("Coverage JSON written to file "):
        target = plain

    if target is None:
        return None

    safe_width = max(60, width)
    centered = f" {target} "
    if len(centered) >= safe_width:
        return f"{centered}{newline}"

    left = (safe_width - len(centered)) // 2
    right = safe_width - len(centered) - left
    return f"{'-' * left}{centered}{'-' * right}{newline}"


def _is_xdist_preface_line(line: str) -> bool:
    """Return True for raw xdist preface lines that duplicate formatted result rows."""
    plain = _strip_ansi(line).strip()
    if not plain.startswith("tests/"):
        return False
    if "::" not in plain:
        return False
    if any(
        token in plain
        for token in ("PASSED", "FAILED", "ERROR", "SKIPPED", "XFAIL", "XPASS")
    ):
        return False
    if plain.startswith("tests collected"):
        return False
    return True


def _init_bottom_progress_line() -> tuple[int, int] | None:
    """Reserve the terminal bottom line for progress using a scroll region."""
    if not sys.stdout.isatty():
        return None
    size = shutil.get_terminal_size((120, 24))
    if size.lines < 3:
        return None
    rows = size.lines
    cols = size.columns
    sys.stdout.write(f"\033[1;{rows - 1}r")
    sys.stdout.write(f"\033[{rows};1H\033[2K")
    sys.stdout.write(_progress_bar_line(0, cols))
    sys.stdout.write(f"\033[{rows - 1};1H")
    sys.stdout.flush()
    return rows, cols


def _draw_bottom_progress(percent: int, rows: int, cols: int) -> None:
    """Update reserved bottom progress line and return cursor to output area."""
    sys.stdout.write(f"\033[{rows};1H\033[2K")
    sys.stdout.write(_progress_bar_line(percent, cols))
    sys.stdout.write(f"\033[{rows - 1};1H")
    sys.stdout.flush()


def _teardown_bottom_progress_line(final_percent: int, rows: int, cols: int) -> None:
    """Restore terminal scroll behavior and clear reserved progress line."""
    sys.stdout.write("\033[r")
    sys.stdout.write(f"\033[{rows};1H\033[2K")
    sys.stdout.write(f"\033[{rows};1H")
    sys.stdout.flush()


def _run_pytest(
    coverage_json: Path,
    junit_xml: Path,
    *,
    workers: str | None,
    live_progress: bool,
    show_output: bool,
    pytest_targets: list[str] | None = None,
) -> tuple[int, str]:
    """Run pytest with coverage and return (exit_code, captured_output)."""
    cmd = [
        "pytest",
        "--override-ini",
        "addopts=",
        "--cov=src",
        f"--cov-report=json:{coverage_json}",
        "--cov-branch",
        "--cov-fail-under=0",
        f"--junitxml={junit_xml}",
        "--color=yes",
        "-v",
    ]
    workers_normalized = (workers or "").strip().lower()
    parallel_enabled = workers_normalized not in {"", "0", "off", "none"}
    if parallel_enabled:
        cmd.extend(["-n", workers_normalized, "--dist=loadscope"])
    if pytest_targets:
        cmd.extend(pytest_targets)
    # Use a wide virtual terminal for pytest so long test ids/descriptions
    # don't hard-wrap before the trailing status token (which breaks formatting).
    env = os.environ.copy()
    cols = str(max(240, shutil.get_terminal_size((120, 24)).columns))
    env["COLUMNS"] = cols

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        bufsize=1,
    )
    assert proc.stdout is not None
    captured_lines: list[str] = []
    progress_percent = 0
    tty_cols = shutil.get_terminal_size((120, 24)).columns
    progress_state: tuple[int, int] | None = None

    if live_progress and sys.stdout.isatty():
        progress_state = _init_bottom_progress_line()

    try:
        for line in proc.stdout:
            captured_lines.append(line)
            maybe_pct = _extract_progress_percent(line)
            if maybe_pct is not None:
                progress_percent = max(progress_percent, maybe_pct)

            if show_output:
                formatted = _format_pytest_result_line(line, tty_cols)
                if formatted is not None:
                    display_line = formatted
                else:
                    stripped = _strip_trailing_progress_token(line)
                    if _is_unfinished_test_item_line(stripped):
                        if progress_state is not None:
                            _draw_bottom_progress(
                                progress_percent, progress_state[0], progress_state[1]
                            )
                        continue
                    if parallel_enabled and _is_xdist_preface_line(stripped):
                        if progress_state is not None:
                            _draw_bottom_progress(
                                progress_percent, progress_state[0], progress_state[1]
                            )
                        continue
                    banner = _bannerize_line(stripped, tty_cols)
                    display_line = banner if banner is not None else stripped
                print(display_line, end="")
            if progress_state is not None:
                _draw_bottom_progress(
                    progress_percent, progress_state[0], progress_state[1]
                )
    finally:
        proc.stdout.close()

    rc = proc.wait()
    output = "".join(captured_lines)

    if progress_state is not None:
        final_percent = 100 if rc == 0 else progress_percent
        _teardown_bottom_progress_line(
            final_percent, progress_state[0], progress_state[1]
        )

    if not show_output and rc != 0 and output.strip():
        print(output, end="" if output.endswith("\n") else "\n")
    return rc, output


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
    """Extract the top-level module name from a 'src/<module>/...' source path."""
    normalized = path.replace("\\", "/")
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
    """Strip trailing underscores from test IDs (e.g. wildcard 'test_AUTH_UC_01_*')."""
    normalized = value.rstrip("_")
    return normalized


def _extract_expected_ids(requirements_path: Path, domain: str) -> set[str]:
    """Scan a requirements markdown file for expected test_DOMAIN_UC_## IDs."""
    if not requirements_path.exists():
        return set()
    text = requirements_path.read_text(encoding="utf-8")
    pattern = re.compile(rf"\btest_{re.escape(domain)}_[A-Z0-9_]+\b")
    return {_normalize_test_id(match.group(0)) for match in pattern.finditer(text)}


def _parse_junit_test_ids(junit_xml: Path) -> tuple[set[str], set[str]]:
    """Return (seen_ids, passed_ids) parsed from junit xml."""
    if not junit_xml.exists():
        return set(), set()
    try:
        root = ET.parse(junit_xml).getroot()
    except ET.ParseError:
        return set(), set()

    seen: set[str] = set()
    passed: set[str] = set()
    pattern = re.compile(r"\btest_[A-Z0-9_]+\b")
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
    """Build per-FR progress rows comparing expected test IDs against actual results."""
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
    """Format a percentage value as a right-aligned string with two decimals."""
    return f"{value:6.2f}%"


def _coverage_status(value: float, threshold: float = 80.0) -> str:
    """Map coverage percentage to human-readable status."""
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
    """Evaluate the coverage gate and return (passed, description)."""
    if gate_mode == "none":
        return True, "gate=none (report-only)"
    if gate_mode == "global":
        ok = global_total_pct >= global_threshold
        msg = f"gate=global total={global_total_pct:.2f}% threshold={global_threshold:.2f}%"
        return ok, msg

    # gate=domain
    if not domain:
        return False, "gate=domain requires --domain"
    row = next((item for item in fr_rows if item["fr"] == domain), None)
    if row is None:
        return False, f"domain {domain} not found"
    ok = row["pass_rate"] >= min_pct
    msg = f"gate=domain {domain} pass_rate={row['pass_rate']:.2f}% threshold={min_pct:.2f}%"
    return ok, msg


def main() -> int:
    """Entry point: run tests, collect coverage, print report, and evaluate gate."""
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
    parser.add_argument(
        "--workers",
        default=os.getenv("TEST_WORKERS", "auto"),
        help=(
            "Pytest-xdist workers (default: env TEST_WORKERS or 'auto'). "
            "Use 0/off/none to disable parallel execution."
        ),
    )
    parser.add_argument(
        "--live-progress",
        action="store_true",
        default=True,
        help="Show an in-place progress bar while pytest runs (default: on).",
    )
    parser.add_argument(
        "--no-live-progress",
        action="store_false",
        dest="live_progress",
        help="Disable in-place progress bar.",
    )
    parser.add_argument(
        "--show-pytest-output",
        action="store_true",
        default=True,
        help="Print raw pytest output even when tests pass.",
    )
    parser.add_argument(
        "--no-show-pytest-output",
        action="store_false",
        dest="show_pytest_output",
        help="Suppress raw pytest output (except on failures).",
    )
    parser.add_argument(
        "--pytest-target",
        action="append",
        default=[],
        help=(
            "Optional pytest target (path/nodeid/expression). "
            "Can be passed multiple times to scope which tests run."
        ),
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        default=True,
        help="Show coverage + FR summary tables and evaluate gate (default: on).",
    )
    parser.add_argument(
        "--no-summary",
        action="store_false",
        dest="summary",
        help="Skip coverage/FR summary tables and gate evaluation.",
    )
    args = parser.parse_args()

    root = _repo_root()
    coverage_json = Path(args.coverage_json)
    if not coverage_json.is_absolute():
        coverage_json = root / coverage_json
    junit_xml = Path(args.junit_xml)
    if not junit_xml.is_absolute():
        junit_xml = root / junit_xml

    # Always run test suite first.
    pytest_rc, _pytest_output = _run_pytest(
        coverage_json,
        junit_xml,
        workers=args.workers,
        live_progress=args.live_progress,
        show_output=args.show_pytest_output,
        pytest_targets=args.pytest_target,
    )

    if not args.summary:
        if pytest_rc != 0:
            print(f"Result: pytest failed (exit={pytest_rc}).", file=sys.stderr)
            return pytest_rc
        print("\nResult: success.")
        return 0

    if not coverage_json.exists():
        print(f"\nERROR: coverage json not found at {coverage_json}", file=sys.stderr)
        return 1 if pytest_rc == 0 else pytest_rc

    coverage_data = json.loads(coverage_json.read_text(encoding="utf-8"))
    module_rows = _aggregate_module_coverage(coverage_data)
    totals = coverage_data.get("totals", {})
    total_statements = _safe_int(totals.get("num_statements"))
    total_missing = _safe_int(totals.get("missing_lines"))
    total_branches = _safe_int(totals.get("num_branches"))
    total_branch_missing = _safe_int(totals.get("missing_branches"))
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
        [
            "Path/Name",
            "Description",
            "Status",
            "Coverage %",
        ],
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
        gate_mode=args.gate,
        min_pct=args.min,
        domain=args.domain,
        global_total_pct=total_pct,
        fr_rows=fr_rows,
        global_threshold=global_threshold,
    )
    print(f"\nGate: {gate_msg}")

    if pytest_rc != 0:
        print(f"Result: pytest failed (exit={pytest_rc}).", file=sys.stderr)
        return pytest_rc
    if not gate_ok:
        print("Result: gate failed.", file=sys.stderr)
        return 1
    print("Result: success.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
