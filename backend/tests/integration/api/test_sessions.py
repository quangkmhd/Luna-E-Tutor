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
    created = api.post('/api/sessions').json()
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


def test_request_models_forbid_unknown_fields(tmp_path):
    response = client(tmp_path).post('/api/sessions', json={'api_key': 'forbidden'})
    assert response.status_code == 422
