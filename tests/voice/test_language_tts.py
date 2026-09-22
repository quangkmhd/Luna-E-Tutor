import sys
from pathlib import Path

import pytest
from pipecat.frames.frames import (
    BotStoppedSpeakingFrame,
    InterruptionFrame,
    LLMFullResponseEndFrame,
    TTSSpeakFrame,
    TTSUpdateSettingsFrame,
)
from pipecat.processors.frame_processor import FrameDirection
from pipecat.transcriptions.language import Language

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'voice/server'))


@pytest.mark.asyncio
async def test_bilingual_segments_wait_for_each_spoken_stop(monkeypatch):
    from language_tts import (
        LanguageSpeechFinishedFrame,
        LanguageTaggedSpeechFrame,
        LanguageTaggedTTSProcessor,
    )

    adapter = LanguageTaggedTTSProcessor()
    sent = []

    async def record(frame, direction=FrameDirection.DOWNSTREAM):
        sent.append((frame, direction))

    monkeypatch.setattr(adapter, 'push_frame', record)
    await adapter.process_frame(LanguageTaggedSpeechFrame(
        '<vi>Xin chào.</vi><en>HELLO</en><vi>Con nói nhé.</vi>', 'turn-1'
    ), FrameDirection.DOWNSTREAM)
    assert [frame.text for frame, _ in sent if isinstance(frame, TTSSpeakFrame)] == ['Xin chào.']
    assert [frame.delta.language for frame, _ in sent if isinstance(frame, TTSUpdateSettingsFrame)] == [Language.VI]

    await adapter.process_frame(LLMFullResponseEndFrame(), FrameDirection.DOWNSTREAM)
    assert not any(isinstance(frame, LLMFullResponseEndFrame) for frame, _ in sent)
    await adapter.process_frame(BotStoppedSpeakingFrame(), FrameDirection.UPSTREAM)
    assert [frame.text for frame, _ in sent if isinstance(frame, TTSSpeakFrame)] == ['Xin chào.', 'HELLO']
    await adapter.process_frame(BotStoppedSpeakingFrame(), FrameDirection.UPSTREAM)
    assert [frame.delta.language for frame, _ in sent if isinstance(frame, TTSUpdateSettingsFrame)] == [Language.VI, Language.EN, Language.VI]
    await adapter.process_frame(BotStoppedSpeakingFrame(), FrameDirection.UPSTREAM)
    assert [frame.text for frame, _ in sent if isinstance(frame, TTSSpeakFrame)] == ['Xin chào.', 'HELLO', 'Con nói nhé.']
    assert len([frame for frame, _ in sent if isinstance(frame, LanguageSpeechFinishedFrame)]) == 1
    assert any(isinstance(frame, LLMFullResponseEndFrame) for frame, _ in sent)


@pytest.mark.asyncio
async def test_interruption_drops_remaining_speech(monkeypatch):
    from language_tts import LanguageTaggedSpeechFrame, LanguageTaggedTTSProcessor

    adapter = LanguageTaggedTTSProcessor()
    sent = []

    async def record(frame, direction=FrameDirection.DOWNSTREAM):
        sent.append(frame)

    monkeypatch.setattr(adapter, 'push_frame', record)
    await adapter.process_frame(LanguageTaggedSpeechFrame('<vi>Chào.</vi><en>HELLO</en>', 'turn-2'), FrameDirection.DOWNSTREAM)
    await adapter.process_frame(InterruptionFrame(), FrameDirection.DOWNSTREAM)
    await adapter.process_frame(BotStoppedSpeakingFrame(), FrameDirection.UPSTREAM)
    assert [frame.text for frame in sent if isinstance(frame, TTSSpeakFrame)] == ['Chào.']
