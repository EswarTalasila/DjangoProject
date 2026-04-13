#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

if ! docker info >/dev/null 2>&1; then
  fail "Docker is not running. Start Docker before running EElab tasks."
  exit 1
fi

if [ "${CONFIRM_DESTROY_EELAB:-}" != "EELAB" ]; then
  fail "refusing destroy:all without CONFIRM_DESTROY_EELAB=EELAB"
  exit 1
fi

step "destroy" "wiping all EElab stacks and named volumes"
for profile in dev test prod proxy; do
  run_compose "${profile}" down -v --remove-orphans || true
done
docker network rm eelab-proxy >/dev/null 2>&1 || true
ok "all EElab docker state has been removed"
