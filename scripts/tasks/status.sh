#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

profile="${1:?profile required}"
printf "[status] profile=%s state=%s\n" "${profile}" "$(stack_state "${profile}")"
while IFS= read -r service; do
  printf "  %-10s %s\n" "${service}" "$(service_state "${profile}" "${service}")"
done < <(required_services "${profile}")
