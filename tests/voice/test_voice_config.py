import sys
from pathlib import Path

import pytest
from pipecat.transcriptions.language import Language

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "voice/server"))


def test_voice_config_names_every_missing_live_variable():
    from voice_config import VoiceConfig

    with pytest.raises(
        ValueError,
        match="SONIOX_API_KEY.*SONIOX_VOICE_ID.*OPENROUTER_API_KEY.*OPENROUTER_MODEL",
    ):
        VoiceConfig.from_environment({})


def test_soniox_services_use_pipecat_settings():
    from voice_config import VoiceConfig, build_soniox_stt, build_soniox_tts

    config = VoiceConfig.from_environment(
        {
            "SONIOX_API_KEY": "secret",
            "SONIOX_VOICE_ID": "teacher-voice",
            "OPENROUTER_API_KEY": "openrouter-secret",
            "OPENROUTER_MODEL": "provider/model",
        }
    )

    stt = build_soniox_stt(config)
    tts = build_soniox_tts(config)

    assert stt._settings.model == "stt-rt-v5"
    assert set(stt._settings.language_hints) == {Language.EN, Language.VI}
    assert stt._vad_force_turn_endpoint is True
    assert tts._settings.model == "tts-rt-v2"
    assert tts._settings.voice == "teacher-voice"
    assert tts._settings.language == Language.EN
    assert tts._settings.speed == 0.8
