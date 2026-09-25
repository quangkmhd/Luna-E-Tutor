import sys
from pathlib import Path

import pytest
from pipecat.transcriptions.language import Language

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "voice/server"))


def test_voice_config_names_every_missing_live_variable():
    from voice_config import VoiceConfig

    with pytest.raises(
        ValueError,
        match="SONIOX_API_KEY.*SONIOX_VOICE_ID",
    ):
        VoiceConfig.from_environment({})


def test_soniox_services_use_pipecat_settings():
    from voice_config import VoiceConfig, build_soniox_stt, build_soniox_tts

    config = VoiceConfig.from_environment(
        {
            "SONIOX_API_KEY": "secret",
            "SONIOX_VOICE_ID": "teacher-voice",
        }
    )

    stt = build_soniox_stt(config)
    tts = build_soniox_tts(config)

    assert stt._settings.model == "stt-rt-v5"
    assert set(stt._settings.language_hints) == {Language.EN, Language.VI}
    assert stt._vad_force_turn_endpoint is True
    assert stt._settings.context == 'Grade 3 English lesson'
    assert tts._settings.model == "tts-rt-v2"
    assert tts._settings.voice == "teacher-voice"
    assert tts._settings.language == Language.VI
    assert tts._settings.speed == 1.0


def test_google_tts_config_uses_credentials_region_and_bilingual_voices(tmp_path, monkeypatch):
    from voice_config import VoiceConfig, build_tts

    credentials = tmp_path / 'gg.json'
    credentials.write_text('{}')
    environment = {
        'SONIOX_API_KEY': 'stt-secret',
        'TTS_PROVIDER': 'google',
        'GOOGLE_APPLICATION_CREDENTIALS': str(credentials),
        'GOOGLE_TTS_LOCATION': 'asia-southeast1',
        'GOOGLE_TTS_EN_VOICE': 'en-US-Chirp3-HD-Zephyr',
        'GOOGLE_TTS_VI_VOICE': 'vi-VN-Chirp3-HD-Zephyr',
    }
    config = VoiceConfig.from_environment(environment)
    assert config.tts_provider == 'google'
    assert config.google_en_voice == 'en-US-Chirp3-HD-Zephyr'
    assert config.google_vi_voice == 'vi-VN-Chirp3-HD-Zephyr'

    class FakeGoogleTTS:
        class Settings:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    monkeypatch.setattr('pipecat.services.google.tts.GoogleTTSService', FakeGoogleTTS)
    tts = build_tts(config)
    assert tts.credentials_path == str(credentials)
    assert tts.location == 'asia-southeast1'
    assert tts.settings.voice == 'vi-VN-Chirp3-HD-Zephyr'
    assert tts.settings.language == Language.VI


def test_google_provider_requires_only_its_own_tts_configuration():
    from voice_config import VoiceConfig

    with pytest.raises(ValueError, match='GOOGLE_APPLICATION_CREDENTIALS.*GOOGLE_TTS_LOCATION'):
        VoiceConfig.from_environment({'SONIOX_API_KEY': 'stt-secret', 'TTS_PROVIDER': 'google'})
