#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

profile="${1:?profile required}"
step "rebuild" "profile=${profile}"
run_compose "${profile}" up -d --build --force-recreate
if ! wait_for_stack "${profile}" 120; then
  fail "profile=${profile} did not become healthy after rebuild"
  logs_tail "${profile}"
  exit 1
fi
ok "profile=${profile} rebuilt without removing persistent data"
