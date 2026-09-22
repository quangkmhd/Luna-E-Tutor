import asyncio
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
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
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
    from voice_teaching import CompletedLearnerTurnFrame
    await processor.process_frame(CompletedLearnerTurnFrame(
        "I live in the city.", "pipecat:test-city"), FrameDirection.DOWNSTREAM)

    assert service.calls == ["I live in the city."]
    assert exchange.plan is not None
    assert exchange.plan.learner_text == "I live in the city."
    assert exchange.flow.nodes[-1]["respond_immediately"] is True


@pytest.mark.asyncio
async def test_eval_send_text_plans_one_typed_turn(tmp_path):
    exchange, processor, service = make_exchange(tmp_path)

    context = LLMContext(messages=[{"role": "user", "content": "I am happy today."}])
    await processor.process_frame(LLMContextFrame(context=context), FrameDirection.DOWNSTREAM)
    from voice_teaching import CompletedLearnerTurnFrame
    await processor.process_frame(CompletedLearnerTurnFrame(
        "I am happy today.", "pipecat:test-happy"), FrameDirection.DOWNSTREAM)

    assert service.calls == ["I am happy today."]
    assert exchange.plan is not None
    assert exchange.plan.turn_id.startswith("pipecat:")


@pytest.mark.asyncio
async def test_completed_turn_commits_only_after_final_language_segment(tmp_path):
    from language_tts import LanguageSpeechFinishedFrame
    from voice_teaching import VoiceCommitProcessor

    exchange, _, service = make_exchange(tmp_path)
    completed = await service.fixture.process(exchange.state, "I am fine.", "voice:u:one")
    exchange.pending_completion = completed
    commit = VoiceCommitProcessor(exchange)

    assert exchange.repository.get_session(exchange.session_id).state.state_version == 0
    await commit.process_frame(BotStoppedSpeakingFrame(), FrameDirection.DOWNSTREAM)
    assert exchange.repository.get_session(exchange.session_id).state.state_version == 0
    await commit.process_frame(LanguageSpeechFinishedFrame('wrong-turn'), FrameDirection.DOWNSTREAM)
    assert exchange.repository.get_session(exchange.session_id).state.state_version == 0
    await commit.process_frame(LanguageSpeechFinishedFrame(completed.plan.turn_id), FrameDirection.DOWNSTREAM)
    stored = exchange.repository.get_session(exchange.session_id)
    assert stored.state.state_version == 1
    assert len(stored.turns) == 1
    await commit.process_frame(LanguageSpeechFinishedFrame(completed.plan.turn_id), FrameDirection.DOWNSTREAM)
    assert exchange.repository.get_session(exchange.session_id).state.state_version == 1


@pytest.mark.asyncio
async def test_interruption_discards_unspoken_pending_completion(tmp_path, monkeypatch):
    from language_tts import LanguageSpeechFinishedFrame
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
    await commit.process_frame(LanguageSpeechFinishedFrame('voice:u:two'), FrameDirection.DOWNSTREAM)

    stored = exchange.repository.get_session(exchange.session_id)
    assert stored.state.state_version == 0
    assert stored.turns == ()


@pytest.mark.asyncio
async def test_interrupted_spoken_transition_is_committed_before_next_learner_turn(tmp_path, monkeypatch):
    from luna_tutor.api.runtime import FixtureScriptEvaluator
    from luna_tutor.curriculum.lesson_script import load_lesson_script
    from luna_tutor.teaching.scripted_lesson import ScriptedLessonService

    from language_tts import LanguageSynthesisStartedFrame
    from voice_teaching import VoiceCommitProcessor, VoiceTeachingExchange, VoiceTeachingProcessor

    async def skip_framework_dispatch(_processor, _frame, _direction):
        return None

    monkeypatch.setattr(
        "pipecat.processors.frame_processor.FrameProcessor.process_frame",
        skip_framework_dispatch,
    )
    script = load_lesson_script(
        Path(__file__).resolve().parents[2] / "curriculum/grade-03/unit-01/lesson-01/content.yaml"
    )
    service = ScriptedLessonService(script, FixtureScriptEvaluator(), None)
    hello = service.opportunities[3]
    state = service.fresh_state("voice-grade3").model_copy(update={
        "script_index": 3,
        "stage_id": hello.stage,
        "activity_id": hello.activity_id,
        "objective_id": hello.objective_id,
        "last_teacher_turn": hello.say,
    })
    repository = SessionRepository(tmp_path / "voice-grade3.sqlite3")
    repository.create_session(state)
    exchange = VoiceTeachingExchange(service, repository, state.session_id, state)
    exchange.flow = RecordingFlow()
    teaching = VoiceTeachingProcessor(exchange)
    previous = await service.process(state, "Hello.", "voice:hello")
    assert previous.next_state.activity_id == "lesson-03.exchange-01"
    exchange.pending_completion = previous
    commit = VoiceCommitProcessor(exchange)

    await teaching.process_frame(LanguageSynthesisStartedFrame("tts-hi"), FrameDirection.UPSTREAM)
    await teaching.process_frame(InterruptionFrame(), FrameDirection.DOWNSTREAM)
    await commit.process_frame(InterruptionFrame(), FrameDirection.DOWNSTREAM)
    assert exchange.repository.get_session(exchange.session_id).state.state_version == 0

    await teaching._plan_turn("Hi.", "voice:hi")
    stored = exchange.repository.get_session(exchange.session_id)
    assert stored.state.state_version == 1
    assert stored.turns[0].plan.turn_id == "voice:hello"
    assert exchange.plan is not None
    assert exchange.plan.state_version == 1
    assert exchange.plan.decision.next_activity_id == "lesson-04.exchange-01"


@pytest.mark.asyncio
async def test_completed_transcript_is_queued_as_uninterruptible_work(tmp_path, monkeypatch):
    from pipecat.frames.frames import UninterruptibleFrame

    exchange, teaching, service = make_exchange(tmp_path)
    queued = []

    async def record_queue(frame, direction=FrameDirection.DOWNSTREAM):
        queued.append((frame, direction))

    monkeypatch.setattr(teaching, "queue_frame", record_queue)
    context = LLMContext(messages=[{"role": "user", "content": "Hi. Hi. Hi."}])
    await teaching.process_frame(LLMContextFrame(context=context), FrameDirection.DOWNSTREAM)

    assert service.calls == []
    assert len(queued) == 1
    turn_frame, direction = queued[0]
    assert isinstance(turn_frame, UninterruptibleFrame)
    assert turn_frame.text == "Hi. Hi. Hi."
    assert direction == FrameDirection.DOWNSTREAM
    await teaching.process_frame(turn_frame, direction)
    assert service.calls == ["Hi. Hi. Hi."]
    assert exchange.flow.nodes


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
    assert error_frame.fatal is True
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

    from language_tts import LanguageTaggedSpeechFrame

    assert [frame.text for frame in output if isinstance(frame, LanguageTaggedSpeechFrame)] == [
        "Let us take a moment, Quang. We can try that together."
    ]
    assert exchange.error is None
    assert exchange.pending_completion is None


@pytest.mark.asyncio
async def test_voice_teacher_does_not_open_empty_llm_tts_stream(tmp_path, monkeypatch):
    from language_tts import LanguageTaggedSpeechFrame
    from pipecat.services.llm_service import LLMService
    from text_flows import BoundedTeacherLLM
    from text_frames import CompletedTeachingFrame

    async def skip_framework_dispatch(_processor, _frame, _direction):
        return None

    monkeypatch.setattr(LLMService, "process_frame", skip_framework_dispatch)
    exchange, _, service = make_exchange(tmp_path)
    plan = await service.plan(exchange.state, "I am fine.", "voice:no-empty-stream")
    exchange.plan = plan
    exchange.flow.current_node = plan.proposed_next_state.activity_id
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

    assert [type(frame) for frame in output] == [
        LanguageTaggedSpeechFrame,
        CompletedTeachingFrame,
    ]
    assert not any(isinstance(frame, (LLMFullResponseStartFrame, LLMFullResponseEndFrame)) for frame in output)


@pytest.mark.asyncio
async def test_voice_teacher_ignores_superseded_flow_frame_and_answers_latest(tmp_path, monkeypatch):
    from pipecat.services.llm_service import LLMService

    from language_tts import LanguageTaggedSpeechFrame
    from text_flows import BoundedTeacherLLM

    async def skip_framework_dispatch(_processor, _frame, _direction):
        return None

    monkeypatch.setattr(LLMService, "process_frame", skip_framework_dispatch)
    exchange, _, service = make_exchange(tmp_path)
    exchange.worker = RecordingWorker()
    first = await service.plan(exchange.state, "Hello.", "voice:old")
    latest = await service.plan(exchange.state, "I'm Minh.", "voice:latest")
    exchange.plan = latest
    exchange.flow.current_node = latest.proposed_next_state.activity_id
    teacher = BoundedTeacherLLM(exchange, end_after_response=False)
    output = []

    async def record(frame, _direction=FrameDirection.DOWNSTREAM):
        output.append(frame)

    monkeypatch.setattr(teacher, "push_frame", record)
    for plan in (first, latest):
        context = LLMContext(messages=[{
            "role": "developer",
            "content": plan.teacher_request.model_dump_json(),
        }])
        await teacher.process_frame(LLMContextFrame(context=context), FrameDirection.DOWNSTREAM)

    assert exchange.error is None
    assert [frame.logical_turn_id for frame in output
            if isinstance(frame, LanguageTaggedSpeechFrame)] == ["voice:latest"]
    assert exchange.pending_completion is not None
    assert exchange.pending_completion.plan.turn_id == "voice:latest"


@pytest.mark.asyncio
async def test_voice_teacher_drops_response_superseded_during_generation(tmp_path, monkeypatch):
    from pipecat.services.llm_service import LLMService

    from language_tts import LanguageTaggedSpeechFrame
    from text_flows import BoundedTeacherLLM

    async def skip_framework_dispatch(_processor, _frame, _direction):
        return None

    monkeypatch.setattr(LLMService, "process_frame", skip_framework_dispatch)
    exchange, _, service = make_exchange(tmp_path)
    exchange.worker = RecordingWorker()
    first = await service.plan(exchange.state, "Hello.", "voice:old")
    latest = await service.plan(exchange.state, "I'm Minh.", "voice:latest")
    exchange.plan = first
    exchange.flow.current_node = first.proposed_next_state.activity_id
    started = asyncio.Event()
    release = asyncio.Event()
    original_respond = service.respond

    async def respond(request):
        if request.turn_id == first.turn_id:
            started.set()
            await release.wait()
        return await original_respond(request)

    monkeypatch.setattr(service, "respond", respond)
    teacher = BoundedTeacherLLM(exchange, end_after_response=False)
    output = []

    async def record(frame, _direction=FrameDirection.DOWNSTREAM):
        output.append(frame)

    monkeypatch.setattr(teacher, "push_frame", record)

    def context_for(plan):
        return LLMContextFrame(context=LLMContext(messages=[{
            "role": "developer", "content": plan.teacher_request.model_dump_json(),
        }]))

    old_response = asyncio.create_task(teacher.process_frame(
        context_for(first), FrameDirection.DOWNSTREAM,
    ))
    await started.wait()
    exchange.plan = latest
    exchange.flow.current_node = latest.proposed_next_state.activity_id
    await teacher.process_frame(context_for(latest), FrameDirection.DOWNSTREAM)
    release.set()
    await old_response

    assert exchange.error is None
    assert [frame.logical_turn_id for frame in output if isinstance(frame, LanguageTaggedSpeechFrame)] == ["voice:latest"]
    assert exchange.pending_completion.plan.turn_id == "voice:latest"
