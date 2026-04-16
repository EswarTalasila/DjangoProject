#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

usage() {
  cat <<'EOF'
usage: task seed:data

Seed the deterministic demo dataset in the development stack.
This provisions known accounts first and then seeds courses, templates,
assignments, and submissions through the Django management command.
EOF
}

if [ "$#" -gt 0 ]; then
  case "${1}" in
    -h|--help|help)
      usage
      exit 0
      ;;
  esac
  fail "task seed:data does not accept extra arguments"
  usage
  exit 1
fi

step "seed" "seeding deterministic demo data in the development stack"
run_compose dev exec -T backend python src/manage.py seed_demo_data
ok "seeded demo data"
