#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

target="${1:-all}"

run_backend() {
  # -----------------------------------------------------------------------
  # Step 1: test orchestration — run pytest with pretty formatted output.
  # pytest_runner.py owns the pytest invocation and live terminal formatting.
  # Coverage data (coverage.json, coverage.junit.xml) is collected via
  # --cov flags during the test run so that the report step can read them.
  # -----------------------------------------------------------------------
  step "test" "running backend test suite"
  local pytest_rc=0
  run_compose test exec -T backend \
    python /app/scripts/tasks/lib/pytest_runner.py || pytest_rc=$?

  # -----------------------------------------------------------------------
  # Step 2: coverage report — read the artifacts and print summary tables.
  # coverage_report.py reads coverage.json and coverage.junit.xml, then
  # prints the coverage breakdown table and FR test-ID progress table.
  # It does NOT re-run pytest.
  # -----------------------------------------------------------------------
  step "test" "generating coverage and FR progress report"
  run_compose test exec -T backend \
    python /app/scripts/coverage/coverage_report.py || true

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
