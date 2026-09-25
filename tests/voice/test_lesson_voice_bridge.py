import asyncio

import httpx
import pytest
from pipecat.frames.frames import (
    BotStoppedSpeakingFrame, ErrorFrame, TranscriptionFrame,
    VADUserStoppedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameDirection
from pipecat.processors.frameworks.rtvi.frames import RTVIClientMessageFrame

from language_tts import LanguageSpeechFinishedFrame
from lesson_voice_bridge import ScriptedDeliveryObserver, ScriptedVoiceBridge


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
async def test_send_requests_finalize_and_waits_for_soniox_final(monkeypatch):
    api = API()
    bridge = ScriptedVoiceBridge(api)
    bridge.ready = True
    sent = []

    async def record(frame, direction=FrameDirection.DOWNSTREAM):
        sent.append((frame, direction))

    monkeypatch.setattr(bridge, 'push_frame', record)
    monkeypatch.setattr(bridge, 'create_task', lambda coro, **_kw: asyncio.create_task(coro))
    await bridge.process_frame(RTVIClientMessageFrame(
        msg_id='one', type='luna.submit-turn',
        data={'turn_id': 'visible-turn', 'text': "Yes, I'm ready."}),
        FrameDirection.DOWNSTREAM)
    assert api.submitted == []
    assert any(isinstance(frame, VADUserStoppedSpeakingFrame) for frame, _ in sent)
    await bridge.process_frame(final("Yes, I am ready."), FrameDirection.DOWNSTREAM)
    assert api.submitted == [('Yes, I am ready.', 'visible-turn')]


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
async def test_backend_503_retries_captured_transcript_with_same_turn_id(monkeypatch):
    class RecoveringAPI(API):
        async def submit(self, text, turn_id):
            self.submitted.append((text, turn_id))
            if len(self.submitted) == 1:
                response = httpx.Response(503, json={'detail': {
                    'code': 'PROVIDER_UNAVAILABLE', 'message': 'temporarily unavailable',
                    'retryable': True,
                }}, request=httpx.Request('POST', 'http://backend/turns'))
                response.raise_for_status()
            return {'output': [{'text': 'Try again.', 'kind': 'teacher', 'image_url': None}],
                    'session': {'objective_id': 'item-1'}}

    api = RecoveringAPI()
    bridge = ScriptedVoiceBridge(api)
    bridge.ready = True
    sent = []

    async def record(frame, direction=FrameDirection.DOWNSTREAM):
        sent.append(frame)

    monkeypatch.setattr(bridge, 'push_frame', record)
    monkeypatch.setattr(bridge, 'create_task', lambda coro, **_kw: asyncio.create_task(coro))
    await bridge.process_frame(RTVIClientMessageFrame(
        msg_id='one', type='luna.submit-turn', data={'turn_id': 'stable-id'}),
        FrameDirection.DOWNSTREAM)
    await bridge.process_frame(final('One, two, three.'), FrameDirection.DOWNSTREAM)
    assert api.submitted == [('One, two, three.', 'stable-id')] * 2
    assert any(getattr(frame, 'text', None) == 'Try again.' for frame in sent)
    assert not any(getattr(frame, 'data', {}).get('event') == 'luna-turn-error'
                   for frame in sent if hasattr(frame, 'data'))


@pytest.mark.asyncio
async def test_persistent_backend_503_keeps_transcript_for_explicit_retry(monkeypatch):
    class UnavailableAPI(API):
        async def submit(self, text, turn_id):
            self.submitted.append((text, turn_id))
            if len(self.submitted) > 2:
                return {'output': [{'text': 'Now letters.', 'kind': 'say', 'image_url': None}],
                        'session': {'objective_id': 'item-4'}}
            response = httpx.Response(503, json={'detail': {
                'code': 'INVALID_EVALUATION', 'message': 'could not assess',
                'retryable': True,
            }}, request=httpx.Request('POST', 'http://backend/turns'))
            response.raise_for_status()

    api = UnavailableAPI()
    bridge = ScriptedVoiceBridge(api)
    bridge.ready = True
    sent = []

    async def record(frame, direction=FrameDirection.DOWNSTREAM):
        sent.append(frame)

    monkeypatch.setattr(bridge, 'push_frame', record)
    monkeypatch.setattr(bridge, 'create_task', lambda coro, **_kw: asyncio.create_task(coro))
    await bridge.process_frame(RTVIClientMessageFrame(
        msg_id='one', type='luna.submit-turn', data={'turn_id': 'stable-id'}),
        FrameDirection.DOWNSTREAM)
    await bridge.process_frame(final('123'), FrameDirection.DOWNSTREAM)
    assert api.submitted == [('123', 'stable-id')] * 2
    assert not bridge.ready
    assert any(getattr(frame, 'data', {}).get('event') == 'luna-turn-error'
               and 'đánh giá' in frame.data['payload']['message']
               and frame.data['payload']['retryable_turn'] is True
               for frame in sent if hasattr(frame, 'data'))
    assert any(getattr(frame, 'data', {}).get('event') == 'luna-turn-ready'
               and frame.data['payload']['ready'] is False
               for frame in sent if hasattr(frame, 'data'))
    await bridge.process_frame(RTVIClientMessageFrame(
        msg_id='retry', type='luna.retry-turn', data={}), FrameDirection.DOWNSTREAM)
    assert api.submitted == [('123', 'stable-id')] * 3
    assert any(getattr(frame, 'text', None) == 'Now letters.' for frame in sent)


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
