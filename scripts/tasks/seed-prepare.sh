#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

wait_for_service() {
  local profile="${1:?profile required}"
  local service="${2:?service required}"
  local timeout="${3:-90}"
  local elapsed=0
  while [ "${elapsed}" -lt "${timeout}" ]; do
    if [ "$(service_state "${profile}" "${service}")" = "healthy" ]; then
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  return 1
}

step "seed" "ensuring development db/backend services are ready"
run_compose dev up -d db backend

if ! wait_for_service dev db 90 || ! wait_for_service dev backend 90; then
  fail "development db/backend services did not become healthy in time"
  logs_tail dev
  exit 1
fi

step "seed" "applying development migrations"
run_compose dev exec -T backend python src/manage.py migrate --noinput

step "seed" "ensuring development admin bootstrap"
run_compose dev exec -T backend python src/manage.py ensure_admin

ok "development db/backend services are ready for seeding"
