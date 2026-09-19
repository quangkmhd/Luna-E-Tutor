from uuid import uuid4

from pipecat.frames.frames import (
    Frame, LLMFullResponseEndFrame, LLMFullResponseStartFrame, LLMTextFrame,
    TranscriptionFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


class SpeakingProcessor(FrameProcessor):
    def __init__(self, api, session_id: str):
        super().__init__()
        self.api = api
        self.session_id = session_id
        self.version: int | None = None

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if not isinstance(frame, TranscriptionFrame) or direction != FrameDirection.DOWNSTREAM:
            await self.push_frame(frame, direction)
            return
        if not frame.finalized:
            return
        if self.version is None:
            self.version = (await self.api.get(self.session_id))['version']
        result = await self.api.submit(self.session_id, {
            'turn_id': str(uuid4()), 'text': frame.text,
            'expected_version': self.version, 'quality': 'final', 'input_mode': 'voice',
        })
        self.version = result['state']['version']
        await self.push_frame(LLMFullResponseStartFrame())
        await self.push_frame(LLMTextFrame(result['reply']['text']))
        await self.push_frame(LLMFullResponseEndFrame())
