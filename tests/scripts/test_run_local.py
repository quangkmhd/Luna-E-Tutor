from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_local_runner_starts_and_cleans_up_all_three_processes():
    script = (ROOT / "scripts/run-local.sh").read_text()
    assert "voice_pid=$!" in script
    assert 'uv run "${env_args[@]}" bot.py' in script
    assert 'NEXT_PUBLIC_PIPECAT_URL="${NEXT_PUBLIC_PIPECAT_URL:-http://localhost:7860}"' in script
    assert 'kill "${backend_pid:-}" "${voice_pid:-}" "${web_pid:-}"' in script
    assert 'wait -n "$backend_pid" "$voice_pid" "$web_pid"' in script
