#!/usr/bin/env bash
set -euo pipefail

TASK_SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${TASK_SCRIPT_DIR}/lib/common.sh"

usage() {
  cat <<'EOF'
usage: task seed:account -- <all|researcher|teacher|student> [--profile dev|test]

Provision deterministic role accounts in the selected backend profile.
The command always resets seeded passwords to their known deterministic values.
EOF
}

profile="dev"
role=""

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
      if [ -n "${role}" ]; then
        fail "unexpected extra argument: ${1}"
        usage
        exit 1
      fi
      role="${1}"
      shift
      ;;
  esac
done

if [ -z "${role}" ]; then
  usage
  exit 1
fi

case "${role}" in
  all|researcher|teacher|student)
    ;;
  *)
    fail "invalid role: ${role}"
    usage
    exit 1
    ;;
esac

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

step "seed" "provisioning role=${role} in profile=${profile}"
run_compose "${profile}" exec -T backend python src/manage.py provision_account --role "${role}" --force-password
ok "seeded role=${role} profile=${profile}"
