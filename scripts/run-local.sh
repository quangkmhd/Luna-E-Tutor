#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_args=()
if [[ -f "$project_root/.env" ]]; then
  env_args=(--env-file "$project_root/.env")
fi

cleanup() {
  kill "${backend_pid:-}" "${web_pid:-}" 2>/dev/null || true
  wait "${backend_pid:-}" "${web_pid:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

(
  cd "$project_root/backend"
  uv run uvicorn luna_tutor.api.runtime:build_runtime_app --factory \
    --host 127.0.0.1 --port 8000 "${env_args[@]}"
) &
backend_pid=$!

(
  cd "$project_root/web"
  NEXT_PUBLIC_TUTOR_API_URL="${NEXT_PUBLIC_TUTOR_API_URL:-http://localhost:8000}" npm run dev
) &
web_pid=$!

wait -n "$backend_pid" "$web_pid"
