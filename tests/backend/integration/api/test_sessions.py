from pathlib import Path

from fastapi.testclient import TestClient
from luna_tutor.api.app import create_app
from luna_tutor.storage.session_repository import SessionRepository


class UnusedTurnService:
    async def process(self, *_):
        raise AssertionError('turn service should not be called')


def client(tmp_path: Path) -> TestClient:
    repository = SessionRepository(tmp_path / 'sessions.sqlite3')
    return TestClient(create_app(repository=repository, turn_service=UnusedTurnService()))


def test_create_session_starts_at_warmup_and_lists_history(tmp_path):
    api = client(tmp_path)
    created = api.post(
        '/api/sessions', json={'unit_id': 'grade05.unit01'}).json()
    assert created['stage_id'] == 'warm-up'
    assert created['state_version'] == 0
    assert created['status'] == 'active'
    assert created['messages'][0]['role'] == 'teacher'
    listing = api.get('/api/sessions')
    assert listing.status_code == 200
    assert listing.json()[0]['session_id'] == created['session_id']


def test_get_missing_session_returns_stable_404(tmp_path):
    response = client(tmp_path).get('/api/sessions/missing')
    assert response.status_code == 404
    assert response.json()['detail']['code'] == 'SESSION_NOT_FOUND'


def test_reset_session_deletes_every_previous_session(tmp_path):
    api = client(tmp_path)
    first = api.post(
        '/api/sessions', json={'unit_id': 'grade05.unit01'}).json()
    second = api.post(
        '/api/sessions', json={'unit_id': 'grade05.unit01'}).json()

    fresh = api.post(
        '/api/sessions/reset', json={'unit_id': 'grade05.unit02'}).json()

    assert fresh['session_id'] not in {first['session_id'], second['session_id']}
    assert fresh['state_version'] == 0
    assert fresh['unit_id'] == 'grade05.unit02'
    assert api.get(f"/api/sessions/{first['session_id']}").status_code == 404
    assert api.get(f"/api/sessions/{second['session_id']}").status_code == 404
    listing = api.get('/api/sessions').json()
    assert [item['session_id'] for item in listing] == [fresh['session_id']]


def test_request_models_forbid_unknown_fields(tmp_path):
    response = client(tmp_path).post('/api/sessions', json={'api_key': 'forbidden'})
    assert response.status_code == 422


def test_historical_session_keeps_original_opening_text(tmp_path):
    from luna_tutor.domain.state import LessonState
    repository = SessionRepository(tmp_path / 'old.sqlite3')
    repository.create_session(LessonState(session_id='old-session', unit_id='grade05.unit01',
        stage_id='warm-up', activity_id='warm-up.hello',
        last_teacher_turn="Hello, Quang! I'm Luna. It's lovely to see you today!"))
    api = TestClient(create_app(repository=repository, turn_service=UnusedTurnService()))
    old = api.get('/api/sessions/old-session').json()
    new = api.post(
        '/api/sessions', json={'unit_id': 'grade05.unit01'}).json()
    assert old['messages'][0]['text'] == "Hello, Quang! I'm Luna. It's lovely to see you today!"
    assert new['messages'][0]['text'] != old['messages'][0]['text']
    assert repository.get_session(new['session_id']).state.opening_message == new['messages'][0]['text']


def test_session_messages_hide_language_markup_and_delivery_cues(tmp_path):
    from luna_tutor.domain.state import LessonState

    repository = SessionRepository(tmp_path / 'tagged.sqlite3')
    repository.create_session(LessonState(
        session_id='tagged', unit_id='grade05.unit01', stage_id='warm-up',
        activity_id='warm-up.hello',
        opening_message='<vi>Xin chào.</vi> <en>[long pause] HELLO</en>',
    ))
    api = TestClient(create_app(repository=repository, turn_service=UnusedTurnService()))

    response = api.get('/api/sessions/tagged')
    assert response.status_code == 200
    assert response.json()['messages'][0]['text'] == 'Xin chào.  HELLO'
