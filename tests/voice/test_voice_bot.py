import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "voice/server"))

from luna_tutor.api.runtime import RuntimeComponents
from luna_tutor.domain.state import LessonState
from luna_tutor.storage.session_repository import SessionRepository
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.transports.base_transport import BaseTransport
from test_voice_teaching import RecordingService


class InputProcessor(FrameProcessor):
    pass


class STTProcessor(FrameProcessor):
    pass


class TTSProcessor(FrameProcessor):
    pass


class OutputProcessor(FrameProcessor):
    pass


class FakeTransport(BaseTransport):
    def __init__(self):
        super().__init__()
        self._register_event_handler("on_client_connected")
        self._register_event_handler("on_client_disconnected")
        self._input = InputProcessor()
        self._output = OutputProcessor()

    def input(self):
        return self._input

    def output(self):
        return self._output


def live_environment(database):
    return {
        "TUTOR_DATABASE_PATH": str(database),
        "SONIOX_API_KEY": "soniox-test",
        "SONIOX_VOICE_ID": "voice-test",
        "OPENROUTER_API_KEY": "openrouter-test",
        "OPENROUTER_MODEL": "provider/model",
    }


def test_build_voice_worker_requires_session_metadata_before_services(tmp_path, monkeypatch):
    import bot

    monkeypatch.setattr(
        bot,
        "build_soniox_stt",
        lambda _config: pytest.fail("provider service should not be constructed"),
    )
    with pytest.raises(ValueError, match="session_id"):
        bot.build_voice_worker(
            FakeTransport(), SimpleNamespace(body={}), live_environment(tmp_path / "voice.sqlite3")
        )


def test_build_voice_worker_rejects_unknown_session_before_services(tmp_path, monkeypatch):
    import bot

    monkeypatch.setattr(
        bot,
        "build_soniox_stt",
        lambda _config: pytest.fail("provider service should not be constructed"),
    )
    with pytest.raises(LookupError, match="missing-session"):
        bot.build_voice_worker(
            FakeTransport(),
            SimpleNamespace(body={"session_id": "missing-session"}),
            live_environment(tmp_path / "voice.sqlite3"),
        )


def test_build_voice_worker_uses_canonical_teaching_pipeline(tmp_path, monkeypatch):
    import bot
    from text_flows import BoundedTeacherLLM
    from voice_teaching import VoiceCommitProcessor, VoiceTeachingProcessor

    repository = SessionRepository(tmp_path / "voice.sqlite3")
    state = LessonState(
        session_id="selected-session",
        unit_id="grade05.unit01",
        stage_id="warm-up",
        activity_id="warm-up.feelings",
        opening_message="Hello, Quang! How are you today?",
    )
    repository.create_session(state)
    monkeypatch.setattr(
        bot,
        "build_runtime_components",
        lambda _environment: RuntimeComponents(repository, RecordingService(), None),
    )
    monkeypatch.setattr(bot, "build_soniox_stt", lambda _config: STTProcessor())
    monkeypatch.setattr(bot, "build_soniox_tts", lambda _config: TTSProcessor())

    transport = FakeTransport()
    worker = bot.build_voice_worker(
        transport,
        SimpleNamespace(body={"session_id": state.session_id}),
        live_environment(tmp_path / "voice.sqlite3"),
    )
    processors = worker.luna_pipeline.processors
    selected = [
        type(processor)
        for processor in processors
        if isinstance(
            processor,
            (
                InputProcessor,
                STTProcessor,
                VoiceTeachingProcessor,
                BoundedTeacherLLM,
                TTSProcessor,
                OutputProcessor,
                VoiceCommitProcessor,
            ),
        )
    ]
    assert selected == [
        InputProcessor,
        STTProcessor,
        VoiceTeachingProcessor,
        BoundedTeacherLLM,
        TTSProcessor,
        OutputProcessor,
        VoiceCommitProcessor,
    ]
    assert worker.luna_exchange.session_id == "selected-session"
    assert worker.luna_exchange.state == state


@pytest.mark.asyncio
async def test_disconnect_discards_pending_completion_before_cancel(tmp_path, monkeypatch):
    import bot

    repository = SessionRepository(tmp_path / "voice.sqlite3")
    state = LessonState(
        session_id="disconnect-session",
        unit_id="grade05.unit01",
        stage_id="warm-up",
        activity_id="warm-up.feelings",
    )
    repository.create_session(state)
    service = RecordingService()
    monkeypatch.setattr(
        bot,
        "build_runtime_components",
        lambda _environment: RuntimeComponents(repository, service, None),
    )
    monkeypatch.setattr(bot, "build_soniox_stt", lambda _config: STTProcessor())
    monkeypatch.setattr(bot, "build_soniox_tts", lambda _config: TTSProcessor())
    transport = FakeTransport()
    worker = bot.build_voice_worker(
        transport,
        SimpleNamespace(body={"session_id": state.session_id}),
        live_environment(tmp_path / "voice.sqlite3"),
    )
    worker.luna_exchange.pending_completion = await service.fixture.process(
        state, "I am fine.", "disconnect-turn"
    )
    cancelled = False

    async def cancel():
        nonlocal cancelled
        cancelled = True

    monkeypatch.setattr(worker, "cancel", cancel)
    await transport._call_event_handler("on_client_disconnected", "client")
    await asyncio.sleep(0)

    assert cancelled is True
    assert worker.luna_exchange.pending_completion is None
    assert repository.get_session(state.session_id).turns == ()
