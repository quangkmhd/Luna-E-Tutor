"""Pipecat SmallWebRTC worker for the persistent Luna English tutor."""

import os
from collections.abc import Mapping

from dotenv import load_dotenv
from loguru import logger
from luna_tutor.api.runtime import RuntimeComponents, build_runtime_components
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.evals.transport import EvalTransportParams
from pipecat.flows import ContextStrategy, ContextStrategyConfig, FlowManager
from pipecat.frames.frames import TTSSpeakFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.workers.runner import WorkerRunner

from text_flows import BoundedTeacherLLM
from voice_config import VoiceConfig, build_soniox_stt, build_soniox_tts
from voice_teaching import (
    VoiceCommitProcessor,
    VoiceTeachingExchange,
    VoiceTeachingProcessor,
)

load_dotenv(override=True)


class LunaVoiceWorker(PipelineWorker):
    """Pipeline worker with explicit session-owned resources."""

    def __init__(self, pipeline, exchange, components):
        super().__init__(
            pipeline,
            params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
        )
        self.luna_exchange = exchange
        self.luna_components = components
        self.luna_pipeline = pipeline


def _session_id(runner_args: RunnerArguments) -> str:
    body = getattr(runner_args, "body", None)
    session_id = body.get("session_id") if isinstance(body, dict) else None
    if not isinstance(session_id, str) or not session_id.strip():
        raise ValueError("SmallWebRTC request_data must include a non-empty session_id")
    return session_id.strip()


def build_voice_worker(
    transport: BaseTransport,
    runner_args: RunnerArguments,
    environment: Mapping[str, str] = os.environ,
) -> LunaVoiceWorker:
    """Build one Pipecat worker after validating its persisted lesson session."""

    session_id = _session_id(runner_args)
    components: RuntimeComponents = build_runtime_components(environment)
    stored = components.repository.get_session(session_id)
    components.curriculum_registry.get(stored.state.unit_id)

    # Provider objects come after metadata/session validation so a malformed
    # offer cannot open provider connections or mutate lesson state.
    config = VoiceConfig.from_environment(environment)
    stt = build_soniox_stt(config)
    tts = build_soniox_tts(config)
    exchange = VoiceTeachingExchange(
        service=components.turn_service,
        repository=components.repository,
        session_id=session_id,
        state=stored.state,
    )
    voice_teaching = VoiceTeachingProcessor(exchange)
    voice_commit = VoiceCommitProcessor(exchange)

    context = LLMContext()
    aggregators = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            # Grade-school learners pause inside sentences. Pipecat's 200 ms
            # default was finalizing Soniox several times inside one utterance.
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.8)),
        ),
    )
    teacher_llm = BoundedTeacherLLM(exchange, end_after_response=False)
    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            aggregators.user(),
            voice_teaching,
            teacher_llm,
            tts,
            transport.output(),
            voice_commit,
            aggregators.assistant(),
        ]
    )
    worker = LunaVoiceWorker(pipeline, exchange, components)
    exchange.worker = worker
    exchange.flow = FlowManager(
        worker=worker,
        llm=teacher_llm,
        context_aggregator=aggregators,
        transport=transport,
        context_strategy=ContextStrategyConfig(strategy=ContextStrategy.RESET),
    )

    # Deliberately attached session resources make the runner lifecycle and
    # focused integration tests observable without global registries.
    greeted = False

    @worker.rtvi.event_handler("on_client_ready")
    async def on_client_ready(_rtvi):
        nonlocal greeted
        latest = exchange.repository.get_session(exchange.session_id)
        exchange.state = latest.state
        await exchange.flow.set_node_from_config(
            {
                "name": latest.state.activity_id,
                "task_messages": [
                    {"role": "developer", "content": "Wait for the learner's speech."}
                ],
                "respond_immediately": False,
            }
        )
        if not greeted and not latest.turns and latest.state.opening_message:
            greeted = True
            await worker.queue_frame(
                TTSSpeakFrame(latest.state.opening_message, append_to_context=True)
            )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(_transport, _client):
        logger.info("Voice client connected for session {}", exchange.session_id)

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(_transport, _client):
        logger.info("Voice client disconnected for session {}", exchange.session_id)
        exchange.discard_pending()
        await worker.cancel()

    return worker


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments) -> None:
    """Initialize Flows and run one browser voice lesson."""

    worker = build_voice_worker(transport, runner_args)
    runner = WorkerRunner(handle_sigint=False)
    await runner.add_workers(worker)
    await worker.luna_exchange.flow.initialize()
    try:
        await runner.run()
    finally:
        client = worker.luna_components.client
        if client is not None:
            await client.aclose()


async def bot(runner_args: RunnerArguments):
    """Pipecat dev-runner entry point."""

    _session_id(runner_args)
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
