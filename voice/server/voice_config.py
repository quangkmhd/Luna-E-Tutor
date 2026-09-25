"""Validated STT and selectable TTS configuration for the Grade 3 voice service."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from pipecat.services.soniox.stt import SonioxSTTService
from pipecat.services.soniox.tts import SonioxTTSService
from pipecat.transcriptions.language import Language


@dataclass(frozen=True)
class VoiceConfig:
    soniox_api_key: str
    soniox_voice_id: str = ''
    tts_provider: str = 'soniox'
    google_credentials_path: str = ''
    google_tts_location: str = ''
    google_en_voice: str = ''
    google_vi_voice: str = ''

    @classmethod
    def from_environment(cls, environment: Mapping[str, str]) -> 'VoiceConfig':
        provider = environment.get('TTS_PROVIDER', 'soniox').strip().lower() or 'soniox'
        if provider not in ('soniox', 'google'):
            raise ValueError(f'Unsupported TTS_PROVIDER: {provider}')
        names = ['SONIOX_API_KEY']
        if provider == 'soniox':
            names.append('SONIOX_VOICE_ID')
        else:
            names.extend(('GOOGLE_APPLICATION_CREDENTIALS', 'GOOGLE_TTS_LOCATION',
                          'GOOGLE_TTS_EN_VOICE', 'GOOGLE_TTS_VI_VOICE'))
        missing = [name for name in names if not environment.get(name, '').strip()]
        if missing:
            raise ValueError('Missing required voice configuration: ' + ', '.join(missing))
        credentials_path = environment.get('GOOGLE_APPLICATION_CREDENTIALS', '').strip()
        if credentials_path and not Path(credentials_path).is_absolute():
            credentials_path = str(Path(__file__).resolve().parents[2] / credentials_path)
        return cls(
            soniox_api_key=environment['SONIOX_API_KEY'].strip(),
            soniox_voice_id=environment.get('SONIOX_VOICE_ID', '').strip(),
            tts_provider=provider,
            google_credentials_path=credentials_path,
            google_tts_location=environment.get('GOOGLE_TTS_LOCATION', '').strip(),
            google_en_voice=environment.get('GOOGLE_TTS_EN_VOICE', '').strip(),
            google_vi_voice=environment.get('GOOGLE_TTS_VI_VOICE', '').strip(),
        )


def build_soniox_stt(config: VoiceConfig) -> SonioxSTTService:
    return SonioxSTTService(
        api_key=config.soniox_api_key,
        vad_force_turn_endpoint=True,
        settings=SonioxSTTService.Settings(
            model='stt-rt-v5', language_hints=[Language.EN, Language.VI],
            language_hints_strict=False, context='Grade 3 English lesson',
        ),
    )


def build_soniox_tts(config: VoiceConfig) -> SonioxTTSService:
    return SonioxTTSService(
        api_key=config.soniox_api_key,
        settings=SonioxTTSService.Settings(
            model='tts-rt-v2', voice=config.soniox_voice_id,
            language=Language.VI, speed=1.0,
        ),
    )


def build_tts(config: VoiceConfig):
    if config.tts_provider == 'soniox':
        return build_soniox_tts(config)
    from pipecat.services.google.tts import GoogleTTSService

    return GoogleTTSService(
        credentials_path=config.google_credentials_path,
        location=config.google_tts_location,
        settings=GoogleTTSService.Settings(
            voice=config.google_vi_voice,
            language=Language.VI,
        ),
    )
