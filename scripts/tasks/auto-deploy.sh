#!/usr/bin/env bash
set -euo pipefail

TASK_SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${TASK_SCRIPT_DIR}/lib/common.sh"

usage() {
  cat <<'EOF'
usage: task auto-deploy:<on|off|status>

Manage the server-side prod auto-deploy installation.

Actions:
  on      install/update the deploy runner and /etc/cron.d entry
  off     remove the cron schedule only (leave script, key, and logs intact)
  status  report installed paths, drift, and recent deploy log lines

Optional environment overrides:
  AUTO_DEPLOY_REPO_PATH         repo checkout path on the server
  AUTO_DEPLOY_INSTALL_ROOT      install root for runner/log/key paths
  AUTO_DEPLOY_RUNNER_PATH       installed runner path
  AUTO_DEPLOY_CRON_PATH         cron file path
  AUTO_DEPLOY_LOG_PATH          deploy log path
  AUTO_DEPLOY_LOCK_PATH         deploy lock path
  AUTO_DEPLOY_DEPLOY_KEY_PATH   private deploy key path
  AUTO_DEPLOY_CRON_SCHEDULE     cron schedule expression (default: */10 * * * *)
  AUTO_DEPLOY_CRON_USER         cron execution user (default: root)
  AUTO_DEPLOY_BRANCH            git branch to deploy (default: master)
  AUTO_DEPLOY_TASK_BIN          task binary path for the installed runner

This is a server-side installation flow. When not already root it uses sudo
to write into /opt/deploy and /etc/cron.d.
EOF
}

action="${1:-}"
if [ -z "${action}" ]; then
  usage
  exit 1
fi

if [ "$#" -gt 1 ]; then
  fail "unexpected extra arguments"
  usage
  exit 1
fi

case "${action}" in
  on|off|status) ;;
  -h|--help|help)
    usage
    exit 0
    ;;
  *)
    fail "unknown action: ${action}"
    usage
    exit 1
    ;;
esac

repo_path="${AUTO_DEPLOY_REPO_PATH:-${REPO_ROOT}}"
install_root="${AUTO_DEPLOY_INSTALL_ROOT:-/opt/deploy}"
runner_path="${AUTO_DEPLOY_RUNNER_PATH:-${install_root}/auto-deploy.sh}"
cron_path="${AUTO_DEPLOY_CRON_PATH:-/etc/cron.d/eelab-auto-deploy}"
log_path="${AUTO_DEPLOY_LOG_PATH:-${install_root}/deploy.log}"
lock_path="${AUTO_DEPLOY_LOCK_PATH:-${install_root}/auto-deploy.lock}"
deploy_key_path="${AUTO_DEPLOY_DEPLOY_KEY_PATH:-${install_root}/keys/github_deploy}"
cron_schedule="${AUTO_DEPLOY_CRON_SCHEDULE:-*/10 * * * *}"
cron_user="${AUTO_DEPLOY_CRON_USER:-root}"
deploy_branch="${AUTO_DEPLOY_BRANCH:-master}"
task_bin="${AUTO_DEPLOY_TASK_BIN:-$(command -v task || true)}"
python_bin="${AUTO_DEPLOY_PYTHON_BIN:-$(command -v python3 || command -v python || true)}"
runner_template="${TASK_SCRIPT_DIR}/auto-deploy-run.sh"
cron_template="${REPO_ROOT}/Deployment/templates/eelab-auto-deploy.cron.template"

require_command() {
  if ! command -v "${1}" >/dev/null 2>&1; then
    fail "required command not found: ${1}"
    exit 1
  fi
}

require_task_bin() {
  if [ -z "${task_bin}" ]; then
    fail "task binary not found on PATH; set AUTO_DEPLOY_TASK_BIN if needed"
    exit 1
  fi
}

needs_root() {
  case "${AUTO_DEPLOY_USE_SUDO:-auto}" in
    0|false|never) return 1 ;;
  esac
  [ "$(id -u)" -ne 0 ]
}

run_root() {
  if needs_root; then
    require_command sudo
    sudo "$@"
  else
    "$@"
  fi
}

hash_file() {
  local path="${1:?path required}"
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "${path}" | awk '{print $1}'
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "${path}" | awk '{print $1}'
  else
    "${python_bin}" - "${path}" <<'PY'
from __future__ import annotations
import hashlib
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
print(hashlib.sha256(path.read_bytes()).hexdigest())
PY
  fi
}

render_template() {
  local template_path="${1:?template path required}"
  local output_path="${2:?output path required}"
  REPO_PATH="${repo_path}" \
  TASK_BIN_PATH="${task_bin}" \
  LOG_PATH="${log_path}" \
  LOCK_PATH="${lock_path}" \
  DEPLOY_KEY_PATH="${deploy_key_path}" \
  DEPLOY_BRANCH_VALUE="${deploy_branch}" \
  RUNNER_PATH="${runner_path}" \
  CRON_SCHEDULE_VALUE="${cron_schedule}" \
  CRON_USER_VALUE="${cron_user}" \
  "${python_bin}" - "${template_path}" "${output_path}" <<'PY'
from __future__ import annotations
import os
import pathlib
import sys

template_path = pathlib.Path(sys.argv[1])
output_path = pathlib.Path(sys.argv[2])
text = template_path.read_text(encoding="utf-8")
replacements = {
    "__REPO_PATH__": os.environ["REPO_PATH"],
    "__TASK_BIN__": os.environ["TASK_BIN_PATH"],
    "__LOG_PATH__": os.environ["LOG_PATH"],
    "__LOCK_PATH__": os.environ["LOCK_PATH"],
    "__DEPLOY_KEY_PATH__": os.environ["DEPLOY_KEY_PATH"],
    "__DEPLOY_BRANCH__": os.environ["DEPLOY_BRANCH_VALUE"],
    "__RUNNER_PATH__": os.environ["RUNNER_PATH"],
    "__CRON_SCHEDULE__": os.environ["CRON_SCHEDULE_VALUE"],
    "__CRON_USER__": os.environ["CRON_USER_VALUE"],
}
for needle, replacement in replacements.items():
    text = text.replace(needle, replacement)
output_path.write_text(text, encoding="utf-8")
PY
}

print_status() {
  local expected_runner=""
  local expected_hash=""
  local installed_hash=""

  if [ -x "${runner_path}" ] && [ -n "${python_bin}" ]; then
    expected_runner="$(mktemp)"
    render_template "${runner_template}" "${expected_runner}"
    expected_hash="$(hash_file "${expected_runner}")"
    installed_hash="$(hash_file "${runner_path}")"
  fi

  step "auto-deploy" "repo=${repo_path}"
  printf '  runner: %s\n' "${runner_path}"
  if [ -x "${runner_path}" ]; then
    if [ -z "${python_bin}" ]; then
      printf '    state: installed (python unavailable; drift not checked)\n'
    elif [ "${expected_hash}" = "${installed_hash}" ]; then
      printf '    state: installed (matches repo)\n'
    else
      printf '    state: installed (drift detected)\n'
      printf '    expected_sha256: %s\n' "${expected_hash}"
      printf '    installed_sha256: %s\n' "${installed_hash}"
    fi
  else
    printf '    state: missing\n'
  fi

  printf '  cron: %s\n' "${cron_path}"
  if [ -f "${cron_path}" ]; then
    printf '    state: enabled\n'
  else
    printf '    state: disabled\n'
  fi

  printf '  deploy key: %s\n' "${deploy_key_path}"
  if [ -e "${deploy_key_path}" ]; then
    printf '    state: present\n'
  else
    printf '    state: missing\n'
  fi

  printf '  log: %s\n' "${log_path}"
  if [ -f "${log_path}" ]; then
    printf '    state: present\n'
    printf '    recent entries:\n'
    tail -n 10 "${log_path}" | sed 's/^/      /'
  else
    printf '    state: missing\n'
  fi

  if [ -n "${expected_runner}" ] && [ -f "${expected_runner}" ]; then
    rm -f "${expected_runner}"
  fi
}

install_auto_deploy() {
  local tmp_runner=""
  local tmp_cron=""

  if [ -z "${python_bin}" ]; then
    fail "python3 or python is required to render install templates"
    exit 1
  fi
  require_task_bin

  if [ ! -f "${runner_template}" ]; then
    fail "runner template missing: ${runner_template}"
    exit 1
  fi
  if [ ! -f "${cron_template}" ]; then
    fail "cron template missing: ${cron_template}"
    exit 1
  fi

  if [ ! -e "${deploy_key_path}" ]; then
    fail "deploy key missing: ${deploy_key_path}"
    exit 1
  fi

  key_mode="$("${python_bin}" - "${deploy_key_path}" <<'PY'
from __future__ import annotations
import pathlib
import stat
import sys

mode = pathlib.Path(sys.argv[1]).stat().st_mode & 0o777
print(f"{mode:03o}")
PY
)"
  case "${key_mode}" in
    ???)
      if [ $((8#${key_mode} & 077)) -ne 0 ]; then
        fail "deploy key permissions must be owner-only (found ${key_mode})"
        exit 1
      fi
      ;;
  esac

  tmp_runner="$(mktemp)"
  tmp_cron="$(mktemp)"
  trap 'rm -f "${tmp_runner:-}" "${tmp_cron:-}"' EXIT

  render_template "${runner_template}" "${tmp_runner}"
  render_template "${cron_template}" "${tmp_cron}"

  run_root install -d -m 0755 "${install_root}"
  run_root install -d -m 0755 "$(dirname "${runner_path}")"
  run_root install -d -m 0755 "$(dirname "${log_path}")"
  run_root install -d -m 0755 "$(dirname "${lock_path}")"
  run_root install -d -m 0755 "$(dirname "${cron_path}")"
  run_root install -m 0755 "${tmp_runner}" "${runner_path}"
  run_root install -m 0644 "${tmp_cron}" "${cron_path}"
  run_root touch "${log_path}"
  run_root chmod 0644 "${log_path}"

  ok "installed auto-deploy runner and cron schedule"
  trap - EXIT
  rm -f "${tmp_runner}" "${tmp_cron}"
  print_status
}

disable_auto_deploy() {
  if [ -f "${cron_path}" ]; then
    run_root rm -f "${cron_path}"
    ok "removed cron schedule ${cron_path}"
  else
    warn "cron schedule not present: ${cron_path}"
  fi
  print_status
}

case "${action}" in
  on) install_auto_deploy ;;
  off) disable_auto_deploy ;;
  status) print_status ;;
esac
