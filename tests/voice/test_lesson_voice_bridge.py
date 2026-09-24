import asyncio

import httpx
import pytest
from pipecat.frames.frames import (
    BotStoppedSpeakingFrame, ErrorFrame, InputAudioRawFrame, TranscriptionFrame,
    VADUserStoppedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameDirection
from pipecat.processors.frameworks.rtvi.frames import RTVIClientMessageFrame

from language_tts import LanguageSpeechFinishedFrame
from lesson_voice_bridge import ManualAudioDrainGate, ScriptedDeliveryObserver, ScriptedVoiceBridge


class API:
    def __init__(self):
        self.submitted = []

    async def submit(self, text, turn_id):
        self.submitted.append((text, turn_id))
        return {'output': [{'text': 'Try again.', 'kind': 'teacher', 'image_url': None}],
                'session': {'objective_id': 'item-1'}}


def final(text):
    return TranscriptionFrame(text=text, user_id='learner', timestamp='now', finalized=True)


@pytest.mark.asyncio
async def test_only_send_finalizes_one_soniox_turn(monkeypatch):
    api = API()
    bridge = ScriptedVoiceBridge(api)
    bridge.ready = True
    sent = []

    async def record(frame, direction=FrameDirection.DOWNSTREAM):
        sent.append((frame, direction))

    monkeypatch.setattr(bridge, 'push_frame', record)
    monkeypatch.setattr(bridge, 'create_task', lambda coro, **_kw: asyncio.create_task(coro))
    await bridge.process_frame(final('unrequested'), FrameDirection.DOWNSTREAM)
    assert api.submitted == []
    submit = RTVIClientMessageFrame(msg_id='one', type='luna.submit-turn', data={'turn_id': 'stable-id'})
    await bridge.process_frame(submit, FrameDirection.DOWNSTREAM)
    await bridge.process_frame(submit, FrameDirection.DOWNSTREAM)
    assert sum(isinstance(frame, VADUserStoppedSpeakingFrame) for frame, _ in sent) == 1
    await bridge.process_frame(final('My name is Quang.'), FrameDirection.DOWNSTREAM)
    await bridge.process_frame(final('late duplicate'), FrameDirection.DOWNSTREAM)
    assert [text for text, _ in api.submitted] == ['My name is Quang.']
    assert api.submitted[0][1] == 'stable-id'


@pytest.mark.asyncio
async def test_late_final_after_timeout_cannot_become_next_turn(monkeypatch):
    api = API()
    bridge = ScriptedVoiceBridge(api, final_timeout=0.01)
    bridge.ready = True
    sent = []

    async def record(frame, direction=FrameDirection.DOWNSTREAM):
        sent.append(frame)

    monkeypatch.setattr(bridge, 'push_frame', record)
    monkeypatch.setattr(bridge, 'create_task', lambda coro, **_kw: asyncio.create_task(coro))
    submit = RTVIClientMessageFrame(msg_id='one', type='luna.submit-turn', data={'turn_id': 'first'})
    await bridge.process_frame(submit, FrameDirection.DOWNSTREAM)
    await asyncio.sleep(0.03)
    assert not bridge.ready
    await bridge.process_frame(final('Old transcript'), FrameDirection.DOWNSTREAM)
    await bridge.process_frame(RTVIClientMessageFrame(
        msg_id='two', type='luna.submit-turn', data={'turn_id': 'second'}),
        FrameDirection.DOWNSTREAM)
    assert api.submitted == []
    assert any(getattr(frame, 'data', {}).get('event') == 'luna-turn-error'
               for frame in sent if hasattr(frame, 'data'))


@pytest.mark.asyncio
async def test_ambiguous_backend_commit_locks_voice_until_reconnect(monkeypatch):
    class LostResponseAPI(API):
        async def submit(self, text, turn_id):
            self.submitted.append((text, turn_id))
            raise httpx.TransportError('response lost')

    api = LostResponseAPI()
    bridge = ScriptedVoiceBridge(api)
    bridge.ready = True
    monkeypatch.setattr(bridge, 'push_frame', lambda *_args, **_kwargs: asyncio.sleep(0))
    monkeypatch.setattr(bridge, 'create_task', lambda coro, **_kw: asyncio.create_task(coro))
    await bridge.process_frame(RTVIClientMessageFrame(
        msg_id='one', type='luna.submit-turn', data={'turn_id': 'same-id'}),
        FrameDirection.DOWNSTREAM)
    await bridge.process_frame(final('Hello.'), FrameDirection.DOWNSTREAM)
    assert api.submitted == [('Hello.', 'same-id'), ('Hello.', 'same-id')]
    assert not bridge.ready
    await bridge.process_frame(RTVIClientMessageFrame(
        msg_id='two', type='luna.submit-turn', data={'turn_id': 'new-id'}),
        FrameDirection.DOWNSTREAM)
    assert len(api.submitted) == 2


@pytest.mark.asyncio
async def test_delivery_waits_for_last_audio_stop(monkeypatch):
    acknowledgements = []

    async def acknowledge():
        acknowledgements.append(True)

    observer = ScriptedDeliveryObserver(acknowledge)
    monkeypatch.setattr(observer, 'push_frame', lambda *_args, **_kwargs: asyncio.sleep(0))
    observer.start_delivery(2)
    observer.started_spans = 2
    await observer.process_frame(LanguageSpeechFinishedFrame(), FrameDirection.DOWNSTREAM)
    await observer.process_frame(BotStoppedSpeakingFrame(), FrameDirection.UPSTREAM)
    assert acknowledgements == []
    await observer.process_frame(LanguageSpeechFinishedFrame(), FrameDirection.DOWNSTREAM)
    assert acknowledgements == []
    await observer.process_frame(BotStoppedSpeakingFrame(), FrameDirection.UPSTREAM)
    assert acknowledgements == [True]


@pytest.mark.asyncio
async def test_tts_error_blocks_delivery_ack_and_requests_reconnect(monkeypatch):
    acknowledgements = []
    failures = []

    async def acknowledge():
        acknowledgements.append(True)

    async def fail():
        failures.append(True)

    observer = ScriptedDeliveryObserver(acknowledge, fail)
    monkeypatch.setattr(observer, 'push_frame', lambda *_args, **_kwargs: asyncio.sleep(0))
    observer.start_delivery(1)
    await observer.process_frame(ErrorFrame('Soniox TTS ended without delivered audio'),
                                 FrameDirection.UPSTREAM)
    await observer.process_frame(LanguageSpeechFinishedFrame(), FrameDirection.DOWNSTREAM)
    assert failures == [True]
    assert acknowledgements == []


@pytest.mark.asyncio
async def test_submit_waits_until_incoming_audio_tail_is_drained(monkeypatch):
    gate = ManualAudioDrainGate(quiet_seconds=0.03)
    forwarded = []

    async def record(frame, direction=FrameDirection.DOWNSTREAM):
        forwarded.append(frame)

    monkeypatch.setattr(gate, 'push_frame', record)
    monkeypatch.setattr(gate, 'create_task', lambda coro, **_kw: asyncio.create_task(coro))
    audio = InputAudioRawFrame(audio=b'\0\0', sample_rate=16000, num_channels=1)
    submit = RTVIClientMessageFrame(msg_id='t1', type='luna.submit-turn')
    await gate.process_frame(audio, FrameDirection.DOWNSTREAM)
    await gate.process_frame(submit, FrameDirection.DOWNSTREAM)
    assert submit not in forwarded
    await asyncio.sleep(0.015)
    await gate.process_frame(audio, FrameDirection.DOWNSTREAM)
    await asyncio.sleep(0.022)
    assert submit not in forwarded
    await asyncio.sleep(0.025)
    assert forwarded[-1] is submit
