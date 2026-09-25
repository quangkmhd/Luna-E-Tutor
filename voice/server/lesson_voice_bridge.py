"""Pipecat transport bridge for button-submitted Grade 3 turns."""

import asyncio
import logging
from collections.abc import Awaitable, Callable

import httpx
from pipecat.frames.frames import (
    BotStoppedSpeakingFrame,
    ErrorFrame,
    Frame,
    InterimTranscriptionFrame,
    TranscriptionFrame,
    VADUserStoppedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.processors.frameworks.rtvi.frames import (
    RTVIClientMessageFrame,
    RTVIServerMessageFrame,
)

from language_tts import (
    LanguageSpeechFinishedFrame,
    LanguageSynthesisStartedFrame,
    LanguageTaggedSpeechFrame,
)


logger = logging.getLogger(__name__)

_RETRYABLE_TURN_CODES = {
    'INVALID_EVALUATION', 'PROVIDER_UNAVAILABLE', 'INVALID_TEACHER_OUTPUT',
}


def _retryable_turn_code(error: httpx.HTTPStatusError) -> str | None:
    if error.response.status_code != 503:
        return None
    try:
        detail = error.response.json()['detail']
    except (ValueError, KeyError, TypeError):
        return None
    if not isinstance(detail, dict) or detail.get('retryable') is not True:
        return None
    code = detail.get('code')
    return code if isinstance(code, str) and code in _RETRYABLE_TURN_CODES else None


def _turn_failure_message(code: str) -> str:
    if code == 'INVALID_EVALUATION':
        return 'Luna chưa đánh giá được câu trả lời. Con bấm gửi lại lượt vừa nói nhé.'
    if code == 'INVALID_TEACHER_OUTPUT':
        return 'Luna chưa tạo được lời đáp. Con bấm gửi lại lượt vừa nói nhé.'
    return 'Dịch vụ của Luna đang tạm gián đoạn. Con bấm gửi lại lượt vừa nói nhé.'


class ScriptedVoiceAPI:
    def __init__(self, base_url: str, session_id: str,
                 client: httpx.AsyncClient | None = None):
        self.session_id = session_id
        self.client = client or httpx.AsyncClient(base_url=base_url, timeout=30)
        self._owns_client = client is None
        self.version = 0

    async def _post(self, path: str, data: dict | None = None) -> dict:
        response = await self.client.post(
            f'/api/sessions/{self.session_id}{path}', json=data)
        response.raise_for_status()
        payload = response.json()
        self.version = payload['session']['state_version']
        return payload

    async def start(self) -> dict:
        return await self._post('/voice/start')

    async def submit(self, text: str, turn_id: str) -> dict:
        return await self._post('/turns', {
            'turn_id': turn_id, 'learner_text': text,
            'expected_state_version': self.version, 'source': 'voice',
        })

    async def delivery_finished(self) -> dict:
        return await self._post('/voice/delivery-finished')

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()


class ScriptedVoiceBridge(FrameProcessor):
    def __init__(self, api: ScriptedVoiceAPI, *, final_timeout: float = 7.0):
        super().__init__()
        self.api = api
        self.final_timeout = final_timeout
        self.ready = False
        self.submitted = False
        self.processing = False
        self.final_text: list[str] = []
        self.retry_text: str | None = None
        self.turn_id: str | None = None
        self.seen_turn_ids: set[str] = set()
        self._timeout_task: asyncio.Task | None = None
        self._delivery_started: Callable[[int], None] | None = None

    def set_delivery_started(self, callback: Callable[[int], None]) -> None:
        self._delivery_started = callback

    async def start_lesson(self) -> None:
        self.ready = False
        try:
            payload = await self.api.start()
            await self._deliver(payload)
        except Exception:
            logger.exception('Voice lesson start failed: session_id=%s',
                             getattr(self.api, 'session_id', None))
            await self.delivery_failed()

    async def _notify(self, event: str, **data) -> None:
        await self.push_frame(RTVIServerMessageFrame(data={
            'event': event, 'payload': data,
        }))

    async def _deliver(self, payload: dict) -> None:
        output = payload['output']
        if self._delivery_started:
            self._delivery_started(len(output))
        for item in output:
            await self._notify(
                'teacher-image', image_url=item.get('image_url'),
                spoken_text=item['text'], turn_id=None,
            )
            await self.push_frame(LanguageTaggedSpeechFrame(item['text']))
        if not output:
            self.ready = bool(payload['session'].get('objective_id'))
            await self._notify('luna-turn-ready', ready=self.ready)

    async def delivery_finished(self) -> None:
        payload = await self.api.delivery_finished()
        await self._deliver(payload)

    async def delivery_failed(self) -> None:
        # The backend may already have accepted this turn. A fresh Voice
        # connection replays its pending output with a fresh Soniox stream.
        self.ready = False
        self.submitted = False
        self.final_text.clear()
        self.retry_text = None
        await self._notify(
            'luna-turn-error',
            message='Lượt nói chưa hoàn tất. Con ngắt rồi kết nối giọng nói lại nhé.',
        )
        await self._notify('luna-turn-ready', ready=False)

    async def _retryable_turn_failed(self, code: str, text: str) -> None:
        # A structured 503 from the lesson API is raised before it commits
        # the learner turn. Keep the finalized transcript for a resend.
        self.submitted = False
        self.final_text.clear()
        self.retry_text = text
        self.ready = False
        await self._notify('luna-turn-error', message=_turn_failure_message(code),
                           retryable_turn=True)
        await self._notify('luna-turn-ready', ready=False)

    async def _finish_missing(self) -> None:
        try:
            await asyncio.sleep(self.final_timeout)
            if self.submitted and not self.processing:
                self.submitted = False
                self.final_text.clear()
                await self.delivery_failed()
        except asyncio.CancelledError:
            pass

    async def _submit_final(self) -> None:
        if self.processing or not self.submitted or not self.final_text:
            return
        self.submitted = False
        self.ready = False
        if self._timeout_task:
            self._timeout_task.cancel()
            self._timeout_task = None
        text = ''.join(self.final_text).strip()
        self.final_text.clear()
        await self._submit_text(text)

    async def _submit_text(self, text: str) -> None:
        self.processing = True
        self.ready = False
        retry_code: str | None = None
        try:
            assert self.turn_id is not None
            for attempt in range(2):
                try:
                    try:
                        payload = await self.api.submit(text, self.turn_id)
                    except httpx.TransportError:
                        # A lost response can follow a committed backend turn.
                        # Reuse the same ID so the backend returns stored output.
                        payload = await self.api.submit(text, self.turn_id)
                    break
                except httpx.HTTPStatusError as error:
                    code = _retryable_turn_code(error)
                    if code is None:
                        raise
                    logger.warning('Lesson turn rejected before commit: code=%s status=503', code)
                    if attempt == 0:
                        await asyncio.sleep(0.3)
                        continue
                    retry_code = code
                    break
            if retry_code is None:
                self.retry_text = None
                await self._deliver(payload)
        except Exception:
            logger.exception('Voice turn failed: session_id=%s turn_id=%s',
                             getattr(self.api, 'session_id', None), self.turn_id)
            await self.delivery_failed()
        finally:
            self.processing = False
        if retry_code is not None:
            await self._retryable_turn_failed(retry_code, text)

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if direction == FrameDirection.DOWNSTREAM:
            if isinstance(frame, RTVIClientMessageFrame) and frame.type == 'luna.retry-turn':
                if self.retry_text is not None and not self.processing and not self.submitted:
                    await self._submit_text(self.retry_text)
                return
            if isinstance(frame, RTVIClientMessageFrame) and frame.type == 'luna.submit-turn':
                if self.ready and not self.submitted and not self.processing:
                    supplied_id = frame.data.get('turn_id') if isinstance(frame.data, dict) else None
                    turn_id = supplied_id if isinstance(supplied_id, str) and supplied_id else frame.msg_id
                    if turn_id in self.seen_turn_ids:
                        return
                    self.seen_turn_ids.add(turn_id)
                    self.turn_id = turn_id
                    self.ready = False
                    self.submitted = True
                    self._timeout_task = self.create_task(
                        self._finish_missing(), name='wait-for-soniox-final')
                    # Pipecat's Soniox service sends finalize on this frame.
                    # Only its finalized TranscriptionFrame is submitted.
                    await self.push_frame(VADUserStoppedSpeakingFrame(), FrameDirection.UPSTREAM)
                return
            if isinstance(frame, TranscriptionFrame):
                if self.submitted and frame.finalized and frame.text.strip():
                    self.final_text.append(frame.text)
                    await self._submit_final()
                return
            if isinstance(frame, InterimTranscriptionFrame):
                return
        await self.push_frame(frame, direction)


class ScriptedDeliveryObserver(FrameProcessor):
    """Acknowledge only after every queued utterance and transport stop."""

    def __init__(self, on_delivery: Callable[[], Awaitable[None]],
                 on_failure: Callable[[], Awaitable[None]] | None = None):
        super().__init__()
        self.on_delivery = on_delivery
        self.on_failure = on_failure
        self.expected = 0
        self.finished = 0
        self.started_spans = 0
        self.stopped_spans = 0
        self.acknowledging = False

    def start_delivery(self, count: int) -> None:
        self.expected = count
        self.finished = 0
        self.started_spans = 0
        self.stopped_spans = 0
        self.acknowledging = False

    async def _maybe_ack(self) -> None:
        if (self.expected and self.finished >= self.expected
                and self.started_spans and self.stopped_spans >= self.started_spans
                and not self.acknowledging):
            self.acknowledging = True
            try:
                await self.on_delivery()
            except Exception:
                logger.exception('Voice delivery acknowledgement failed')
                self.expected = 0
                if self.on_failure:
                    await self.on_failure()
            finally:
                self.acknowledging = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, LanguageSynthesisStartedFrame):
            self.started_spans += 1
        elif isinstance(frame, ErrorFrame) and self.expected:
            self.expected = 0
            if self.on_failure:
                await self.on_failure()
        elif isinstance(frame, BotStoppedSpeakingFrame):
            self.stopped_spans += 1
        elif isinstance(frame, LanguageSpeechFinishedFrame):
            self.finished += 1
        await self.push_frame(frame, direction)
        await self._maybe_ack()
