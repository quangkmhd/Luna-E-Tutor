from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from luna_tutor.api.app import create_app
from luna_tutor.llm.openrouter import InvalidModelOutputError, ProviderError
from luna_tutor.storage.session_repository import SessionRepository

from .helpers import FakeTurnService


def setup(tmp_path, service=None):
    service = service or FakeTurnService()
    repository = SessionRepository(tmp_path / 'sessions.sqlite3')
    api = TestClient(create_app(repository=repository, turn_service=service))
    session = api.post('/api/sessions').json()
    return api, repository, service, session


def payload(session, turn_id='turn-1'):
    return {'turn_id': turn_id, 'expected_state_version': session['state_version'],
            'learner_text': 'Hello, Luna!'}


def test_turn_is_committed_and_duplicate_returns_existing_result(tmp_path):
    api, repository, service, session = setup(tmp_path)
    first = api.post(f"/api/sessions/{session['session_id']}/turns",
                     json=payload(session))
    second = api.post(f"/api/sessions/{session['session_id']}/turns",
                      json=payload(session))
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert service.calls == ['turn-1']
    assert len(repository.get_session(session['session_id']).turns) == 1


def test_stale_version_is_conflict_and_does_not_call_model(tmp_path):
    api, _, service, session = setup(tmp_path)
    request = payload(session)
    request['expected_state_version'] = 7
    response = api.post(f"/api/sessions/{session['session_id']}/turns", json=request)
    assert response.status_code == 409
    assert response.json()['detail']['code'] == 'STATE_CONFLICT'
    assert service.calls == []


def test_two_different_turns_at_same_version_commit_only_one(tmp_path):
    api, repository, _, session = setup(tmp_path, FakeTurnService(delay=.05))
    url = f"/api/sessions/{session['session_id']}/turns"
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda turn: api.post(url, json=payload(session, turn)),
                                  ['turn-a', 'turn-b']))
    assert sorted(item.status_code for item in responses) == [200, 409]
    assert len(repository.get_session(session['session_id']).turns) == 1


def test_provider_failures_are_retryable_and_do_not_mutate_state(tmp_path):
    for error, code in [
        (ProviderError(status_code=503, request_id='turn-1', reason='down'),
         'PROVIDER_UNAVAILABLE'),
        (InvalidModelOutputError(status_code=200, request_id='turn-1', reason='bad'),
         'INVALID_EVALUATION'),
    ]:
        api, repository, _, session = setup(tmp_path / code, FakeTurnService(error=error))
        response = api.post(f"/api/sessions/{session['session_id']}/turns",
                            json=payload(session))
        assert response.status_code == 503
        assert response.json()['detail'] == {
            'code': code,
            'message': ('The tutor service is temporarily unavailable.'
                        if code == 'PROVIDER_UNAVAILABLE'
                        else 'The tutor could not assess that turn.'),
            'retryable': True,
        }
        stored = repository.get_session(session['session_id'])
        assert stored.state.state_version == 0
        assert stored.turns == ()


def test_invalid_teacher_output_is_retryable_without_committing(tmp_path):
    from luna_tutor.llm.teacher import InvalidTeacherResultError
    error = InvalidTeacherResultError(status_code=200, request_id='turn-1', reason='invalid reply')
    api, repository, _, session = setup(tmp_path, FakeTurnService(error=error))
    response = api.post(f"/api/sessions/{session['session_id']}/turns", json=payload(session))
    assert response.status_code == 503
    assert response.json()['detail']['code'] == 'INVALID_TEACHER_OUTPUT'
    assert response.json()['detail']['retryable']
    stored = repository.get_session(session['session_id'])
    assert stored.state.state_version == 0
    assert stored.turns == ()
