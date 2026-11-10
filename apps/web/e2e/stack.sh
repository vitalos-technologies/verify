#!/usr/bin/env bash
# Starts an isolated synthetic stack for browser tests: fresh vv_e2e schema, seed, worker, API on :8100.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
api="$here/../../../services/api"
export VV_ENV=test VV_DEV_EXPOSE_CODES=1
export VV_OWNER_DSN="${VV_E2E_OWNER_DSN:-postgresql://vv_owner:vv_owner_local@localhost:5432/vv_e2e}"
export VV_APP_DSN="${VV_E2E_APP_DSN:-postgresql://vv_app:vv_app_local@localhost:5432/vv_e2e}"
export VV_WORKER_DSN="${VV_E2E_WORKER_DSN:-postgresql://vv_worker:vv_worker_local@localhost:5432/vv_e2e}"
export VV_HOSTED_BASE_URL="http://localhost:3100" VV_CONSOLE_BASE_URL="http://localhost:3100"
cd "$api"
psql "$VV_OWNER_DSN" -q -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;"
uv run -q vv-admin migrate >/dev/null
uv run -q vv-admin dev-roles >/dev/null
mkdir -p "$here/.state"
uv run -q vv-admin seed-dev > "$here/.state/seed.json"
uv run -q vv-worker > "$here/.state/worker.log" 2>&1 &
worker=$!
trap 'kill $worker 2>/dev/null || true' EXIT
uv run -q uvicorn --factory vv.api.app:create_app --port 8100 --no-access-log
