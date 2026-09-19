"""Text-only Pipecat adapter for the existing atomic teaching service.

Each HTTP turn owns a short-lived worker. SQLite remains the session authority,
so reconnects and concurrent requests cannot inherit another worker's context.
This module performs no audio initialization or speech-provider calls.
"""

from luna_tutor.domain.decisions import CompletedTurn
from luna_tutor.domain.evidence import InputEvent, TranscriptStatus
from luna_tutor.domain.state import LessonState
from luna_tutor.teaching.turn_service import TurnService
from pipecat.frames.frames import EndFrame, Frame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineWorker
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.workers.runner import WorkerRunner

from text_frames import CompletedTeachingFrame, LearnerTextFrame, TextResultProcessor


class TeachingProcessor(FrameProcessor):
    def __init__(self, service):
        super().__init__()
        self.service = service
        self.error: Exception | None = None

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, LearnerTextFrame) and direction == FrameDirection.DOWNSTREAM:
            try:
                metadata = ({'transcript_status': frame.transcript_status}
                            if frame.transcript_status != 'final' else {})
                if frame.input_event != 'transcript':
                    metadata['input_event'] = frame.input_event
                completed = await self.service.process(frame.state, frame.text, frame.turn_id, **metadata)
            except Exception as error:
                # Preserve the application's safe typed error for the HTTP layer.
                # No CompletedTeachingFrame means no state can be committed.
                self.error = error
            else:
                await self.push_frame(CompletedTeachingFrame(completed), direction)
        else:
            await self.push_frame(frame, direction)


class PipecatTurnService:
    def __init__(self, turn_service):
        self.turn_service = turn_service

    async def process(self, state: LessonState, learner_text: str, turn_id: str,
                      *, transcript_status: TranscriptStatus = 'final',
                      input_event: InputEvent = 'transcript') -> CompletedTurn:
        if isinstance(self.turn_service, TurnService):
            from text_flows import run_teaching_flow
            return await run_teaching_flow(self.turn_service, state, learner_text, turn_id,
                                           transcript_status=transcript_status, input_event=input_event)
        # Small process-only fixtures use this adapter; production always uses Flows above.
        teaching = TeachingProcessor(self.turn_service)
        result = TextResultProcessor()
        worker = PipelineWorker(
            Pipeline([teaching, result]), enable_rtvi=False,
            enable_turn_tracking=False, idle_timeout_secs=None,
        )
        runner = WorkerRunner(handle_sigint=False)
        await runner.add_workers(worker)
        await worker.queue_frames([LearnerTextFrame(state, learner_text, turn_id, transcript_status, input_event), EndFrame()])
        await runner.run()
        if teaching.error is not None:
            raise teaching.error
        if len(result.turns) != 1:
            raise RuntimeError('Text pipeline must produce exactly one completed teaching turn')
        return result.turns[0]
