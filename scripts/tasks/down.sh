#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

profile="${1:?profile required}"
state="$(stack_state "${profile}")"
step "down" "profile=${profile} state=${state}"

if [ "${state}" = "missing" ]; then
  ok "profile=${profile} has no managed containers"
  exit 0
fi

run_compose "${profile}" down --remove-orphans
ok "profile=${profile} stopped without removing volumes"
