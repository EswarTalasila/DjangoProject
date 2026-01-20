#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

docker compose run --rm backend sh -c "PYTHONPATH=/app/src python /app/scripts/diagrams/generate_all.py $* && python /app/scripts/diagrams/index_diagrams.py"
