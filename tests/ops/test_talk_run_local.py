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
    assert "OPENROUTER_API_KEY=" in lines
    assert "OPENROUTER_MODEL=google/gemini-3.5-flash-lite" in lines
    assert any(line.startswith("SONIOX_VOICE_ID=") for line in lines)
    assert not any(line.startswith("TALK_LLM_MODEL=") for line in lines)
    assert "NEXT_PUBLIC_TALK_PIPECAT_URL=http://localhost:7863" in lines


def test_talk_runtime_uses_the_openrouter_pipecat_service():
    source = ROOT.joinpath("talk/server/bot.py").read_text()
    project = ROOT.joinpath("talk/server/pyproject.toml").read_text()
    assert "from pipecat.services.openrouter.llm import OpenRouterLLMService" in source
    assert "OpenRouterLLMService(" in source
    assert "GoogleLLMService" not in source
    assert "openrouter" in project


def test_voice_runtimes_load_only_the_root_environment_file():
    for relative_path in ("talk/server/bot.py", "voice/server/bot.py"):
        source = ROOT.joinpath(relative_path).read_text()
        assert 'PROJECT_ROOT = Path(__file__).resolve().parents[2]' in source
        assert 'load_dotenv(PROJECT_ROOT / ".env", override=True)' in source

    assert not ROOT.joinpath("talk/server/.env").exists()
    assert not ROOT.joinpath("voice/server/.env").exists()
    assert not ROOT.joinpath("backend/.env").exists()
