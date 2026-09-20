import pytest

from voice_config import TalkVoiceConfig


def test_configuration_reports_all_missing_provider_values():
    with pytest.raises(ValueError) as error:
        TalkVoiceConfig.from_environment({})
    assert str(error.value) == (
        "Missing required Talk configuration: SONIOX_API_KEY, SONIOX_VOICE_ID, "
        "GEMINI_API_KEY, TALK_LLM_MODEL"
    )


def test_configuration_accepts_explicit_values():
    config = TalkVoiceConfig.from_environment(
        {
            "SONIOX_API_KEY": "soniox",
            "SONIOX_VOICE_ID": "Colleen",
            "GEMINI_API_KEY": "gemini",
            "TALK_LLM_MODEL": "gemini-3.5-flash-lite",
        }
    )
    assert config.voice_id == "Colleen"
    assert config.llm_model == "gemini-3.5-flash-lite"
