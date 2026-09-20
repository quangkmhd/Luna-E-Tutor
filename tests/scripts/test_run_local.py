from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_local_runner_starts_and_cleans_up_all_three_processes():
    script = (ROOT / "scripts/run-local.sh").read_text()
    assert "voice_pid=$!" in script
    assert 'uv run "${env_args[@]}" bot.py' in script
    assert 'NEXT_PUBLIC_PIPECAT_URL="${NEXT_PUBLIC_PIPECAT_URL:-http://localhost:7860}"' in script
    assert 'kill "${backend_pid:-}" "${voice_pid:-}" "${web_pid:-}"' in script
    assert 'wait -n "$backend_pid" "$voice_pid" "$web_pid"' in script


def test_local_runner_enables_reload_for_backend_and_voice():
    script = (ROOT / "scripts/run-local.sh").read_text()
    assert "--reload" in script
    assert "watchfiles --filter python" in script
    assert '"$project_root/voice/server" "$project_root/backend/src"' in script


def test_local_runner_keeps_separate_logs_for_all_three_services():
    script = (ROOT / "scripts/run-local.sh").read_text()
    assert 'log_dir="$project_root/.run/logs"' in script
    assert 'tee -a "$log_dir/backend.log"' in script
    assert 'tee -a "$log_dir/voice.log"' in script
    assert 'tee -a "$log_dir/web.log"' in script
