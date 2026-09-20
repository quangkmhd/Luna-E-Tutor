import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "voice/server"))

from luna_tutor.api.runtime import FixtureTurnService
from luna_tutor.domain.state import LessonState
from luna_tutor.storage.session_repository import SessionRepository
from pipecat.frames.frames import (
    BotStoppedSpeakingFrame,
    EndWorkerFrame,
    ErrorFrame,
    InterimTranscriptionFrame,
    InterruptionFrame,
    LLMContextFrame,
    LLMTextFrame,
    TranscriptionFrame,
)
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.frame_processor import FrameDirection
from pipecat.transcriptions.language import Language


class RecordingService:
    def __init__(self):
        self.calls = []
        self.completed = {}
        self.fixture = FixtureTurnService()

    async def plan(self, state, learner_text, turn_id, **_kwargs):
        self.calls.append(learner_text)
        completed = await self.fixture.process(state, learner_text, turn_id)
        self.completed[turn_id] = completed
        return completed.plan

    async def respond(self, request):
        return self.completed[request.turn_id].teacher_utterance

    def complete(self, _state, plan, _utterance):
        return self.completed[plan.turn_id]


class RecordingFlow:
    def __init__(self):
        self.state = {}
        self.current_node = None
        self.nodes = []

    async def set_node_from_config(self, node):
        self.current_node = node["name"]
        self.nodes.append(node)


class RecordingWorker:
    def __init__(self):
        self.frames = []

    async def queue_frames(self, frames):
        self.frames.extend(frames)


def make_exchange(tmp_path):
    from voice_teaching import VoiceTeachingExchange, VoiceTeachingProcessor

    repository = SessionRepository(tmp_path / "voice.sqlite3")
    state = LessonState(
        session_id="voice-session",
        unit_id="grade05.unit01",
        stage_id="warm-up",
        activity_id="warm-up.feelings",
        opening_message="Hello, Quang! How are you today?",
    )
    repository.create_session(state)
    service = RecordingService()
    exchange = VoiceTeachingExchange(
        service=service,
        repository=repository,
        session_id=state.session_id,
        state=state,
    )
    exchange.flow = RecordingFlow()
    return exchange, VoiceTeachingProcessor(exchange), service


@pytest.mark.asyncio
async def test_provider_transcripts_do_not_plan_before_pipecat_finishes_the_turn(tmp_path):
    exchange, processor, service = make_exchange(tmp_path)
    await processor.process_frame(
        InterimTranscriptionFrame("I live", "u", "now", Language.EN),
        FrameDirection.DOWNSTREAM,
    )
    final = TranscriptionFrame("I live in the city.", "u", "now", Language.EN)
    await processor.process_frame(final, FrameDirection.DOWNSTREAM)
    await processor.process_frame(final, FrameDirection.DOWNSTREAM)

    assert service.calls == []
    assert exchange.plan is None

    context = LLMContext(messages=[{"role": "user", "content": "I live in the city."}])
    await processor.process_frame(LLMContextFrame(context=context), FrameDirection.DOWNSTREAM)

    assert service.calls == ["I live in the city."]
    assert exchange.plan is not None
    assert exchange.plan.learner_text == "I live in the city."
    assert exchange.flow.nodes[-1]["respond_immediately"] is True


@pytest.mark.asyncio
async def test_eval_send_text_plans_one_typed_turn(tmp_path):
    exchange, processor, service = make_exchange(tmp_path)

    context = LLMContext(messages=[{"role": "user", "content": "I am happy today."}])
    await processor.process_frame(LLMContextFrame(context=context), FrameDirection.DOWNSTREAM)

    assert service.calls == ["I am happy today."]
    assert exchange.plan is not None
    assert exchange.plan.turn_id.startswith("pipecat:")


@pytest.mark.asyncio
async def test_completed_turn_commits_only_after_bot_stops(tmp_path):
    from voice_teaching import VoiceCommitProcessor

    exchange, _, service = make_exchange(tmp_path)
    completed = await service.fixture.process(exchange.state, "I am fine.", "voice:u:one")
    exchange.pending_completion = completed
    commit = VoiceCommitProcessor(exchange)

    assert exchange.repository.get_session(exchange.session_id).state.state_version == 0
    await commit.process_frame(BotStoppedSpeakingFrame(), FrameDirection.DOWNSTREAM)
    stored = exchange.repository.get_session(exchange.session_id)
    assert stored.state.state_version == 1
    assert len(stored.turns) == 1


@pytest.mark.asyncio
async def test_interruption_discards_unspoken_pending_completion(tmp_path, monkeypatch):
    from voice_teaching import VoiceCommitProcessor

    async def skip_framework_dispatch(_processor, _frame, _direction):
        return None

    monkeypatch.setattr(
        "pipecat.processors.frame_processor.FrameProcessor.process_frame",
        skip_framework_dispatch,
    )

    exchange, _, service = make_exchange(tmp_path)
    exchange.pending_completion = await service.fixture.process(
        exchange.state, "I am fine.", "voice:u:two"
    )
    commit = VoiceCommitProcessor(exchange)

    await commit.process_frame(InterruptionFrame(), FrameDirection.DOWNSTREAM)
    await commit.process_frame(BotStoppedSpeakingFrame(), FrameDirection.DOWNSTREAM)

    stored = exchange.repository.get_session(exchange.session_id)
    assert stored.state.state_version == 0
    assert stored.turns == ()


@pytest.mark.asyncio
async def test_upstream_provider_error_prevents_later_speech_stop_commit(tmp_path):
    from voice_teaching import VoiceCommitProcessor

    exchange, teaching, service = make_exchange(tmp_path)
    exchange.pending_completion = await service.fixture.process(
        exchange.state, "I am fine.", "voice:u:error"
    )
    commit = VoiceCommitProcessor(exchange)

    await teaching.process_frame(ErrorFrame("Soniox TTS failed"), FrameDirection.UPSTREAM)
    await commit.process_frame(BotStoppedSpeakingFrame(), FrameDirection.DOWNSTREAM)

    stored = exchange.repository.get_session(exchange.session_id)
    assert stored.state.state_version == 0
    assert stored.turns == ()


@pytest.mark.asyncio
async def test_teaching_failure_keeps_the_original_exception_on_pipecat_error_frame(tmp_path):
    exchange, _, _ = make_exchange(tmp_path)
    exchange.worker = RecordingWorker()
    failure = RuntimeError("teacher generation failed")

    await exchange.fail(failure)

    assert len(exchange.worker.frames) == 2
    error_frame, end_frame = exchange.worker.frames
    assert isinstance(error_frame, ErrorFrame)
    assert error_frame.error == "teacher generation failed"
    assert error_frame.exception is failure
    assert error_frame.fatal is False
    assert isinstance(end_frame, EndWorkerFrame)


@pytest.mark.asyncio
async def test_invalid_teacher_fallback_is_spoken_without_ending_voice_session(
    tmp_path, monkeypatch
):
    from luna_tutor.domain.decisions import TeacherUtterance
    from pipecat.services.llm_service import LLMService
    from text_flows import BoundedTeacherLLM

    async def skip_framework_dispatch(_processor, _frame, _direction):
        return None

    monkeypatch.setattr(LLMService, "process_frame", skip_framework_dispatch)
    exchange, _, service = make_exchange(tmp_path)
    plan = await service.plan(exchange.state, "I live in the city.", "voice:fallback")
    exchange.plan = plan
    exchange.flow.current_node = plan.proposed_next_state.activity_id

    class FallbackService:
        async def respond(self, _request):
            return TeacherUtterance(
                spoken_text="Let us take a moment, Quang. We can try that together.",
                delivery_intent="reassuring",
                generation_mode="fallback",
            )

        def complete(self, *_args):
            pytest.fail("Fallback must not commit the proposed lesson transition")

    exchange.service = FallbackService()
    teacher = BoundedTeacherLLM(exchange, end_after_response=False)
    output = []

    async def record(frame, _direction=FrameDirection.DOWNSTREAM):
        output.append(frame)

    monkeypatch.setattr(teacher, "push_frame", record)
    context = LLMContext(messages=[{
        "role": "developer",
        "content": plan.teacher_request.model_dump_json(),
    }])

    await teacher.process_frame(LLMContextFrame(context=context), FrameDirection.DOWNSTREAM)

    assert [frame.text for frame in output if isinstance(frame, LLMTextFrame)] == [
        "Let us take a moment, Quang. We can try that together."
    ]
    assert exchange.error is None
    assert exchange.pending_completion is None
