import asyncio
import sys
from dataclasses import fields
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "voice/server"))

from luna_tutor.api.runtime import RuntimeComponents
from luna_tutor.curriculum.registry import CurriculumRegistry, UnknownUnitError
from luna_tutor.domain.state import LessonState
from luna_tutor.storage.session_repository import SessionRepository
from luna_tutor.teaching.unit_router import UnitTurnRouter
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.transports.base_transport import BaseTransport
from pipecat.utils.types import is_given
from test_voice_teaching import RecordingService

ROOT = Path(__file__).resolve().parents[2]


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


def runtime_components(repository, service):
    return RuntimeComponents(
        repository=repository,
        turn_service=service,
        client=None,
        curriculum_registry=CurriculumRegistry(
            ROOT / "curriculum",
            (
                "grade05.unit01", "grade05.unit02",
                "grade05.unit03", "grade05.unit04", "grade05.unit05",
            ),
        ),
    )


def test_bounded_teacher_initializes_complete_pipecat_llm_settings():
    from text_flows import BoundedTeacherLLM

    teacher = BoundedTeacherLLM(SimpleNamespace())

    missing = [
        item.name
        for item in fields(teacher._settings)
        if item.name != "extra" and not is_given(getattr(teacher._settings, item.name))
    ]
    assert missing == []


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


def test_build_voice_worker_rejects_unknown_stored_unit_before_services(
    tmp_path, monkeypatch
):
    import bot

    repository = SessionRepository(tmp_path / "voice.sqlite3")
    state = LessonState(
        session_id="unknown-unit",
        unit_id="grade05.unit99",
        stage_id="warm-up",
        activity_id="warm-up.feelings",
    )
    repository.create_session(state)
    monkeypatch.setattr(
        bot,
        "build_runtime_components",
        lambda _environment: runtime_components(repository, RecordingService()),
    )
    monkeypatch.setattr(
        bot,
        "build_soniox_stt",
        lambda _config: pytest.fail("provider service should not be constructed"),
    )

    with pytest.raises(UnknownUnitError, match="grade05.unit99"):
        bot.build_voice_worker(
            FakeTransport(),
            SimpleNamespace(body={"session_id": state.session_id}),
            live_environment(tmp_path / "voice.sqlite3"),
        )


@pytest.mark.asyncio
async def test_build_voice_worker_routes_persisted_unit2_state(
    tmp_path, monkeypatch
):
    import bot

    repository = SessionRepository(tmp_path / "voice.sqlite3")
    state = LessonState(
        session_id="unit2-session",
        unit_id="grade05.unit02",
        stage_id="warm-up",
        activity_id="warm-up.feelings",
        opening_message="Hello, Quang! How are you today?",
    )
    repository.create_session(state)
    unit1 = RecordingService()
    unit2 = RecordingService()
    router = UnitTurnRouter({
        "grade05.unit01": unit1,
        "grade05.unit02": unit2,
    }, response_service=unit2)
    monkeypatch.setattr(
        bot,
        "build_runtime_components",
        lambda _environment: runtime_components(repository, router),
    )
    monkeypatch.setattr(bot, "build_soniox_stt", lambda _config: STTProcessor())
    monkeypatch.setattr(bot, "build_soniox_tts", lambda _config: TTSProcessor())

    worker = bot.build_voice_worker(
        FakeTransport(),
        SimpleNamespace(body={"session_id": state.session_id}),
        live_environment(tmp_path / "voice.sqlite3"),
    )
    await worker.luna_exchange.service.plan(
        state, "I feel happy.", "unit2-voice"
    )

    assert worker.luna_exchange.state.unit_id == "grade05.unit02"
    assert unit2.calls == ["I feel happy."]
    assert unit1.calls == []


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
        lambda _environment: runtime_components(repository, RecordingService()),
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
    assert processors.index(next(p for p in processors if isinstance(p, VoiceTeachingProcessor))) > processors.index(
        next(p for p in processors if p.__class__.__name__ == "LLMUserAggregator")
    )
    assert worker.luna_exchange.session_id == "selected-session"
    assert worker.luna_exchange.state == state


def test_voice_worker_does_not_finalize_on_a_brief_pause_inside_a_sentence(
    tmp_path, monkeypatch
):
    import bot

    repository = SessionRepository(tmp_path / "voice.sqlite3")
    state = LessonState(
        session_id="pause-session",
        unit_id="grade05.unit01",
        stage_id="warm-up",
        activity_id="warm-up.feelings",
    )
    repository.create_session(state)
    monkeypatch.setattr(
        bot,
        "build_runtime_components",
        lambda _environment: runtime_components(repository, RecordingService()),
    )
    monkeypatch.setattr(bot, "build_soniox_stt", lambda _config: STTProcessor())
    monkeypatch.setattr(bot, "build_soniox_tts", lambda _config: TTSProcessor())

    worker = bot.build_voice_worker(
        FakeTransport(),
        SimpleNamespace(body={"session_id": state.session_id}),
        live_environment(tmp_path / "voice.sqlite3"),
    )
    user_aggregator = next(
        processor
        for processor in worker.luna_pipeline.processors
        if processor.__class__.__name__ == "LLMUserAggregator"
    )

    assert user_aggregator._params.vad_analyzer.params.stop_secs == 0.8


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
        lambda _environment: runtime_components(repository, service),
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
