#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
log_dir="$project_root/.run/logs"
mkdir -p "$log_dir"
: >"$log_dir/backend.log"
: >"$log_dir/voice.log"
: >"$log_dir/web.log"

env_args=()
if [[ -f "$project_root/.env" ]]; then
  env_args=(--env-file "$project_root/.env")
fi

voice_command=(
  uv run "${env_args[@]}" bot.py
  -t webrtc --host 127.0.0.1 --port 7860
  --allowed-origins http://localhost:3000
)
printf -v voice_command_string '%q ' "${voice_command[@]}"

cleanup() {
  kill "${backend_pid:-}" "${voice_pid:-}" "${web_pid:-}" 2>/dev/null || true
  wait "${backend_pid:-}" "${voice_pid:-}" "${web_pid:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

(
  cd "$project_root/backend"
  uv run "${env_args[@]}" uvicorn luna_tutor.api.runtime:build_runtime_app --factory \
    --host 127.0.0.1 --port 8000 \
    --reload --reload-dir "$project_root/backend/src" \
    > >(tee -a "$log_dir/backend.log") 2>&1
) &
backend_pid=$!

(
  cd "$project_root/voice/server"
  uv run watchfiles --filter python "$voice_command_string" \
    "$project_root/voice/server" "$project_root/backend/src" \
    > >(tee -a "$log_dir/voice.log") 2>&1
) &
voice_pid=$!

(
  cd "$project_root/web"
  NEXT_PUBLIC_TUTOR_API_URL="${NEXT_PUBLIC_TUTOR_API_URL:-http://localhost:8000}" \
  NEXT_PUBLIC_PIPECAT_URL="${NEXT_PUBLIC_PIPECAT_URL:-http://localhost:7860}" \
    npm run dev \
    > >(tee -a "$log_dir/web.log") 2>&1
) &
web_pid=$!

printf 'Development logs:\n  %s\n  %s\n  %s\n' \
  "$log_dir/backend.log" "$log_dir/voice.log" "$log_dir/web.log"

wait -n "$backend_pid" "$voice_pid" "$web_pid"
