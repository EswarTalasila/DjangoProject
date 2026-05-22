#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

if ! docker info >/dev/null 2>&1; then
  fail "Docker is not running. Start Docker before running Lattice tasks."
  exit 1
fi

warn "destroy:all will remove all Lattice containers, volumes, and proxy state"
printf "Are you sure? [y/N]: "
read -r confirmation

case "${confirmation}" in
  y|Y|yes|YES)
    ;;
  *)
    fail "destroy:all cancelled at y/N confirmation"
    exit 1
    ;;
esac

printf "Type Lattice to continue: "
read -r final_confirmation

if [ "${final_confirmation}" != "Lattice" ]; then
  fail "destroy:all cancelled; confirmation phrase did not match Lattice"
  exit 1
fi

step "destroy" "wiping all Lattice stacks and named volumes"
for profile in dev test prod proxy; do
  run_compose "${profile}" down -v --remove-orphans || true
done
docker network rm lattice-proxy >/dev/null 2>&1 || true
ok "all Lattice docker state has been removed"
