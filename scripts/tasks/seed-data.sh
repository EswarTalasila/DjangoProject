#!/usr/bin/env bash
set -euo pipefail

TASK_SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${TASK_SCRIPT_DIR}/lib/common.sh"

usage() {
  cat <<'EOF'
usage: task seed:data -- [--profile dev|test]

Seed the deterministic demo dataset in the selected backend profile.
This provisions known accounts first and then seeds courses, templates,
assignments, and submissions through the Django management command.
EOF
}

profile="dev"

while [ "$#" -gt 0 ]; do
  case "${1}" in
    --profile)
      if [ "$#" -lt 2 ]; then
        fail "--profile requires a value"
        usage
        exit 1
      fi
      profile="${2}"
      shift 2
      ;;
    -h|--help|help)
      usage
      exit 0
      ;;
    *)
      fail "task seed:data does not accept extra arguments"
      usage
      exit 1
      ;;
  esac
done

case "${profile}" in
  dev|test)
    ;;
  *)
    fail "invalid profile: ${profile}"
    usage
    exit 1
    ;;
esac

"${TASK_SCRIPT_DIR}/seed-prepare.sh" "${profile}"

step "seed" "seeding deterministic demo data in profile=${profile}"
run_compose "${profile}" exec -T backend python src/manage.py seed_demo_data
ok "seeded demo data profile=${profile}"
