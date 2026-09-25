import sys
from pathlib import Path

import pytest
from pipecat.frames.frames import (
    AggregatedTextFrame,
    BotStoppedSpeakingFrame,
    ErrorFrame,
    InterruptionFrame,
    LLMFullResponseEndFrame,
    TTSAudioRawFrame,
    TTSSpeakFrame,
    TTSStartedFrame,
    TTSStoppedFrame,
    TTSUpdateSettingsFrame,
)
from pipecat.processors.frame_processor import FrameDirection
from pipecat.processors.frameworks.rtvi.frames import RTVIServerMessageFrame
from pipecat.transcriptions.language import Language

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'voice/server'))


@pytest.mark.asyncio
async def test_google_caption_events_follow_audio_chunks_and_source(monkeypatch):
    from google_captions import GoogleCaptionProgressProcessor
    from language_tts import GoogleCaptionSource

    source = GoogleCaptionSource()
    source.set_source('<en>Hello there.</en>')
    source.set_segment()
    progress = GoogleCaptionProgressProcessor(source)
    sent = []

    async def record(frame, direction=FrameDirection.DOWNSTREAM):
        sent.append((frame, direction))

    monkeypatch.setattr(progress, 'push_frame', record)
    await progress.process_frame(AggregatedTextFrame('Hello there.', aggregated_by='sentence', context_id='ctx-1'), FrameDirection.DOWNSTREAM)
    await progress.process_frame(TTSAudioRawFrame(b'\0' * 4800, 24000, 1, context_id='ctx-1'), FrameDirection.DOWNSTREAM)
    await progress.process_frame(TTSAudioRawFrame(b'\0' * 2400, 24000, 1, context_id='ctx-1'), FrameDirection.DOWNSTREAM)
    await progress.process_frame(TTSStoppedFrame(context_id='ctx-1'), FrameDirection.DOWNSTREAM)

    events = [frame.data for frame, _ in sent if isinstance(frame, RTVIServerMessageFrame)]
    assert [event['payload']['kind'] for event in events] == ['start', 'chunk', 'chunk', 'end']
    assert events[0]['payload']['source_text'] == '<en>Hello there.</en>'
    assert [event['payload']['audio_ms'] for event in events[1:]] == [100, 150, 150]
    assert [frame for frame, _ in sent if isinstance(frame, TTSAudioRawFrame)][0].audio == b'\0' * 4800


@pytest.mark.asyncio
async def test_bilingual_segments_wait_for_each_spoken_stop(monkeypatch):
    from language_tts import (
        LanguageSpeechFinishedFrame,
        LanguageSynthesisFinishedFrame,
        LanguageSynthesisStartedFrame,
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
    assert [frame.text for frame, _ in sent if isinstance(frame, TTSSpeakFrame)] == ['Xin chào']
    assert [frame.delta.language for frame, _ in sent if isinstance(frame, TTSUpdateSettingsFrame)] == [Language.VI]

    await adapter.process_frame(LLMFullResponseEndFrame(), FrameDirection.DOWNSTREAM)
    assert not any(isinstance(frame, LLMFullResponseEndFrame) for frame, _ in sent)
    await adapter.process_frame(BotStoppedSpeakingFrame(), FrameDirection.UPSTREAM)
    assert [frame.text for frame, _ in sent if isinstance(frame, TTSSpeakFrame)] == ['Xin chào']
    await adapter.process_frame(LanguageSynthesisStartedFrame('vi-1'), FrameDirection.UPSTREAM)
    await adapter.process_frame(BotStoppedSpeakingFrame(), FrameDirection.UPSTREAM)
    assert [frame.text for frame, _ in sent if isinstance(frame, TTSSpeakFrame)] == ['Xin chào']
    await adapter.process_frame(LanguageSynthesisFinishedFrame('stale-context'), FrameDirection.UPSTREAM)
    await adapter.process_frame(BotStoppedSpeakingFrame(), FrameDirection.UPSTREAM)
    assert [frame.text for frame, _ in sent if isinstance(frame, TTSSpeakFrame)] == ['Xin chào']
    await adapter.process_frame(LanguageSynthesisFinishedFrame('vi-1'), FrameDirection.UPSTREAM)
    assert [frame.text for frame, _ in sent if isinstance(frame, TTSSpeakFrame)] == ['Xin chào', 'HELLO']
    await adapter.process_frame(LanguageSynthesisStartedFrame('en-1'), FrameDirection.UPSTREAM)
    await adapter.process_frame(LanguageSynthesisFinishedFrame('en-1'), FrameDirection.UPSTREAM)
    assert [frame.delta.language for frame, _ in sent if isinstance(frame, TTSUpdateSettingsFrame)] == [Language.VI, Language.EN, Language.VI]
    await adapter.process_frame(LanguageSynthesisStartedFrame('vi-2'), FrameDirection.UPSTREAM)
    await adapter.process_frame(LanguageSynthesisFinishedFrame('vi-2'), FrameDirection.UPSTREAM)
    assert [frame.text for frame, _ in sent if isinstance(frame, TTSSpeakFrame)] == ['Xin chào', 'HELLO', 'Con nói nhé']
    assert len([frame for frame, _ in sent if isinstance(frame, LanguageSpeechFinishedFrame)]) == 1
    assert any(isinstance(frame, LLMFullResponseEndFrame) for frame, _ in sent)


@pytest.mark.asyncio
async def test_google_switches_voice_and_omits_square_bracket_cues(monkeypatch):
    from language_tts import (
        LanguageSynthesisFinishedFrame,
        LanguageSynthesisStartedFrame,
        LanguageTaggedSpeechFrame,
        LanguageTaggedTTSProcessor,
    )

    adapter = LanguageTaggedTTSProcessor(
        provider='google',
        google_vi_voice='vi-VN-Chirp3-HD-Zephyr',
        google_en_voice='en-US-Chirp3-HD-Zephyr',
    )
    sent = []

    async def record(frame, direction=FrameDirection.DOWNSTREAM):
        sent.append(frame)

    monkeypatch.setattr(adapter, 'push_frame', record)
    await adapter.process_frame(LanguageTaggedSpeechFrame(
        '<vi>[long pause] Xin chào.</vi><en>[slowly] Hello!</en><vi>Con nói nhé.</vi>',
        'turn-google'
    ), FrameDirection.DOWNSTREAM)
    await adapter.process_frame(LanguageSynthesisStartedFrame('vi-1'), FrameDirection.UPSTREAM)
    await adapter.process_frame(LanguageSynthesisFinishedFrame('vi-1'), FrameDirection.UPSTREAM)

    assert [frame.text for frame in sent if isinstance(frame, TTSSpeakFrame)] == [
        'Xin chào', 'Hello',
    ]
    assert [(frame.delta.language, frame.delta.voice) for frame in sent
            if isinstance(frame, TTSUpdateSettingsFrame)] == [
        (Language.VI, 'vi-VN-Chirp3-HD-Zephyr'),
        (Language.EN, 'en-US-Chirp3-HD-Zephyr'),
    ]
    assert [frame.delta.speaking_rate for frame in sent
            if isinstance(frame, TTSUpdateSettingsFrame)] == [1.0, 0.9]

    await adapter.process_frame(LanguageSynthesisStartedFrame('en-1'), FrameDirection.UPSTREAM)
    await adapter.process_frame(LanguageSynthesisFinishedFrame('en-1'), FrameDirection.UPSTREAM)
    assert [frame.delta.speaking_rate for frame in sent
            if isinstance(frame, TTSUpdateSettingsFrame)] == [1.0, 0.9, 1.0]


@pytest.mark.asyncio
async def test_authored_symbols_are_not_sent_to_tts(monkeypatch):
    from language_tts import LanguageTaggedSpeechFrame, LanguageTaggedTTSProcessor

    adapter = LanguageTaggedTTSProcessor(provider='soniox')
    sent = []

    async def record(frame, direction=FrameDirection.DOWNSTREAM):
        sent.append(frame)

    monkeypatch.setattr(adapter, 'push_frame', record)
    await adapter.process_frame(LanguageTaggedSpeechFrame(
        '<en>Say **Hello** - #@$%,... and *goodbye*?</en>'
    ), FrameDirection.DOWNSTREAM)
    assert [frame.text for frame in sent if isinstance(frame, TTSSpeakFrame)] == [
        'Say Hello and goodbye',
    ]


@pytest.mark.asyncio
async def test_cue_only_output_fails_delivery_instead_of_finishing_silently(monkeypatch):
    from language_tts import (
        LanguageSpeechFinishedFrame,
        LanguageTaggedSpeechFrame,
        LanguageTaggedTTSProcessor,
    )

    adapter = LanguageTaggedTTSProcessor()
    sent = []

    async def record(frame, direction=FrameDirection.DOWNSTREAM):
        sent.append(frame)

    monkeypatch.setattr(adapter, 'push_frame', record)
    await adapter.process_frame(LanguageTaggedSpeechFrame('<vi>[long pause]</vi>'), FrameDirection.DOWNSTREAM)
    assert any(isinstance(frame, ErrorFrame) for frame in sent)
    assert not any(isinstance(frame, LanguageSpeechFinishedFrame) for frame in sent)


@pytest.mark.asyncio
async def test_soniox_completion_observer_reports_matching_context_upstream(monkeypatch):
    from language_tts import (
        LanguageSynthesisFinishedFrame,
        LanguageSynthesisStartedFrame,
        LanguageTTSCompletionObserver,
    )

    observer = LanguageTTSCompletionObserver()
    sent = []

    async def record(frame, direction=FrameDirection.DOWNSTREAM):
        sent.append((frame, direction))

    monkeypatch.setattr(observer, 'push_frame', record)
    await observer.process_frame(TTSStartedFrame(context_id='soniox-1'), FrameDirection.DOWNSTREAM)
    await observer.process_frame(TTSAudioRawFrame(audio=b'\0\0', sample_rate=24000, num_channels=1), FrameDirection.DOWNSTREAM)
    await observer.process_frame(TTSStoppedFrame(context_id='soniox-1'), FrameDirection.DOWNSTREAM)
    assert [(type(frame), frame.context_id, direction) for frame, direction in sent
            if isinstance(frame, (LanguageSynthesisStartedFrame, LanguageSynthesisFinishedFrame))] == [
        (LanguageSynthesisStartedFrame, 'soniox-1', FrameDirection.UPSTREAM),
        (LanguageSynthesisFinishedFrame, 'soniox-1', FrameDirection.UPSTREAM),
    ]


@pytest.mark.asyncio
async def test_observer_does_not_complete_unheard_or_interrupted_audio(monkeypatch):
    from language_tts import (
        LanguageSynthesisFinishedFrame,
        LanguageTTSCompletionObserver,
    )

    observer = LanguageTTSCompletionObserver()
    sent = []

    async def record(frame, direction=FrameDirection.DOWNSTREAM):
        sent.append((frame, direction))

    monkeypatch.setattr(observer, 'push_frame', record)
    await observer.process_frame(TTSStartedFrame(context_id='silent'), FrameDirection.DOWNSTREAM)
    await observer.process_frame(TTSStoppedFrame(context_id='silent'), FrameDirection.DOWNSTREAM)
    assert not any(isinstance(frame, LanguageSynthesisFinishedFrame) for frame, _ in sent)
    assert any(isinstance(frame, ErrorFrame) for frame, _ in sent)

    sent.clear()
    await observer.process_frame(TTSStartedFrame(context_id='interrupted'), FrameDirection.DOWNSTREAM)
    await observer.process_frame(TTSAudioRawFrame(audio=b'\0\0', sample_rate=24000, num_channels=1), FrameDirection.DOWNSTREAM)
    await observer.process_frame(InterruptionFrame(), FrameDirection.DOWNSTREAM)
    await observer.process_frame(TTSStoppedFrame(context_id='interrupted'), FrameDirection.DOWNSTREAM)
    assert not any(isinstance(frame, LanguageSynthesisFinishedFrame) for frame, _ in sent)


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
    assert [frame.text for frame in sent if isinstance(frame, TTSSpeakFrame)] == ['Chào']


@pytest.mark.asyncio
async def test_barge_in_during_audio_does_not_finish_or_start_next_language_segment(monkeypatch):
    from language_tts import (
        LanguageSpeechFinishedFrame,
        LanguageSynthesisStartedFrame,
        LanguageTaggedSpeechFrame,
        LanguageTaggedTTSProcessor,
        LanguageTTSCompletionObserver,
    )
    from pipecat.processors.frame_processor import FrameProcessor

    async def skip_framework_dispatch(_processor, _frame, _direction):
        return None

    monkeypatch.setattr(FrameProcessor, 'process_frame', skip_framework_dispatch)

    adapter = LanguageTaggedTTSProcessor()
    observer = LanguageTTSCompletionObserver()
    sent = []

    async def record_adapter(frame, direction=FrameDirection.DOWNSTREAM):
        sent.append(frame)

    async def route_observer(frame, direction=FrameDirection.DOWNSTREAM):
        if direction == FrameDirection.UPSTREAM:
            await adapter.process_frame(frame, direction)

    monkeypatch.setattr(adapter, 'push_frame', record_adapter)
    monkeypatch.setattr(observer, 'push_frame', route_observer)

    await adapter.process_frame(
        LanguageTaggedSpeechFrame('<vi>Xin chào con.</vi><en>Hello!</en>', 'turn-barge-in'),
        FrameDirection.DOWNSTREAM,
    )
    await observer.process_frame(TTSStartedFrame(context_id='spoken-context'), FrameDirection.DOWNSTREAM)
    assert any(isinstance(frame, LanguageSynthesisStartedFrame) for frame in sent)
    await observer.process_frame(
        TTSAudioRawFrame(audio=b'\0\0', sample_rate=24000, num_channels=1, context_id='spoken-context'),
        FrameDirection.DOWNSTREAM,
    )
    await adapter.process_frame(InterruptionFrame(), FrameDirection.DOWNSTREAM)
    await observer.process_frame(InterruptionFrame(), FrameDirection.DOWNSTREAM)
    await observer.process_frame(TTSStoppedFrame(context_id='spoken-context'), FrameDirection.DOWNSTREAM)

    assert [frame.text for frame in sent if isinstance(frame, TTSSpeakFrame)] == ['Xin chào con']
    assert not any(isinstance(frame, (ErrorFrame, LanguageSpeechFinishedFrame)) for frame in sent)
