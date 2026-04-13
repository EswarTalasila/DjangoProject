#!/usr/bin/env python3
"""Pytest test-runner with live pretty output formatting.

This module owns test orchestration for the backend: it invokes pytest,
reformats output for terminal readability, and returns the exit code.
Coverage data collection (--cov flags) happens here so that coverage_report.py
can later read the generated artifacts.

Extracted from scripts/coverage/coverage_report.py to satisfy the ownership
split: test.sh -> pytest_runner.py (test orchestration + pretty output),
then coverage_report.py (coverage + FR tables).
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# ANSI / regex constants (shared with coverage_report.py's original output)
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# ANSI / formatting helpers
# ---------------------------------------------------------------------------


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from *text*."""
    return _ANSI_RE.sub("", text)


def _progress_bar_line(percent: int, width: int) -> str:
    """Render a full-width green progress bar in the form [*****.....] [ 42%]."""
    normalized = max(0, min(100, percent))
    suffix = f" [{normalized:3d}%]"
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


_PYTEST_BANNER_RE = re.compile(r"^(=+)\s+(.*?)\s+(=+)$")


def _reformat_pytest_banner(line: str, width: int) -> str | None:
    """Reformat pytest's ``=== text ===`` banners to fit *width*."""
    newline = ""
    body = line
    if line.endswith("\r\n"):
        body = line[:-2]
        newline = "\r\n"
    elif line.endswith("\n"):
        body = line[:-1]
        newline = "\n"

    plain = _strip_ansi(body)
    match = _PYTEST_BANNER_RE.match(plain)
    if match is None:
        return None

    text = match.group(2)
    safe_width = max(40, width)
    inner = f" {text} "
    if len(inner) + 2 >= safe_width:
        return f"={inner}={newline}"
    left = (safe_width - len(inner)) // 2
    right = safe_width - len(inner) - left
    color = ""
    reset = ""
    if "\033[" in body:
        if "passed" in text or "passed" in body:
            color, reset = "\033[32m", "\033[0m"
        elif "failed" in text.lower() or "error" in text.lower():
            color, reset = "\033[31m", "\033[0m"
        elif "warning" in text.lower():
            color, reset = "\033[33m", "\033[0m"
    return f"{color}{'=' * left}{inner}{'=' * right}{reset}{newline}"


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


# ---------------------------------------------------------------------------
# Terminal progress bar (bottom-of-screen)
# ---------------------------------------------------------------------------


def _tty_size() -> tuple[int, int]:
    """Return current (rows, cols) from the terminal, re-queried each call."""
    size = shutil.get_terminal_size((120, 24))
    return size.lines, size.columns


def _init_bottom_progress_line() -> bool:
    """Reserve the terminal bottom line for progress using a scroll region."""
    if not sys.stdout.isatty():
        return False
    rows, cols = _tty_size()
    if rows < 3:
        return False
    sys.stdout.write(f"\033[1;{rows - 1}r")
    sys.stdout.write(f"\033[{rows};1H\033[2K")
    sys.stdout.write(_progress_bar_line(0, cols))
    sys.stdout.write(f"\033[{rows - 1};1H")
    sys.stdout.flush()
    return True


def _draw_bottom_progress(percent: int) -> None:
    """Update reserved bottom progress line, adapting to current terminal size."""
    rows, cols = _tty_size()
    if rows < 3:
        return
    sys.stdout.write(f"\033[1;{rows - 1}r")
    sys.stdout.write(f"\033[{rows};1H\033[2K")
    sys.stdout.write(_progress_bar_line(percent, cols))
    sys.stdout.write(f"\033[{rows - 1};1H")
    sys.stdout.flush()


def _teardown_bottom_progress_line() -> None:
    """Restore terminal scroll behavior and clear reserved progress line."""
    rows, _ = _tty_size()
    sys.stdout.write("\033[r")
    sys.stdout.write(f"\033[{rows};1H\033[2K")
    sys.stdout.write(f"\033[{rows};1H")
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# Django readiness check
# ---------------------------------------------------------------------------


def _wait_for_django_ready(timeout_seconds: int = 45) -> tuple[bool, str]:
    """Wait until Django checks succeed before running pytest."""
    deadline = time.monotonic() + max(1, timeout_seconds)
    profile = (os.getenv("ENVIRONMENT") or "development").strip() or "development"
    last_error = ""

    while time.monotonic() < deadline:
        check_cmd = ["python", "src/manage.py", "check"]
        check_proc = subprocess.run(
            check_cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        if check_proc.returncode == 0:
            if profile == "testing":
                env_proc = subprocess.run(
                    [
                        "python",
                        "src/manage.py",
                        "env_report",
                        "--profile",
                        "testing",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if env_proc.returncode == 0:
                    return True, ""
                last_error = (env_proc.stderr or env_proc.stdout).strip()
            else:
                return True, ""
        else:
            last_error = (check_proc.stderr or check_proc.stdout).strip()
        time.sleep(1)

    return False, last_error


# ---------------------------------------------------------------------------
# Pytest invocation with live formatted output
# ---------------------------------------------------------------------------


def _run_pytest(
    coverage_json: Path,
    junit_xml: Path,
    *,
    workers: str | None,
    live_progress: bool,
    show_output: bool,
    pytest_targets: list[str] | None = None,
) -> int:
    """Run pytest with coverage and return exit code.

    This is the extracted test-orchestration function.  It runs pytest
    directly, streams formatted output to the terminal, and returns
    the pytest exit code.  Coverage data is collected via --cov flags
    so that coverage_report.py can later read the artifacts.
    """
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

    progress_active = False

    if live_progress and sys.stdout.isatty():
        progress_active = _init_bottom_progress_line()

    try:
        for line in proc.stdout:
            captured_lines.append(line)
            maybe_pct = _extract_progress_percent(line)
            if maybe_pct is not None:
                progress_percent = max(progress_percent, maybe_pct)

            cols_int = _tty_size()[1]

            if show_output:
                pytest_banner = _reformat_pytest_banner(line, cols_int)
                if pytest_banner is not None:
                    print(pytest_banner, end="")
                    if progress_active:
                        _draw_bottom_progress(progress_percent)
                    continue

                formatted = _format_pytest_result_line(line, cols_int)
                if formatted is not None:
                    display_line = formatted
                else:
                    stripped = _strip_trailing_progress_token(line)
                    if _is_unfinished_test_item_line(stripped):
                        if progress_active:
                            _draw_bottom_progress(progress_percent)
                        continue
                    if parallel_enabled and _is_xdist_preface_line(stripped):
                        if progress_active:
                            _draw_bottom_progress(progress_percent)
                        continue
                    banner = _bannerize_line(stripped, cols_int)
                    display_line = banner if banner is not None else stripped
                print(display_line, end="")
            if progress_active:
                _draw_bottom_progress(progress_percent)
    finally:
        proc.stdout.close()

    rc = proc.wait()
    output = "".join(captured_lines)

    if progress_active:
        _teardown_bottom_progress_line()

    if not show_output and rc != 0 and output.strip():
        print(output, end="" if output.endswith("\n") else "\n")
    return rc


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _repo_root() -> Path:
    """Return the repository root directory (three levels up from this script in lib/)."""
    return Path(__file__).resolve().parents[3]


def main() -> int:
    """Entry point: check Django readiness, run pytest with formatted output."""
    parser = argparse.ArgumentParser(
        description="Run backend pytest suite with pretty formatted output."
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
        help="Print formatted pytest output (default: on).",
    )
    parser.add_argument(
        "--no-show-pytest-output",
        action="store_false",
        dest="show_pytest_output",
        help="Suppress formatted pytest output (except on failures).",
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

    args = parser.parse_args()

    # Django readiness gate
    ready, startup_error = _wait_for_django_ready()
    if not ready:
        print(
            "ERROR: backend Django app is not ready; aborting test run.",
            file=sys.stderr,
        )
        if startup_error:
            print(startup_error, file=sys.stderr)
        print(
            "Hint: run 'task up:test' and wait for profile diagnostics to pass.",
            file=sys.stderr,
        )
        return 2

    root = _repo_root()
    coverage_json = Path(args.coverage_json)
    if not coverage_json.is_absolute():
        coverage_json = root / coverage_json
    junit_xml = Path(args.junit_xml)
    if not junit_xml.is_absolute():
        junit_xml = root / junit_xml

    return _run_pytest(
        coverage_json,
        junit_xml,
        workers=args.workers,
        live_progress=args.live_progress,
        show_output=args.show_pytest_output,
        pytest_targets=args.pytest_target or None,
    )


if __name__ == "__main__":
    raise SystemExit(main())
