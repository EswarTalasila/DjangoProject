#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

ensure_proxy_certs() {
  local ssl_dir="${REPO_ROOT}/proxy/ssl"
  local cert_file="${ssl_dir}/nginx.crt"
  local key_file="${ssl_dir}/nginx.key"
  local public_host
  public_host="$(grep -E '^PUBLIC_HOST=' "${REPO_ROOT}/.env" 2>/dev/null | cut -d= -f2- || true)"
  public_host="${public_host:-localhost}"

  if [ -f "${cert_file}" ] && [ -f "${key_file}" ]; then
    return 0
  fi

  if ! command -v openssl >/dev/null 2>&1; then
    fail "openssl is required to generate proxy certificates"
    return 1
  fi

  mkdir -p "${ssl_dir}"
  step "proxy" "generating self-signed certificate for ${public_host}"
  openssl req -x509 -nodes -newkey rsa:2048 \
    -keyout "${key_file}" \
    -out "${cert_file}" \
    -days 365 \
    -subj "/CN=${public_host}" \
    -addext "subjectAltName=DNS:${public_host},DNS:localhost,IP:127.0.0.1" >/dev/null 2>&1
}

profile="${1:?profile required}"

if [ "${profile}" = "proxy" ]; then
  ensure_proxy_certs
fi

state="$(stack_state "${profile}")"
step "up" "profile=${profile} state=${state}"

case "${state}" in
  running_healthy)
    ok "profile=${profile} is already healthy"
    exit 0
    ;;
  running_unhealthy|broken)
    fail "profile=${profile} is unhealthy or broken; refusing automatic repair"
    logs_tail "${profile}"
    exit 1
    ;;
  missing|stopped|partial)
    ;;
  *)
    warn "unrecognized state ${state}; attempting non-destructive compose up"
    ;;
esac

run_compose "${profile}" up -d
if ! wait_for_stack "${profile}" 90; then
  fail "profile=${profile} did not become healthy in time"
  logs_tail "${profile}"
  exit 1
fi

ok "profile=${profile} is healthy"
