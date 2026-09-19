import pytest

from pipecat.frames.frames import LLMFullResponseEndFrame, LLMFullResponseStartFrame, LLMTextFrame, TranscriptionFrame
from pipecat.processors.frame_processor import FrameDirection
from speaking_processor import SpeakingProcessor


class FakeApi:
    def __init__(self): self.version = 0; self.turns = []
    async def get(self, session_id): return {'session_id': session_id, 'version': self.version}
    async def submit(self, session_id, turn):
        self.turns.append((session_id, turn))
        self.version += 1
        return {'state': {'version': self.version}, 'reply': {'text': 'Great! Tell me one reason.', 'support_kind': 'continue'}}


@pytest.mark.asyncio
async def test_final_transcript_becomes_one_spoken_reply():
    api = FakeApi(); processor = SpeakingProcessor(api, 's1')
    pushed = []
    async def capture(frame, direction=FrameDirection.DOWNSTREAM): pushed.append(frame)
    processor.push_frame = capture
    await processor.process_frame(TranscriptionFrame('I like juice', 'u1', 'now', finalized=True), FrameDirection.DOWNSTREAM)
    assert len(api.turns) == 1
    assert [type(frame) for frame in pushed] == [LLMFullResponseStartFrame, LLMTextFrame, LLMFullResponseEndFrame]
    assert pushed[1].text == 'Great! Tell me one reason.'


@pytest.mark.asyncio
async def test_non_final_transcript_is_not_submitted():
    api = FakeApi(); processor = SpeakingProcessor(api, 's1')
    pushed = []
    async def capture(frame, direction=FrameDirection.DOWNSTREAM): pushed.append(frame)
    processor.push_frame = capture
    await processor.process_frame(TranscriptionFrame('I like', 'u1', 'now', finalized=False), FrameDirection.DOWNSTREAM)
    assert api.turns == []
