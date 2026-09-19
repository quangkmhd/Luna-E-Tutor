"""Typed frames shared by the HTTP pipeline and native teaching Flows."""

from dataclasses import dataclass

from luna_tutor.domain.decisions import CompletedTurn
from luna_tutor.domain.evidence import InputEvent, TranscriptStatus
from luna_tutor.domain.state import LessonState
from pipecat.frames.frames import DataFrame, Frame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


@dataclass
class LearnerTextFrame(DataFrame):
    state: LessonState
    text: str
    turn_id: str
    transcript_status: TranscriptStatus = "final"
    input_event: InputEvent = "transcript"


@dataclass
class CompletedTeachingFrame(DataFrame):
    turn: CompletedTurn


class TextResultProcessor(FrameProcessor):
    def __init__(self):
        super().__init__()
        self.turns: list[CompletedTurn] = []

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, CompletedTeachingFrame) and direction == FrameDirection.DOWNSTREAM:
            self.turns.append(frame.turn)
        await self.push_frame(frame, direction)
