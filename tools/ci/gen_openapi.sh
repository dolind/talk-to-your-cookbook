#!/usr/bin/env bash
set -euo pipefail

PORT=8000
OUTPUT_JSON="docs/openapi.json"
OUTPUT_HTML="docs/openapi.html"
APP_DIR="backend"

mkdir -p "docs"


PYTHONPATH="${APP_DIR}" uvicorn backend.app.main:app \
  --host 0.0.0.0 \
  --port ${PORT} \
  --lifespan off \
  --log-level info &
UVICORN_PID=$!

cleanup() {
  kill "${UVICORN_PID}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 8
curl -fsSL "http://127.0.0.1:${PORT}/api/v1/openapi.json" -o "${OUTPUT_JSON}"
npx --yes @redocly/cli build-docs "${OUTPUT_JSON}" --output="${OUTPUT_HTML}"

cd frontend
# Generate TypeScript types
echo "Generating TypeScript types..."
npm run generate-types
