"""Send Google audio chunk duration to the browser for paced captions.

Google's streaming response contains PCM audio but no word timestamps. These
events give the browser the actual duration of each chunk without exposing
audio bytes or pretending to know exact word boundaries.
"""

from dataclasses import dataclass

from pipecat.frames.frames import (
    AggregatedTextFrame,
    CancelFrame,
    ErrorFrame,
    Frame,
    InterruptionFrame,
    TTSAudioRawFrame,
    TTSStoppedFrame,
    TTSTextFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.processors.frameworks.rtvi.frames import RTVIServerMessageFrame

from language_tts import GoogleCaptionSource


@dataclass
class _Segment:
    source_id: int
    source_text: str
    segment_index: int
    text: str
    audio_ms: float = 0


class GoogleCaptionProgressProcessor(FrameProcessor):
    def __init__(self, source: GoogleCaptionSource):
        super().__init__()
        self._source = source
        self._segments: dict[str, _Segment] = {}

    async def _emit(self, kind: str, segment: _Segment) -> None:
        await self.push_frame(RTVIServerMessageFrame(data={
            'event': 'google-tts-caption',
            'payload': {
                'kind': kind,
                'source_id': segment.source_id,
                'source_text': segment.source_text,
                'segment_index': segment.segment_index,
                'segment_text': segment.text,
                'audio_ms': round(segment.audio_ms),
            },
        }))

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, (CancelFrame, ErrorFrame, InterruptionFrame)):
            self._segments.clear()
        elif direction == FrameDirection.DOWNSTREAM:
            if isinstance(frame, AggregatedTextFrame) and not isinstance(frame, TTSTextFrame) and frame.context_id:
                segment = _Segment(
                    self._source.source_id, self._source.source_text,
                    self._source.segment_index, frame.text,
                )
                self._segments[frame.context_id] = segment
                await self._emit('start', segment)
            elif isinstance(frame, TTSAudioRawFrame) and frame.context_id in self._segments:
                segment = self._segments[frame.context_id]
                segment.audio_ms += len(frame.audio) / (2 * frame.num_channels * frame.sample_rate) * 1000
                await self._emit('chunk', segment)
            elif isinstance(frame, TTSStoppedFrame) and frame.context_id in self._segments:
                segment = self._segments.pop(frame.context_id)
                await self._emit('end', segment)
        await self.push_frame(frame, direction)
