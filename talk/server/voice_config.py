"""Validated provider configuration for the standalone Talk runtime."""

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class TalkVoiceConfig:
    soniox_api_key: str
    voice_id: str
    openrouter_api_key: str
    llm_model: str

    @classmethod
    def from_environment(cls, environment: Mapping[str, str]) -> "TalkVoiceConfig":
        names = (
            "SONIOX_API_KEY",
            "SONIOX_VOICE_ID",
            "OPENROUTER_API_KEY",
            "OPENROUTER_MODEL",
        )
        missing = [name for name in names if not environment.get(name, "").strip()]
        if missing:
            raise ValueError("Missing required Talk configuration: " + ", ".join(missing))
        return cls(*(environment[name].strip() for name in names))
