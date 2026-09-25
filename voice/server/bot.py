"""Grade 3 scripted Voice worker: manual Soniox finalization and ordered TTS."""

import os
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger
from pipecat.evals.transport import EvalTransportParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.frameworks.rtvi import RTVIProcessor
from pipecat.processors.frameworks.rtvi.frames import RTVIServerMessageFrame
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.workers.runner import WorkerRunner

from language_tts import GoogleCaptionSource, LanguageTaggedTTSProcessor, LanguageTTSCompletionObserver
from google_captions import GoogleCaptionProgressProcessor
from lesson_voice_bridge import (
    ScriptedDeliveryObserver,
    ScriptedVoiceAPI,
    ScriptedVoiceBridge,
)
from voice_config import VoiceConfig, build_soniox_stt, build_tts

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=True)


def _session_id(runner_args: RunnerArguments) -> str:
    body = getattr(runner_args, 'body', None)
    session_id = body.get('session_id') if isinstance(body, dict) else None
    if not isinstance(session_id, str) or not session_id.strip():
        raise ValueError('SmallWebRTC request_data must include a non-empty session_id')
    return session_id.strip()


def build_voice_worker(transport: BaseTransport, runner_args: RunnerArguments,
                       environment=os.environ) -> PipelineWorker:
    session_id = _session_id(runner_args)
    config = VoiceConfig.from_environment(environment)
    stt = build_soniox_stt(config)
    api = ScriptedVoiceAPI(environment.get('TUTOR_API_URL', 'http://127.0.0.1:8000'),
                           session_id)
    bridge = ScriptedVoiceBridge(api)
    delivery = ScriptedDeliveryObserver(bridge.delivery_finished, bridge.delivery_failed)
    bridge.set_delivery_started(delivery.start_delivery)
    caption_source = GoogleCaptionSource() if config.tts_provider == 'google' else None
    pipeline = Pipeline([
        transport.input(), stt, bridge, LanguageTaggedTTSProcessor(
            provider=config.tts_provider,
            google_vi_voice=config.google_vi_voice,
            google_en_voice=config.google_en_voice,
            caption_source=caption_source,
        ),
        delivery, build_tts(config),
        *([GoogleCaptionProgressProcessor(caption_source)] if caption_source else []),
        transport.output(),
        LanguageTTSCompletionObserver(),
    ])
    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
        rtvi_processor=RTVIProcessor(),
    )
    worker.luna_api = api
    worker.luna_bridge = bridge

    greeted = False

    @worker.rtvi.event_handler('on_client_ready')
    async def on_client_ready(_rtvi):
        nonlocal greeted
        if not greeted:
            greeted = True
            await bridge.push_frame(RTVIServerMessageFrame(data={
                'event': 'tts-provider', 'payload': {'provider': config.tts_provider},
            }))
            await bridge.start_lesson()

    @transport.event_handler('on_client_connected')
    async def on_client_connected(_transport, _client):
        logger.info('Voice client connected for session {}', session_id)

    @transport.event_handler('on_client_disconnected')
    async def on_client_disconnected(_transport, _client):
        logger.info('Voice client disconnected for session {}', session_id)
        await worker.cancel()

    return worker


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments) -> None:
    worker = build_voice_worker(transport, runner_args)
    runner = WorkerRunner(handle_sigint=False)
    await runner.add_workers(worker)
    try:
        await runner.run()
    finally:
        await worker.luna_api.close()


async def bot(runner_args: RunnerArguments):
    _session_id(runner_args)
    transport_params = {
        'webrtc': lambda: TransportParams(audio_in_enabled=True, audio_out_enabled=True),
        'eval': lambda: EvalTransportParams(audio_in_enabled=True, audio_out_enabled=True),
    }
    transport = await create_transport(runner_args, transport_params)
    await run_bot(transport, runner_args)


if __name__ == '__main__':
    from pipecat.runner.run import main
    main()
