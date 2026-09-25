from types import SimpleNamespace

import bot
import pytest
from lesson_voice_bridge import ScriptedDeliveryObserver, ScriptedVoiceBridge
from google_captions import GoogleCaptionProgressProcessor
from pipecat.pipeline.pipeline import Pipeline
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.transports.base_transport import BaseTransport


class FakeTransport(BaseTransport):
    def __init__(self):
        super().__init__()
        self._register_event_handler('on_client_connected')
        self._register_event_handler('on_client_disconnected')
        self._input = FrameProcessor()
        self._output = FrameProcessor()

    def input(self):
        return self._input

    def output(self):
        return self._output


def test_voice_requires_session_id_before_provider_creation():
    with pytest.raises(ValueError, match='session_id'):
        bot.build_voice_worker(FakeTransport(), SimpleNamespace(body={}), {})


def test_voice_pipeline_uses_manual_soniox_and_scripted_bridge(monkeypatch):
    stt = FrameProcessor()
    tts = FrameProcessor()
    monkeypatch.setattr(bot, 'build_soniox_stt', lambda _config: stt)
    monkeypatch.setattr(bot, 'build_tts', lambda _config: tts)
    transport = FakeTransport()
    worker = bot.build_voice_worker(
        transport, SimpleNamespace(body={'session_id': 'grade3-session'}),
        {'SONIOX_API_KEY': 'test', 'SONIOX_VOICE_ID': 'test'},
    )
    assert worker.luna_bridge.api.session_id == 'grade3-session'
    processors = next(item.processors for item in worker.pipeline.processors if isinstance(item, Pipeline))
    assert stt in processors
    assert any(isinstance(item, ScriptedVoiceBridge) for item in processors)
    assert any(isinstance(item, ScriptedDeliveryObserver) for item in processors)
    assert transport.output() in processors
    assert not any(isinstance(item, GoogleCaptionProgressProcessor) for item in processors)
    assert processors.index(stt) < next(i for i, item in enumerate(processors) if isinstance(item, ScriptedVoiceBridge))


def test_google_voice_pipeline_tracks_audio_chunks(monkeypatch):
    stt = FrameProcessor()
    tts = FrameProcessor()
    monkeypatch.setattr(bot, 'build_soniox_stt', lambda _config: stt)
    monkeypatch.setattr(bot, 'build_tts', lambda _config: tts)
    transport = FakeTransport()
    worker = bot.build_voice_worker(
        transport, SimpleNamespace(body={'session_id': 'grade3-session'}),
        {
            'SONIOX_API_KEY': 'test', 'TTS_PROVIDER': 'google',
            'GOOGLE_APPLICATION_CREDENTIALS': 'gg.json',
            'GOOGLE_TTS_LOCATION': 'asia-southeast1',
            'GOOGLE_TTS_EN_VOICE': 'en-US-Chirp3-HD-Zephyr',
            'GOOGLE_TTS_VI_VOICE': 'vi-VN-Chirp3-HD-Zephyr',
        },
    )
    processors = next(item.processors for item in worker.pipeline.processors if isinstance(item, Pipeline))
    captions = next(item for item in processors if isinstance(item, GoogleCaptionProgressProcessor))
    assert processors.index(tts) < processors.index(captions) < processors.index(transport.output())
