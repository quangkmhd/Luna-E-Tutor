from types import MappingProxyType

import pytest

from session_config import MAX_TOPIC_LENGTH, TalkSessionConfigError, parse_talk_session_config


def test_topic_is_trimmed_and_returned():
    assert parse_talk_session_config({"topic": "  Animals  "}).topic == "Animals"


@pytest.mark.parametrize("topic", ["", "   ", "x" * 121, None])
def test_invalid_topic_is_rejected(topic):
    with pytest.raises(TalkSessionConfigError):
        parse_talk_session_config(MappingProxyType({"topic": topic}))


def test_topic_limit_matches_browser_contract():
    assert MAX_TOPIC_LENGTH == 120
