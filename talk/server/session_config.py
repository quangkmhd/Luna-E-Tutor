"""Request-scoped configuration for a standalone Free Talk session."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

MAX_TOPIC_LENGTH = 120


class TalkSessionConfigError(ValueError):
    """Raised when Talk request metadata is invalid."""


@dataclass(frozen=True)
class TalkSessionConfig:
    topic: str


def parse_talk_session_config(payload: Mapping[str, Any]) -> TalkSessionConfig:
    raw_topic = payload.get("topic")
    topic = raw_topic.strip() if isinstance(raw_topic, str) else ""
    if not topic:
        raise TalkSessionConfigError("Please choose or enter a conversation topic")
    if len(topic) > MAX_TOPIC_LENGTH:
        raise TalkSessionConfigError(
            f"Conversation topic must be at most {MAX_TOPIC_LENGTH} characters"
        )
    return TalkSessionConfig(topic=topic)
