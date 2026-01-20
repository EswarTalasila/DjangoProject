#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

E2E_BASE_URL=${E2E_BASE_URL:-http://eel-frontend:4200}
E2E_API_URL=${E2E_API_URL:-http://eel-backend:8000/api/v1}

export E2E_BASE_URL
export E2E_API_URL

# Ensure the frontend/backend services are up before running.

docker compose --profile e2e run --rm frontend-e2e sh -c "npm ci && npm run e2e"
