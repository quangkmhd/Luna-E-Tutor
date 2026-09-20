"""Standalone Pipecat worker for Luna's independent Free Talk room."""

import os
from collections.abc import Mapping
from typing import cast

from dotenv import load_dotenv
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.evals.transport import EvalTransportParams
from pipecat.frames.frames import LLMMessagesAppendFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext, LLMContextMessage
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.services.google.llm import GoogleLLMService
from pipecat.services.soniox.stt import SonioxSTTService
from pipecat.services.soniox.tts import SonioxTTSService
from pipecat.transcriptions.language import Language
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.workers.runner import WorkerRunner

from free_talk.prompts import build_free_talk_opening_message, build_free_talk_system_prompt
from session_config import TalkSessionConfig, parse_talk_session_config
from voice_config import TalkVoiceConfig

load_dotenv(override=True)


class TalkVoiceWorker(PipelineWorker):
    """Pipeline worker that exposes its normalized topic for verification."""

    def __init__(self, pipeline: Pipeline, session: TalkSessionConfig):
        super().__init__(
            pipeline,
            params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
        )
        self.talk_session = session


def parse_runner_config(runner_args: RunnerArguments) -> TalkSessionConfig:
    """Normalize Talk metadata before constructing external services."""
    body = getattr(runner_args, "body", None)
    return parse_talk_session_config(body if isinstance(body, dict) else {})


def compose_talk_pipeline_processors(*, input, stt, user, llm, tts, output, assistant):
    """Return the canonical cascade with the assistant aggregator last."""
    return [input, stt, user, llm, tts, output, assistant]


def build_talk_worker(
    transport: BaseTransport,
    runner_args: RunnerArguments,
    environment: Mapping[str, str] = os.environ,
) -> TalkVoiceWorker:
    """Build one isolated Free Talk worker from validated request metadata."""
    session = parse_runner_config(runner_args)
    config = TalkVoiceConfig.from_environment(environment)

    stt = SonioxSTTService(
        api_key=config.soniox_api_key,
        vad_force_turn_endpoint=True,
        settings=SonioxSTTService.Settings(
            model="stt-rt-v5",
            language_hints=[Language.EN, Language.VI],
            language_hints_strict=False,
        ),
    )
    llm = GoogleLLMService(
        api_key=config.gemini_api_key,
        settings=GoogleLLMService.Settings(
            model=config.llm_model,
            system_instruction=build_free_talk_system_prompt(),
        ),
    )
    tts = SonioxTTSService(
        api_key=config.soniox_api_key,
        settings=SonioxTTSService.Settings(
            model="tts-rt-v2",
            voice=config.voice_id,
            language=Language.EN,
            speed=0.8,
        ),
    )

    aggregators = LLMContextAggregatorPair(
        LLMContext(),
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.8)),
        ),
    )
    pipeline = Pipeline(
        compose_talk_pipeline_processors(
            input=transport.input(),
            stt=stt,
            user=aggregators.user(),
            llm=llm,
            tts=tts,
            output=transport.output(),
            assistant=aggregators.assistant(),
        )
    )
    worker = TalkVoiceWorker(pipeline, session)
    greeted = False

    @worker.rtvi.event_handler("on_client_ready")
    async def on_client_ready(_rtvi):
        nonlocal greeted
        if greeted:
            return
        greeted = True
        opening = cast(LLMContextMessage, build_free_talk_opening_message(session.topic))
        await worker.queue_frame(
            LLMMessagesAppendFrame(
                messages=[opening],
                run_llm=True,
            )
        )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(_transport, _client):
        logger.info("Free Talk client connected for topic {}", session.topic)

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(_transport, _client):
        logger.info("Free Talk client disconnected for topic {}", session.topic)
        await worker.cancel()

    return worker


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments) -> None:
    """Build and run one browser or eval Free Talk session."""
    worker = build_talk_worker(transport, runner_args)
    runner = WorkerRunner(handle_sigint=runner_args.handle_sigint)
    await runner.add_workers(worker)
    await runner.run()


async def bot(runner_args: RunnerArguments):
    """Pipecat development-runner entry point."""
    parse_runner_config(runner_args)
    transport_params = {
        "webrtc": lambda: TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        ),
        "eval": lambda: EvalTransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        ),
    }
    transport = await create_transport(runner_args, transport_params)
    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
