import pytest
from luna_tutor.api import runtime
from luna_tutor.api.runtime import FixtureTurnService
from luna_tutor.storage.session_repository import SessionRepository


def test_fixture_components_are_deterministic_and_have_repository(tmp_path):
    components = runtime.build_runtime_components(
        {
            "ENV": "test",
            "TUTOR_LLM_MODE": "fixture",
            "TUTOR_DATABASE_PATH": str(tmp_path / "voice.sqlite3"),
        }
    )

    assert isinstance(components.repository, SessionRepository)
    assert isinstance(components.turn_service, FixtureTurnService)
    assert components.client is None


def test_live_components_require_openrouter_configuration(tmp_path):
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        runtime.build_runtime_components(
            {"TUTOR_DATABASE_PATH": str(tmp_path / "voice.sqlite3")}
        )
