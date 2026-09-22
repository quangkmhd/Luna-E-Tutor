"""Validated provider configuration for the Pipecat voice runtime."""

from collections.abc import Mapping
from dataclasses import dataclass

from luna_tutor.curriculum.models import UnitCurriculum
from pipecat.services.soniox.stt import SonioxSTTService
from pipecat.services.soniox.tts import SonioxTTSService
from pipecat.transcriptions.language import Language

def transcription_context(curriculum: UnitCurriculum) -> str:
    targets = [item.text for item in curriculum.vocabulary]
    targets.extend(item.text for item in curriculum.patterns)
    return (
        f'Grade {curriculum.grade} Unit {curriculum.unit} {curriculum.title}: '
        + ', '.join(targets)
    )[:1200]


@dataclass(frozen=True)
class VoiceConfig:
    soniox_api_key: str
    soniox_voice_id: str
    openrouter_api_key: str
    openrouter_model: str

    @classmethod
    def from_environment(cls, environment: Mapping[str, str]) -> "VoiceConfig":
        names = (
            "SONIOX_API_KEY",
            "SONIOX_VOICE_ID",
            "OPENROUTER_API_KEY",
            "OPENROUTER_MODEL",
        )
        missing = [name for name in names if not environment.get(name, "").strip()]
        if missing:
            raise ValueError("Missing required voice configuration: " + ", ".join(missing))
        return cls(*(environment[name].strip() for name in names))


def build_soniox_stt(config: VoiceConfig, curriculum: UnitCurriculum) -> SonioxSTTService:
    return SonioxSTTService(
        api_key=config.soniox_api_key,
        vad_force_turn_endpoint=True,
        settings=SonioxSTTService.Settings(
            model="stt-rt-v5",
            language_hints=[Language.EN, Language.VI],
            language_hints_strict=False,
            context=transcription_context(curriculum),
        ),
    )


def build_soniox_tts(config: VoiceConfig) -> SonioxTTSService:
    return SonioxTTSService(
        api_key=config.soniox_api_key,
        settings=SonioxTTSService.Settings(
            model="tts-rt-v2",
            voice=config.soniox_voice_id,
            language=Language.VI,
            speed=0.9,
        ),
    )
