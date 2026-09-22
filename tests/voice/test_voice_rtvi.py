import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "voice/server"))

from pipecat.frames.frames import (
    AggregatedTextFrame,
    AggregationType,
    BotStartedSpeakingFrame,
    InterruptionFrame,
)
from pipecat.observers.base_observer import FramePushed
from pipecat.processors.frame_processor import FrameDirection


@pytest.mark.asyncio
async def test_interrupted_unspoken_caption_is_not_flushed_with_next_utterance(monkeypatch):
    from voice_rtvi import LunaRTVIObserver

    observer = LunaRTVIObserver()
    sent = []

    async def record(message, *_args, **_kwargs):
        sent.append(message)

    monkeypatch.setattr(observer, "send_rtvi_message", record)
    skipped = AggregatedTextFrame("Xin chào con! Cô là Luna.", AggregationType.SENTENCE)
    skipped.context_id = "interrupted-greeting"
    skipped.will_be_spoken = True
    await observer._handle_aggregated_llm_text(skipped)

    await observer.on_push_frame(FramePushed(
        source=None,
        destination=None,
        frame=InterruptionFrame(),
        direction=FrameDirection.DOWNSTREAM,
        timestamp=0,
    ))
    await observer._handle_bot_speaking(BotStartedSpeakingFrame())

    assert not any(getattr(message, "data", None) and
                   getattr(message.data, "text", None) == skipped.text for message in sent)

    next_line = AggregatedTextFrame("Cô trò mình sang Trạm 1.", AggregationType.SENTENCE)
    next_line.context_id = "next-turn"
    next_line.will_be_spoken = True
    await observer._handle_aggregated_llm_text(next_line)
    assert any(getattr(message, "data", None) and
               getattr(message.data, "text", None) == next_line.text for message in sent)
