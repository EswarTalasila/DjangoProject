#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASKS_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd -- "${TASKS_DIR}/../.." && pwd)"

if [ -n "${FORCE_COLOR:-}" ] || { [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; }; then
  C_RESET="$(printf '\033[0m')"
  C_BLUE="$(printf '\033[34m')"
  C_GREEN="$(printf '\033[32m')"
  C_YELLOW="$(printf '\033[33m')"
  C_RED="$(printf '\033[31m')"
else
  C_RESET=""
  C_BLUE=""
  C_GREEN=""
  C_YELLOW=""
  C_RED=""
fi

step() {
  printf "%s[%s]%s %s\n" "${C_BLUE}" "$1" "${C_RESET}" "$2"
}

ok() {
  printf "%s[ok]%s %s\n" "${C_GREEN}" "${C_RESET}" "$1"
}

warn() {
  printf "%s[warn]%s %s\n" "${C_YELLOW}" "${C_RESET}" "$1"
}

fail() {
  printf "%s[error]%s %s\n" "${C_RED}" "${C_RESET}" "$1" >&2
}

project_name() {
  case "${1:?profile required}" in
    proxy) echo "lattice-proxy" ;;
    dev) echo "lattice-dev" ;;
    test) echo "lattice-test" ;;
    prod) echo "lattice-prod" ;;
    *) fail "unknown profile: $1"; return 1 ;;
  esac
}

compose_file() {
  case "${1:?profile required}" in
    proxy) echo "${REPO_ROOT}/docker/compose.proxy.yml" ;;
    dev) echo "${REPO_ROOT}/docker/compose.dev.yml" ;;
    test) echo "${REPO_ROOT}/docker/compose.test.yml" ;;
    prod) echo "${REPO_ROOT}/docker/compose.prod.yml" ;;
    *) fail "unknown profile: $1"; return 1 ;;
  esac
}

env_file() {
  case "${1:?profile required}" in
    proxy) echo "${REPO_ROOT}/.env" ;;
    dev) echo "${REPO_ROOT}/env/.env.development" ;;
    test) echo "${REPO_ROOT}/env/.env.testing" ;;
    prod) echo "${REPO_ROOT}/env/.env.production" ;;
    *) fail "unknown profile: $1"; return 1 ;;
  esac
}

run_compose() {
  local profile="${1:?profile required}"
  shift
  (
    cd "${REPO_ROOT}"
    docker compose \
      -p "$(project_name "${profile}")" \
      --env-file "$(env_file "${profile}")" \
      -f "$(compose_file "${profile}")" \
      "$@"
  )
}

required_services() {
  case "${1:?profile required}" in
    proxy) printf '%s\n' proxy ;;
    dev|test|prod) printf '%s\n' db backend frontend ;;
    *) fail "unknown profile: $1"; return 1 ;;
  esac
}

container_id() {
  local profile="${1:?profile required}"
  local service="${2:?service required}"
  run_compose "${profile}" ps -a -q "${service}" 2>/dev/null | head -n 1
}

service_state() {
  local profile="${1:?profile required}"
  local service="${2:?service required}"
  local cid
  cid="$(container_id "${profile}" "${service}")"
  if [ -z "${cid}" ]; then
    echo "missing"
    return 0
  fi

  local raw_state
  raw_state="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${cid}" 2>/dev/null || true)"
  case "${raw_state}" in
    healthy|running) echo "healthy" ;;
    starting|created|restarting) echo "starting" ;;
    exited|dead) echo "stopped" ;;
    unhealthy) echo "unhealthy" ;;
    *) echo "${raw_state:-unknown}" ;;
  esac
}

stack_state() {
  local profile="${1:?profile required}"
  local total=0
  local missing=0
  local healthy=0
  local stopped=0
  local starting=0
  local unhealthy=0
  local other=0
  local service
  while IFS= read -r service; do
    total=$((total + 1))
    case "$(service_state "${profile}" "${service}")" in
      missing) missing=$((missing + 1)) ;;
      healthy) healthy=$((healthy + 1)) ;;
      stopped) stopped=$((stopped + 1)) ;;
      starting) starting=$((starting + 1)) ;;
      unhealthy) unhealthy=$((unhealthy + 1)) ;;
      *) other=$((other + 1)) ;;
    esac
  done < <(required_services "${profile}")

  if [ "${missing}" -eq "${total}" ]; then
    echo "missing"
  elif [ "${healthy}" -eq "${total}" ]; then
    echo "running_healthy"
  elif [ "${stopped}" -eq "${total}" ] || { [ "${stopped}" -gt 0 ] && [ $((stopped + missing)) -eq "${total}" ]; }; then
    echo "stopped"
  elif [ "${unhealthy}" -gt 0 ] || [ "${other}" -gt 0 ]; then
    echo "broken"
  elif [ "${starting}" -gt 0 ]; then
    echo "running_unhealthy"
  else
    echo "partial"
  fi
}

wait_for_stack() {
  local profile="${1:?profile required}"
  local timeout="${2:-60}"
  local elapsed=0
  while [ "${elapsed}" -lt "${timeout}" ]; do
    local ready=1
    local service
    while IFS= read -r service; do
      if [ "$(service_state "${profile}" "${service}")" != "healthy" ]; then
        ready=0
      fi
    done < <(required_services "${profile}")
    if [ "${ready}" -eq 1 ]; then
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  return 1
}

logs_tail() {
  local profile="${1:?profile required}"
  run_compose "${profile}" logs --tail 80 || true
}
