from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_local_runner_starts_isolated_talk_service_and_exposes_its_url():
    script = ROOT.joinpath("scripts/run-local.sh").read_text()
    assert 'cd "$project_root/talk/server"' in script
    assert "--port 7863" in script
    assert 'tee -a "$log_dir/talk.log"' in script
    assert 'NEXT_PUBLIC_TALK_PIPECAT_URL="${NEXT_PUBLIC_TALK_PIPECAT_URL:-http://localhost:7863}"' in script
    assert '"${talk_pid:-}"' in script
    assert 'wait -n "$backend_pid" "$voice_pid" "$talk_pid" "$web_pid"' in script


def test_example_environment_names_talk_credentials_without_secret_values():
    lines = ROOT.joinpath(".env.example").read_text().splitlines()
    assert "GEMINI_API_KEY=" in lines
    assert "SONIOX_VOICE_ID=" in lines
    assert "TALK_LLM_MODEL=gemini-3.5-flash-lite" in lines
    assert "NEXT_PUBLIC_TALK_PIPECAT_URL=http://localhost:7863" in lines
