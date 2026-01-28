#!/usr/bin/env bash
set -euo pipefail

USE_DOCKER=${E2E_USE_DOCKER:-true}

env_args=()
for var in \
  E2E_ADMIN_USERNAME \
  E2E_ADMIN_PASSWORD \
  E2E_ADMIN_NAME \
  E2E_TEACHER_USERNAME \
  E2E_TEACHER_PASSWORD \
  E2E_STUDENT_USERNAME \
  E2E_STUDENT_PASSWORD \
  ADMIN_EMAIL \
  ADMIN_PASSWORD \
  ADMIN_USERNAME; do
  if [[ -n "${!var-}" ]]; then
    env_args+=("-e" "${var}=${!var}")
  fi
done

if [[ "$USE_DOCKER" == "true" ]]; then
  docker compose exec "${env_args[@]}" backend python src/manage.py seed_e2e "$@"
else
  (cd backend && python src/manage.py seed_e2e "$@")
fi
