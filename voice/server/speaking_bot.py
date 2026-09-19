"""Pipecat voice adapter for the independent grade 5 speaking room."""
import asyncio
from contextlib import suppress
import os
from uuid import uuid4

from dotenv import load_dotenv
from loguru import logger
from pipecat.evals.transport import EvalTransportParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.services.soniox.stt import SonioxSTTService
from pipecat.services.soniox.tts import SonioxTTSService
from pipecat.transports.base_transport import TransportParams
from pipecat.workers.runner import WorkerRunner

from speaking_api_client import SpeakingApiClient
from speaking_processor import SpeakingProcessor

ROOT_ENV = '/home/quangnhvn34/dev/massko/E-Voice-Tutor-v1/.env'
load_dotenv(ROOT_ENV, override=True)


def require(name: str) -> str:
    value = os.getenv(name, '').strip()
    if not value: raise ValueError(f'{name} is required in {ROOT_ENV}')
    return value


async def run_bot(transport, runner_args: RunnerArguments):
    body = runner_args.body or {}
    session_id = str(body.get('speaking_session_id', '')).strip()
    if not session_id:
        raise ValueError('speaking_session_id is required')
    if os.getenv('STT_PROVIDER', '').strip().lower() != 'soniox':
        raise ValueError('STT_PROVIDER must be soniox for the speaking room')
    api = SpeakingApiClient(os.getenv('TUTOR_API_URL', 'http://127.0.0.1:8000'))
    voice_token = str(uuid4())
    lease_task = None
    acquired = False

    async def renew_voice_lease():
        while True:
            await asyncio.sleep(10)
            await api.acquire_voice(session_id, voice_token)

    try:
        await api.acquire_voice(session_id, voice_token)
        acquired = True
        lease_task = asyncio.create_task(renew_voice_lease())
        processor = SpeakingProcessor(api, session_id)
        await api.get(session_id)
        key = require('SONIOX_API_KEY')
        pipeline = Pipeline([
            transport.input(), SonioxSTTService(api_key=key), processor,
            SonioxTTSService(api_key=key, settings=SonioxTTSService.Settings(
                voice=require('SONIOX_VOICE_ID'))), transport.output(),
        ])
        worker = PipelineWorker(pipeline, params=PipelineParams(
            enable_metrics=True, enable_usage_metrics=True))

        @transport.event_handler('on_client_disconnected')
        async def disconnected(_transport, _client):
            await worker.cancel()

        runner = WorkerRunner(handle_sigint=False)
        await runner.add_workers(worker)
        await runner.run()
    finally:
        if lease_task is not None:
            lease_task.cancel()
            with suppress(asyncio.CancelledError):
                await lease_task
        if acquired:
            with suppress(Exception):
                await api.release_voice(session_id, voice_token)
        await api.close()


async def bot(runner_args: RunnerArguments):
    transport = await create_transport(runner_args, {
        'webrtc': lambda: TransportParams(audio_in_enabled=True, audio_out_enabled=True),
        'eval': lambda: EvalTransportParams(audio_in_enabled=True, audio_out_enabled=True),
    })
    logger.info('Starting grade 5 speaking voice session')
    await run_bot(transport, runner_args)


if __name__ == '__main__':
    from pipecat.runner.run import main
    main()
