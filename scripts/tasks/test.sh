#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

target="${1:-all}"

terminal_cols() {
  if [ -r /dev/tty ] && command -v stty >/dev/null 2>&1; then
    local size
    size="$(stty size < /dev/tty 2>/dev/null || true)"
    if [ -n "${size}" ]; then
      printf '%s\n' "${size##* }"
      return 0
    fi
  fi
  if [ -n "${COLUMNS:-}" ]; then
    printf '%s\n' "${COLUMNS}"
    return 0
  fi
  if [ -t 1 ] && command -v tput >/dev/null 2>&1; then
    tput cols 2>/dev/null && return 0
  fi
  printf '%s\n' "120"
}

terminal_lines() {
  if [ -r /dev/tty ] && command -v stty >/dev/null 2>&1; then
    local size
    size="$(stty size < /dev/tty 2>/dev/null || true)"
    if [ -n "${size}" ]; then
      printf '%s\n' "${size%% *}"
      return 0
    fi
  fi
  if [ -n "${LINES:-}" ]; then
    printf '%s\n' "${LINES}"
    return 0
  fi
  if [ -t 1 ] && command -v tput >/dev/null 2>&1; then
    tput lines 2>/dev/null && return 0
  fi
  printf '%s\n' "24"
}

run_backend() {
  # -----------------------------------------------------------------------
  # Step 1: test orchestration — run pytest with pretty formatted output.
  # pytest_runner.py owns the pytest invocation and live terminal formatting.
  # Coverage data (coverage.json, coverage.junit.xml) is collected via
  # --cov flags during the test run so that the report step can read them.
  # -----------------------------------------------------------------------
  step "test" "running backend test suite"
  local pytest_rc=0
  local cols lines
  cols="$(terminal_cols)"
  lines="$(terminal_lines)"
  run_compose test exec -T \
    -e "EELAB_TERM_COLUMNS=${cols}" \
    -e "EELAB_TERM_LINES=${lines}" \
    -e "COLUMNS=${cols}" \
    -e "LINES=${lines}" \
    backend \
    python /app/scripts/tasks/lib/pytest_runner.py || pytest_rc=$?

  # -----------------------------------------------------------------------
  # Step 2: coverage report — read the artifacts and print summary tables.
  # coverage_report.py reads coverage.json and coverage.junit.xml, then
  # prints the coverage breakdown table and FR test-ID progress table.
  # It does NOT re-run pytest.
  # -----------------------------------------------------------------------
  step "test" "generating coverage and FR progress report"
  run_compose test exec -T \
    -e "EELAB_TERM_COLUMNS=${cols}" \
    -e "EELAB_TERM_LINES=${lines}" \
    -e "COLUMNS=${cols}" \
    -e "LINES=${lines}" \
    backend \
    python /app/scripts/coverage/coverage_report.py || true

  # -----------------------------------------------------------------------
  # Step 3: docstring check — warn about test methods missing docstrings.
  # These docstrings populate the description column in the test output
  # table above. Missing docstrings produce empty description cells.
  # This step is advisory (|| true) — it does not fail the test run.
  # -----------------------------------------------------------------------
  step "test" "checking test docstrings"
  run_compose test exec -T backend \
    python /app/scripts/coverage/check_test_docstrings.py || true

  # Propagate the pytest exit code so the task fails on test failures.
  return "${pytest_rc}"
}

run_frontend() {
  step "test" "running frontend unit/integration suite with coverage"
  run_compose test exec -T frontend npm run test:coverage
}

case "${target}" in
  backend)
    run_backend
    ;;
  frontend)
    run_frontend
    ;;
  all)
    run_backend
    run_frontend
    ;;
  *)
    fail "unknown test target: ${target}"
    exit 1
    ;;
esac
