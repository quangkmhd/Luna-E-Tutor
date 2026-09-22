"""Native activity Flows for typed tutoring; Engine is the only transition authority."""

from dataclasses import dataclass, field
from typing import Any, cast

from luna_tutor.domain.decisions import PlannedTurn, TeacherTurnRequest
from luna_tutor.domain.evidence import InputEvent, TranscriptStatus
from luna_tutor.domain.state import LessonState
from luna_tutor.teaching.turn_service import TurnService
from pipecat.flows import ContextStrategy, ContextStrategyConfig, FlowManager
from pipecat.frames.frames import (
    EndFrame,
    Frame,
    LLMContextFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.llm_service import LLMService
from pipecat.services.settings import LLMSettings
from pipecat.turns.user_turn_strategies import ExternalUserTurnStrategies
from pipecat.workers.runner import WorkerRunner

from text_frames import CompletedTeachingFrame, LearnerTextFrame, TextResultProcessor
from language_tts import LanguageTaggedSpeechFrame


@dataclass
class Exchange:
    service: TurnService
    state: LessonState
    plan: PlannedTurn | None = None
    error: Exception | None = None
    flow: FlowManager = field(init=False)
    worker: PipelineWorker = field(init=False)

    async def fail(self, error):
        self.error = error
        await self.worker.queue_frame(EndFrame())


class PlanProcessor(FrameProcessor):
    def __init__(self, exchange):
        super().__init__()
        self.exchange = exchange

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if not isinstance(frame, LearnerTextFrame):
            await self.push_frame(frame, direction)
            return
        exchange = self.exchange
        try:
            if frame.state.status != 'active':
                return
            plan = await exchange.service.plan(
                frame.state,
                frame.text,
                frame.turn_id,
                transcript_status=frame.transcript_status,
                input_event=frame.input_event,
            )
            exchange.plan = plan
            # Insert untrusted data as a value, not as a template. Flow rendering
            # substitutes once, so learner-authored {{...}} cannot access Flow state.
            exchange.flow.state["teacher_request"] = plan.teacher_request.model_dump_json()
            await exchange.flow.set_node_from_config(
                {
                    "name": plan.proposed_next_state.activity_id,
                    "task_messages": [{"role": "developer", "content": "{{ teacher_request }}"}],
                    "respond_immediately": True,
                }
            )
        except Exception as error:
            await exchange.fail(error)


class BoundedTeacherLLM(LLMService):
    """Use the existing Gemini prompt/schema/validation through native LLM frames."""

    def __init__(self, exchange, *, end_after_response=True):
        super().__init__(
            settings=LLMSettings(
                model="bounded-teacher",
                system_instruction=None,
                temperature=None,
                max_tokens=None,
                top_p=None,
                top_k=None,
                frequency_penalty=None,
                presence_penalty=None,
                seed=None,
                filter_incomplete_user_turns=None,
                user_turn_completion_config=None,
            )
        )
        self.exchange = exchange
        self.end_after_response = end_after_response
        self.responded_turn_ids = set()

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if not isinstance(frame, LLMContextFrame):
            await self.push_frame(frame, direction)
            return
        exchange = self.exchange
        try:
            if exchange.plan is None:
                raise RuntimeError("Flow must request exactly one authorized Teacher response")
            turn_id = exchange.plan.turn_id
            if turn_id in self.responded_turn_ids:
                raise RuntimeError("Flow must request exactly one authorized Teacher response")
            self.responded_turn_ids.add(turn_id)
            generation_epoch = getattr(exchange, "generation_epoch", None)
            messages = cast(list[dict[str, Any]], frame.context.get_messages())
            if len(messages) != 1 or messages[0].get("role") != "developer":
                raise ValueError("Unexpected teaching node context")
            content = messages[0].get("content")
            if not isinstance(content, str):
                raise ValueError("Unexpected teaching node content")
            request = TeacherTurnRequest.model_validate_json(content)
            if (
                request != exchange.plan.teacher_request
                or exchange.flow.current_node != exchange.plan.proposed_next_state.activity_id
            ):
                raise ValueError("Flow node and teaching authorization disagree")
            utterance = await exchange.service.respond(request)
            if utterance.generation_mode == "fallback" and not self.end_after_response:
                # A safe Teacher fallback is speakable but cannot authorize or
                # persist the Engine's proposed transition. Keep voice alive so
                # the learner can try again on the unchanged stored state.
                await self.push_frame(LanguageTaggedSpeechFrame(utterance.spoken_text))
                return
            completed = exchange.service.complete(exchange.state, exchange.plan, utterance)
            if (
                generation_epoch is not None
                and generation_epoch != exchange.generation_epoch
            ):
                return
            if hasattr(exchange, "pending_completion"):
                exchange.pending_completion = completed
            await self.push_frame(LanguageTaggedSpeechFrame(
                completed.teacher_utterance.spoken_text, completed.plan.turn_id,
            ))
            await self.push_frame(CompletedTeachingFrame(completed))
            if self.end_after_response:
                await exchange.worker.queue_frame(EndFrame())
        except Exception as error:
            await exchange.fail(error)


async def run_teaching_flow(
    service,
    state,
    learner_text,
    turn_id,
    *,
    transcript_status: TranscriptStatus = "final",
    input_event: InputEvent = "transcript",
):
    exchange = Exchange(service, state)
    context = LLMContext()
    aggregators = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            user_turn_strategies=ExternalUserTurnStrategies(), audio_idle_timeout=0
        ),
    )
    teacher = BoundedTeacherLLM(exchange)
    result = TextResultProcessor()
    worker = PipelineWorker(
        Pipeline(
            [
                PlanProcessor(exchange),
                aggregators.user(),
                teacher,
                result,
                aggregators.assistant(),
            ]
        ),
        enable_rtvi=False,
        enable_turn_tracking=False,
        idle_timeout_secs=None,
    )
    exchange.worker = worker
    exchange.flow = FlowManager(
        worker=worker,
        llm=teacher,
        context_aggregator=aggregators,
        context_strategy=ContextStrategyConfig(strategy=ContextStrategy.RESET),
    )
    runner = WorkerRunner(handle_sigint=False)
    await runner.add_workers(worker)
    await exchange.flow.initialize()
    await exchange.flow.set_node_from_config(
        {
            "name": state.activity_id,
            "task_messages": [{"role": "developer", "content": "Wait for the teaching decision."}],
            "respond_immediately": False,
        }
    )
    await worker.queue_frame(
        LearnerTextFrame(state, learner_text, turn_id, transcript_status, input_event)
    )
    await runner.run()
    if exchange.error is not None:
        raise exchange.error
    if len(result.turns) != 1:
        raise RuntimeError("Teaching Flow must produce exactly one completed turn")
    return result.turns[0]
