#!/usr/bin/env bash
set -euo pipefail

REPO_PATH="__REPO_PATH__"
TASK_BIN="__TASK_BIN__"
LOG_PATH="__LOG_PATH__"
LOCK_PATH="__LOCK_PATH__"
DEPLOY_KEY_PATH="__DEPLOY_KEY_PATH__"
DEPLOY_BRANCH="__DEPLOY_BRANCH__"

mkdir -p "$(dirname "${LOG_PATH}")"
touch "${LOG_PATH}"
exec >>"${LOG_PATH}" 2>&1

timestamp() {
  date -Is
}

echo "$(timestamp): auto-deploy run starting"

if command -v flock >/dev/null 2>&1; then
  exec 9>"${LOCK_PATH}"
  if ! flock -n 9; then
    echo "$(timestamp): another deploy run is active; skipping"
    exit 0
  fi
else
  lock_dir="${LOCK_PATH}.d"
  if [ -f "${lock_dir}/pid" ]; then
    stale_pid="$(cat "${lock_dir}/pid" 2>/dev/null || true)"
    if [ -n "${stale_pid}" ] && ! kill -0 "${stale_pid}" 2>/dev/null; then
      rm -rf "${lock_dir}"
    fi
  fi
  if ! mkdir "${lock_dir}" 2>/dev/null; then
    echo "$(timestamp): another deploy run is active; skipping"
    exit 0
  fi
  printf '%s\n' "$$" > "${lock_dir}/pid"
  trap 'rm -rf "${lock_dir}" >/dev/null 2>&1 || true' EXIT
fi

if [ ! -d "${REPO_PATH}" ]; then
  echo "$(timestamp): repo path missing: ${REPO_PATH}"
  exit 1
fi

if [ ! -x "${TASK_BIN}" ]; then
  echo "$(timestamp): task binary missing or not executable: ${TASK_BIN}"
  exit 1
fi

if [ ! -f "${DEPLOY_KEY_PATH}" ]; then
  echo "$(timestamp): deploy key missing: ${DEPLOY_KEY_PATH}"
  exit 1
fi

printf -v GIT_SSH_COMMAND 'ssh -i %q -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new' "${DEPLOY_KEY_PATH}"
export GIT_SSH_COMMAND

cd "${REPO_PATH}"

if [ -n "$(git status --porcelain --untracked-files=all 2>/dev/null)" ]; then
  echo "$(timestamp): repo checkout is dirty; refusing to auto-deploy"
  exit 1
fi

current_head="$(git rev-parse HEAD 2>/dev/null || echo none)"
git fetch origin "${DEPLOY_BRANCH}"
remote_head="$(git rev-parse "refs/remotes/origin/${DEPLOY_BRANCH}")"

if [ "${current_head}" = "${remote_head}" ]; then
  echo "$(timestamp): no changes on origin/${DEPLOY_BRANCH} (${remote_head})"
  exit 0
fi

echo "$(timestamp): deploying ${current_head} -> ${remote_head} from origin/${DEPLOY_BRANCH}"
git checkout -B "${DEPLOY_BRANCH}" "refs/remotes/origin/${DEPLOY_BRANCH}"
git reset --hard "${remote_head}"
if ! "${TASK_BIN}" env:init || ! "${TASK_BIN}" rebuild:prod; then
  echo "$(timestamp): deploy failed at ${remote_head}; rolling back to ${current_head}"
  git checkout -B "${DEPLOY_BRANCH}" "${current_head}"
  "${TASK_BIN}" env:init || true
  "${TASK_BIN}" rebuild:prod || true
  exit 1
fi

echo "$(timestamp): deploy complete at ${remote_head}"
