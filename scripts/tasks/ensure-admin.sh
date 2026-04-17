#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

profile="${1:?profile required}"
project="$(project_name "${profile}")"
backend_container="${project}-backend-1"

step "ensure-admin" "profile=${profile} container=${backend_container}"

state="$(stack_state "${profile}")"
case "${state}" in
  running_healthy) ;;
  *)
    fail "profile=${profile} state=${state}; run task up:${profile} first"
    exit 1
    ;;
esac

env_path="$(env_file "${profile}")"
media_root="$(grep -E '^MEDIA_ROOT=' "${env_path}" | cut -d= -f2-)"
media_root="${media_root:-/app/media}"

docker exec --user root "${backend_container}" bash -c "
  mkdir -p '${media_root}/images/questions' '${media_root}/images/submissions' '${media_root}/artifacts' &&
  chown -R django:django '${media_root}'
" >/dev/null

docker exec "${backend_container}" python src/manage.py migrate --noinput >/dev/null
docker exec "${backend_container}" python src/manage.py collectstatic --noinput >/dev/null
docker exec "${backend_container}" python src/manage.py ensure_admin

ok "profile=${profile} backend initialized (migrate, collectstatic, ensure_admin, media dirs)"
