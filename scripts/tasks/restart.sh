#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

profile="${1:?profile required}"
state="$(stack_state "${profile}")"
step "restart" "profile=${profile} state=${state}"

if [ "${state}" = "missing" ]; then
  warn "profile=${profile} is missing; run task up:${profile} instead"
  exit 0
fi

run_compose "${profile}" restart
if ! wait_for_stack "${profile}" 90; then
  fail "profile=${profile} did not become healthy after restart"
  logs_tail "${profile}"
  exit 1
fi

ok "profile=${profile} restarted cleanly"
