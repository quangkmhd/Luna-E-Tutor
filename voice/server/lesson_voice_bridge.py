"""Pipecat transport bridge for button-submitted Grade 3 turns.

The backend owns Jev, Teacher history, and lesson progression. This processor
only finalizes Soniox on a client submit and delivers authored/Teacher speech.
"""

import asyncio
import time
from collections.abc import Awaitable, Callable

import httpx
from pipecat.frames.frames import (
    BotStoppedSpeakingFrame,
    ErrorFrame,
    Frame,
    InputAudioRawFrame,
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


class ManualAudioDrainGate(FrameProcessor):
    """Forward Send only after incoming WebRTC audio has gone quiet.

    Audio RTP and the RTVI data channel have no shared ordering. A client
    message can reach the pipeline before its final audio packet. This gate
    uses the observed audio stream to delay Soniox finalize until the media
    tail has crossed the STT boundary.
    """

    def __init__(self, quiet_seconds: float = 0.25):
        super().__init__()
        self.quiet_seconds = quiet_seconds
        self._last_audio = 0.0
        self._audio_arrived = asyncio.Event()
        self._pending = False

    async def _drain(self, frame: RTVIClientMessageFrame) -> None:
        try:
            while True:
                remaining = self.quiet_seconds - (time.monotonic() - self._last_audio)
                if remaining <= 0:
                    break
                self._audio_arrived.clear()
                try:
                    await asyncio.wait_for(self._audio_arrived.wait(), timeout=remaining)
                except TimeoutError:
                    pass
            await self.push_frame(frame)
        finally:
            self._pending = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if direction == FrameDirection.DOWNSTREAM:
            if isinstance(frame, InputAudioRawFrame):
                self._last_audio = time.monotonic()
                self._audio_arrived.set()
            elif isinstance(frame, RTVIClientMessageFrame) and frame.type == 'luna.submit-turn':
                if not self._pending:
                    self._pending = True
                    self.create_task(self._drain(frame), name='drain-webrtc-audio-before-finalize')
                return
        await self.push_frame(frame, direction)


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
        await self._notify(
            'luna-turn-error',
            message='Lượt nói chưa hoàn tất. Con ngắt rồi kết nối giọng nói lại nhé.',
        )
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
        self.processing = True
        self.submitted = False
        self.ready = False
        if self._timeout_task:
            self._timeout_task.cancel()
            self._timeout_task = None
        text = ''.join(self.final_text).strip()
        self.final_text.clear()
        try:
            assert self.turn_id is not None
            try:
                payload = await self.api.submit(text, self.turn_id)
            except httpx.TransportError:
                # A lost response can follow a committed backend turn. Reuse
                # the same ID so the backend returns its stored output.
                payload = await self.api.submit(text, self.turn_id)
            await self._deliver(payload)
        except Exception:
            await self.delivery_failed()
        finally:
            self.processing = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if direction == FrameDirection.DOWNSTREAM:
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
                    # Soniox is in Pipecat endpoint mode. Its built-in handler
                    # converts this frame into the provider's finalize request.
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
