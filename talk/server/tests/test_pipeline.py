import importlib.util
from types import SimpleNamespace
from typing import cast

import pytest
from pipecat.runner.types import RunnerArguments

from bot import compose_talk_pipeline_processors, parse_runner_config
from session_config import TalkSessionConfigError


def test_pipeline_has_canonical_cascade_order():
    parts = {
        name: object()
        for name in ("input", "stt", "user", "llm", "tts", "output", "assistant")
    }
    assert compose_talk_pipeline_processors(**parts) == [
        parts["input"],
        parts["stt"],
        parts["user"],
        parts["llm"],
        parts["tts"],
        parts["output"],
        parts["assistant"],
    ]


def test_runner_topic_is_validated_before_worker_construction():
    with pytest.raises(TalkSessionConfigError):
        parse_runner_config(
            cast(RunnerArguments, SimpleNamespace(body={"topic": "   "}))
        )


def test_talk_environment_does_not_install_unit1_application():
    assert importlib.util.find_spec("luna_tutor") is None
