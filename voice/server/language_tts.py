"""Deliver authored language spans as sequential, complete TTS utterances."""

from collections import deque
from dataclasses import dataclass

from luna_tutor.speech.language_segments import SpeechSegment, parse_speech_segments
from pipecat.frames.frames import (
    BotStoppedSpeakingFrame,
    CancelFrame,
    DataFrame,
    ErrorFrame,
    Frame,
    InterruptionFrame,
    LLMFullResponseEndFrame,
    TTSSpeakFrame,
    TTSStartedFrame,
    TTSStoppedFrame,
    TTSUpdateSettingsFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.soniox.tts import SonioxTTSSettings
from pipecat.transcriptions.language import Language

from text_frames import CompletedTeachingFrame


@dataclass
class LanguageTaggedSpeechFrame(DataFrame):
    text: str
    logical_turn_id: str | None = None


@dataclass
class LanguageSpeechFinishedFrame(DataFrame):
    logical_turn_id: str | None = None


@dataclass
class LanguageSynthesisStartedFrame(DataFrame):
    context_id: str


@dataclass
class LanguageSynthesisFinishedFrame(DataFrame):
    context_id: str


class LanguageTTSCompletionObserver(FrameProcessor):
    """Relay Soniox context boundaries upstream without delaying playback."""

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if direction == FrameDirection.DOWNSTREAM and isinstance(frame, TTSStartedFrame) and frame.context_id:
            await self.push_frame(LanguageSynthesisStartedFrame(frame.context_id), FrameDirection.UPSTREAM)
        elif direction == FrameDirection.DOWNSTREAM and isinstance(frame, TTSStoppedFrame) and frame.context_id:
            await self.push_frame(LanguageSynthesisFinishedFrame(frame.context_id), FrameDirection.UPSTREAM)
        await self.push_frame(frame, direction)


class LanguageTaggedTTSProcessor(FrameProcessor):
    """Wait for Soniox termination and playback drain before switching language."""

    def __init__(self):
        super().__init__()
        self._queue: deque[LanguageTaggedSpeechFrame] = deque()
        self._active: LanguageTaggedSpeechFrame | None = None
        self._remaining: deque[SpeechSegment] = deque()
        self._deferred: list[Frame] = []
        self._active_context_id: str | None = None
        self._synthesis_done = False

    async def _next_segment(self) -> None:
        span = self._remaining.popleft()
        self._active_context_id = None
        self._synthesis_done = False
        await self.push_frame(TTSUpdateSettingsFrame(delta=SonioxTTSSettings(
            language=Language.VI if span.language == 'vi' else Language.EN,
        )))
        await self.push_frame(TTSSpeakFrame(span.text, append_to_context=True))

    async def _start_next(self) -> None:
        if self._active is not None or not self._queue:
            return
        self._active = self._queue.popleft()
        self._remaining = deque(parse_speech_segments(self._active.text, strict=False))
        if self._remaining:
            await self._next_segment()
        else:
            await self._finish_active()

    async def _finish_active(self) -> None:
        active = self._active
        self._active = None
        if active is not None:
            await self.push_frame(LanguageSpeechFinishedFrame(active.logical_turn_id))
        for frame in self._deferred:
            await self.push_frame(frame)
        self._deferred.clear()
        await self._start_next()

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, (InterruptionFrame, ErrorFrame, CancelFrame)):
            self._queue.clear()
            self._remaining.clear()
            self._deferred.clear()
            self._active = None
            self._active_context_id = None
            self._synthesis_done = False
            await self.push_frame(frame, direction)
        elif direction == FrameDirection.UPSTREAM and isinstance(frame, LanguageSynthesisStartedFrame):
            if self._active is not None and self._active_context_id is None:
                self._active_context_id = frame.context_id
            await self.push_frame(frame, direction)
        elif direction == FrameDirection.UPSTREAM and isinstance(frame, LanguageSynthesisFinishedFrame):
            if self._active is not None and frame.context_id == self._active_context_id:
                self._synthesis_done = True
            await self.push_frame(frame, direction)
        elif direction == FrameDirection.UPSTREAM and isinstance(frame, BotStoppedSpeakingFrame):
            await self.push_frame(frame, direction)
            if self._active is not None and self._synthesis_done:
                if self._remaining:
                    await self._next_segment()
                else:
                    await self._finish_active()
        elif direction == FrameDirection.DOWNSTREAM and isinstance(frame, LanguageTaggedSpeechFrame):
            self._queue.append(frame)
            await self._start_next()
        elif direction == FrameDirection.DOWNSTREAM and self._active is not None and isinstance(
            frame, (LLMFullResponseEndFrame, CompletedTeachingFrame)
        ):
            self._deferred.append(frame)
        else:
            await self.push_frame(frame, direction)
