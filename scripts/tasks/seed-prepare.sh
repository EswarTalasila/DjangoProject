#!/usr/bin/env bash
set -euo pipefail

TASK_SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${TASK_SCRIPT_DIR}/lib/common.sh"

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

profile="${1:-dev}"
case "${profile}" in
  dev|test)
    ;;
  *)
    fail "invalid seed profile: ${profile} (expected dev or test)"
    exit 1
    ;;
esac

lock_dir="/tmp/eelab-seed-${profile}.lock"
if ! mkdir "${lock_dir}" 2>/dev/null; then
  fail "another seed operation is already running for profile=${profile}"
  exit 1
fi
trap 'rmdir "${lock_dir}" >/dev/null 2>&1 || true' EXIT

"${TASK_SCRIPT_DIR}/prepare-env.sh" "${profile}"
"${TASK_SCRIPT_DIR}/check-env.sh" "${profile}"
"${TASK_SCRIPT_DIR}/up.sh" proxy

step "seed" "ensuring ${profile} db/backend services are ready"
run_compose "${profile}" up -d db backend

if ! wait_for_service "${profile}" db 90 || ! wait_for_service "${profile}" backend 90; then
  fail "${profile} db/backend services did not become healthy in time"
  logs_tail "${profile}"
  exit 1
fi

step "seed" "applying ${profile} migrations"
run_compose "${profile}" exec -T backend python src/manage.py migrate --noinput

step "seed" "ensuring ${profile} admin bootstrap"
run_compose "${profile}" exec -T backend python src/manage.py ensure_admin

ok "${profile} db/backend services are ready for seeding"
