#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

COMPOSE_CMD=(docker compose)

"${COMPOSE_CMD[@]}" run --rm backend sh -c "ruff check /app/src /app/tests && black --check /app/src /app/tests && mypy /app/src && python /app/scripts/lint/check_docstrings.py --root /app/src"
