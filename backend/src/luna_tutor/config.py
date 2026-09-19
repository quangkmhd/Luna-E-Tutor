"""Runtime configuration for the Luna Tutor teaching core."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Settings loaded from the process environment."""

    openrouter_api_key: str
    openrouter_model: str = "google/gemini-3.5-flash-lite"
    request_timeout_seconds: float = 20.0

    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings after validating the required OpenRouter API key."""
        key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not key:
            raise ValueError("OPENROUTER_API_KEY is required")
        return cls(openrouter_api_key=key)
