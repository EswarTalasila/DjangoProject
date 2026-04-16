#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

usage() {
  cat <<'EOF'
usage: task seed:account -- <all|researcher|teacher|student>

Provision deterministic role accounts in the development stack.
The command always resets seeded passwords to their known deterministic values.
EOF
}

if [ "$#" -ne 1 ] || [ -z "${1:-}" ]; then
  usage
  exit 1
fi

role="${1}"
case "${role}" in
  all|researcher|teacher|student)
    ;;
  -h|--help|help)
    usage
    exit 0
    ;;
  *)
    fail "invalid role: ${role}"
    usage
    exit 1
    ;;
esac

step "seed" "provisioning role=${role} in the development stack"
run_compose dev exec -T backend python src/manage.py provision_account --role "${role}" --force-password
ok "seeded role=${role}"
