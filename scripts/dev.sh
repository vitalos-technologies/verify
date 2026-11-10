#!/usr/bin/env bash
# Start a local synthetic environment: migrate, set dev role passwords, seed, run API + worker.
set -euo pipefail
cd "$(dirname "$0")/../services/api"
set -a; [ -f ../../.env ] && . ../../.env; set +a
: "${VV_OWNER_DSN:?set VV_OWNER_DSN (see .env.example)}"
uv sync -q
uv run vv-admin migrate
uv run vv-admin dev-roles
if [ "${1:-}" = "--seed" ]; then uv run vv-admin seed-dev; fi
uv run vv-worker & WORKER=$!
trap 'kill $WORKER 2>/dev/null' EXIT
uv run vv-api
