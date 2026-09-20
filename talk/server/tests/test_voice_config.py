import pytest

from voice_config import TalkVoiceConfig


def test_configuration_reports_all_missing_provider_values():
    with pytest.raises(ValueError) as error:
        TalkVoiceConfig.from_environment({})
    assert str(error.value) == (
        "Missing required Talk configuration: SONIOX_API_KEY, SONIOX_VOICE_ID, "
        "OPENROUTER_API_KEY, OPENROUTER_MODEL"
    )


def test_configuration_accepts_explicit_values():
    config = TalkVoiceConfig.from_environment(
        {
            "SONIOX_API_KEY": "soniox",
            "SONIOX_VOICE_ID": "Colleen",
            "OPENROUTER_API_KEY": "openrouter",
            "OPENROUTER_MODEL": "google/gemini-3.5-flash-lite",
        }
    )
    assert config.voice_id == "Colleen"
    assert config.openrouter_api_key == "openrouter"
    assert config.llm_model == "google/gemini-3.5-flash-lite"
