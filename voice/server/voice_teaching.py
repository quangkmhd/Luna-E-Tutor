"""Pipecat frame adapters for the persistent Luna teaching engine."""

from dataclasses import dataclass, field
from typing import Any, cast

from luna_tutor.domain.decisions import CompletedTurn, PlannedTurn
from luna_tutor.domain.state import LessonState
from luna_tutor.storage.session_repository import SessionRepository
from loguru import logger
from pipecat.frames.frames import (
    BotStoppedSpeakingFrame,
    CancelFrame,
    EndWorkerFrame,
    ErrorFrame,
    Frame,
    InterruptionFrame,
    LLMContextFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


@dataclass
class VoiceTeachingExchange:
    """Mutable, session-local bridge between ordered frames and lesson state."""

    service: Any
    repository: SessionRepository
    session_id: str
    state: LessonState
    plan: PlannedTurn | None = None
    pending_completion: CompletedTurn | None = None
    error: Exception | None = None
    flow: Any = field(init=False, default=None)
    worker: Any = field(init=False, default=None)
    seen_turn_ids: set[str] = field(default_factory=set)
    generation_epoch: int = 0

    def discard_pending(self) -> None:
        self.pending_completion = None
        self.generation_epoch += 1

    async def fail(self, error: Exception) -> None:
        logger.opt(exception=error).error("Voice teaching failed: {}", error)
        self.error = error
        self.discard_pending()
        if self.worker is not None:
            await self.worker.queue_frames(
                [ErrorFrame(str(error), exception=error), EndWorkerFrame()]
            )


class VoiceTeachingProcessor(FrameProcessor):
    """Plan one lesson response from each Pipecat-completed user turn.

    This processor belongs immediately after ``LLMUserAggregator``.  Raw STT
    frames can be final provider chunks without being a complete conversational
    turn, so they must remain owned by Pipecat's VAD/Smart Turn aggregation.
    """

    def __init__(self, exchange: VoiceTeachingExchange):
        super().__init__()
        self.exchange = exchange

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, (InterruptionFrame, ErrorFrame, CancelFrame)):
            self.exchange.discard_pending()
            await self.push_frame(frame, direction)
            return
        if direction != FrameDirection.DOWNSTREAM:
            await self.push_frame(frame, direction)
            return
        if not isinstance(frame, LLMContextFrame):
            await self.push_frame(frame, direction)
            return

        messages = cast(list[dict[str, Any]], frame.context.get_messages())
        message = messages[-1] if messages else None
        content = message.get("content") if isinstance(message, dict) else None
        if not (
            isinstance(message, dict)
            and message.get("role") == "user"
            and isinstance(content, str)
            and content.strip()
        ):
            await self.push_frame(frame, direction)
            return

        # Consume Pipecat's generic inference frame. The authorized Flow node
        # below emits the only LLMContextFrame allowed to reach the teacher.
        logger.info("Pipecat completed learner turn: {!r}", content.strip())
        await self._plan_turn(content.strip(), f"pipecat:{frame.id}")

    async def _plan_turn(self, text: str, turn_id: str) -> None:
        if turn_id in self.exchange.seen_turn_ids:
            return
        self.exchange.seen_turn_ids.add(turn_id)

        try:
            stored_turn = self.exchange.repository.get_turn(self.exchange.session_id, turn_id)
            if stored_turn is not None:
                self.exchange.state = self.exchange.repository.get_session(
                    self.exchange.session_id
                ).state
                return
            stored = self.exchange.repository.get_session(self.exchange.session_id)
            self.exchange.state = stored.state
            if stored.state.status != 'active':
                return
            plan = await self.exchange.service.plan(
                stored.state,
                text,
                turn_id,
                transcript_status="final",
                input_event="transcript",
            )
            self.exchange.plan = plan
            self.exchange.flow.state["teacher_request"] = (
                plan.teacher_request.model_dump_json()
            )
            await self.exchange.flow.set_node_from_config(
                {
                    "name": plan.proposed_next_state.activity_id,
                    "task_messages": [
                        {"role": "developer", "content": "{{ teacher_request }}"}
                    ],
                    "respond_immediately": True,
                }
            )
        except Exception as error:
            await self.exchange.fail(error)


class VoiceCommitProcessor(FrameProcessor):
    """Commit only teacher turns whose audio Pipecat reports as finished."""

    def __init__(self, exchange: VoiceTeachingExchange):
        super().__init__()
        self.exchange = exchange

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, (InterruptionFrame, ErrorFrame, CancelFrame)):
            self.exchange.discard_pending()
        elif (
            direction == FrameDirection.DOWNSTREAM
            and isinstance(frame, BotStoppedSpeakingFrame)
            and self.exchange.pending_completion is not None
        ):
            completed = self.exchange.pending_completion
            self.exchange.pending_completion = None
            try:
                committed = self.exchange.repository.commit_turn(
                    self.exchange.session_id,
                    completed.plan.state_version,
                    completed,
                )
                self.exchange.state = committed.next_state
            except Exception as error:
                await self.exchange.fail(error)
        await self.push_frame(frame, direction)
