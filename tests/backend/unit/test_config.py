import pytest

from luna_tutor.config import Settings


def test_settings_requires_openrouter_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        Settings.from_env()


def test_settings_pins_model(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    settings = Settings.from_env()

    assert settings.openrouter_model == "google/gemini-3.5-flash-lite"
