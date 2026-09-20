import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'voice/server'))

from luna_tutor.api.runtime import FixtureTurnService
from luna_tutor.domain.state import LessonState


def initial_state():
    return LessonState(session_id='text-test', unit_id='grade05.unit01',
                       stage_id='warm-up', activity_id='warm-up.hello')


@pytest.mark.asyncio
async def test_typed_input_reaches_real_pipeline_and_returns_one_completed_turn():
    from text_pipeline import PipecatTurnService
    original = initial_state()
    completed = await PipecatTurnService(FixtureTurnService()).process(
        original, 'Hello Luna', 'typed-1')
    assert completed.plan.learner_text == 'Hello Luna'
    assert completed.next_state.state_version == 1
    assert completed.next_state.applied_turn_ids == ('typed-1',)
    assert completed.teacher_utterance.spoken_text
    assert original.state_version == 0


@pytest.mark.asyncio
async def test_provider_failure_survives_pipeline_and_does_not_mutate_state():
    from luna_tutor.llm.openrouter import ProviderError
    from text_pipeline import PipecatTurnService
    original = initial_state()
    with pytest.raises(ProviderError):
        await PipecatTurnService(FixtureTurnService()).process(
            original, 'fixture: provider failure', 'typed-2')
    assert original.state_version == 0
    assert not original.applied_turn_ids


@pytest.mark.asyncio
async def test_parallel_sessions_do_not_share_results():
    import asyncio

    from text_pipeline import PipecatTurnService
    service = PipecatTurnService(FixtureTurnService())
    a, b = await asyncio.gather(
        service.process(initial_state(), 'First learner', 'a'),
        service.process(initial_state().model_copy(update={'session_id': 'other'}),
                        'Second learner', 'b'))
    assert a.plan.learner_text == 'First learner'
    assert b.plan.learner_text == 'Second learner'
    assert a.next_state.session_id == 'text-test'
    assert b.next_state.session_id == 'other'


def test_api_uses_pipeline_and_keeps_idempotency_and_history(tmp_path):
    from fastapi.testclient import TestClient
    from luna_tutor.api.runtime import build_runtime_app
    from text_pipeline import PipecatTurnService
    app = build_runtime_app({
        'ENV': 'test', 'TUTOR_LLM_MODE': 'fixture',
        'TUTOR_DATABASE_PATH': str(tmp_path / 'pipeline.sqlite3'),
    }, turn_service_adapter=PipecatTurnService)
    with TestClient(app) as api:
        session = api.post('/api/sessions').json()
        path = f"/api/sessions/{session['session_id']}/turns"
        body = {'turn_id': 'web-text', 'expected_state_version': 0,
                'learner_text': 'I live countryside.'}
        response = api.post(path, json=body)
        assert response.status_code == 200
        updated = response.json()['session']
        assert updated['state_version'] == 1
        assert 'I live in the countryside.' in updated['messages'][-1]['text']
        duplicate = api.post(path, json=body)
        assert duplicate.status_code == 200
        assert duplicate.json()['session']['state_version'] == 1
        assert len(duplicate.json()['session']['messages']) == 3


@pytest.mark.asyncio
async def test_pipeline_preserves_uncertainty_metadata():
    from text_pipeline import PipecatTurnService
    seen = []
    class Service:
        async def process(self, state, text, turn_id, *, transcript_status='final'):
            seen.append(transcript_status)
            return await FixtureTurnService().process(state, text, turn_id)
    await PipecatTurnService(Service()).process(
        initial_state(), 'countryside', 'uncertain', transcript_status='uncertain')
    assert seen == ['uncertain']


@pytest.mark.asyncio
async def test_pipeline_preserves_explicit_no_response_event():
    from text_pipeline import PipecatTurnService
    seen = []
    class Service:
        async def process(self, state, text, turn_id, *, input_event='transcript'):
            seen.append(input_event)
            return await FixtureTurnService().process(state, text, turn_id)
    await PipecatTurnService(Service()).process(
        initial_state(), '', 'silent', input_event='no_response')
    assert seen == ['no_response']
