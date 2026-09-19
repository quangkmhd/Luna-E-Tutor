from fastapi.testclient import TestClient

from luna_tutor.api.app import create_app
from luna_tutor.domain.state import LessonState, ObjectiveProgress, ReviewItem
from luna_tutor.storage.session_repository import SessionRepository

from .helpers import FakeTurnService


def test_abandon_preserves_history_and_new_session_starts_fresh(tmp_path):
    repository = SessionRepository(tmp_path / 'sessions.sqlite3')
    api = TestClient(create_app(repository=repository, turn_service=FakeTurnService()))
    first = api.post('/api/sessions').json()
    turn = {'turn_id': 'one', 'expected_state_version': 0, 'learner_text': 'Hello'}
    api.post(f"/api/sessions/{first['session_id']}/turns", json=turn)
    abandoned = api.post(f"/api/sessions/{first['session_id']}/abandon").json()
    second = api.post('/api/sessions').json()
    assert abandoned['status'] == 'abandoned'
    assert len(abandoned['messages']) == 3
    assert second['stage_id'] == 'warm-up' and second['state_version'] == 0
    assert len(api.get('/api/sessions').json()) == 2


def test_finish_rejected_before_free_talk(tmp_path):
    repository = SessionRepository(tmp_path / 'sessions.sqlite3')
    api = TestClient(create_app(repository=repository, turn_service=FakeTurnService()))
    session = api.post('/api/sessions').json()
    response = api.post(f"/api/sessions/{session['session_id']}/finish",
                        json={'expected_state_version': 0})
    assert response.status_code == 409
    assert response.json()['detail']['code'] == 'NOT_IN_FREE_TALK'


def test_finish_free_talk_returns_evidence_based_summary_and_is_idempotent(tmp_path):
    repository = SessionRepository(tmp_path / 'sessions.sqlite3')
    state = LessonState(
        session_id='free-session', unit_id='grade05.unit01', state_version=3,
        stage_id='free-talk', activity_id='free-talk.conversation',
        objective_progress=(
            ObjectiveProgress(objective_id='independent', attempted=True,
                              independent_uses=1),
            ObjectiveProgress(objective_id='supported', attempted=True,
                              supported_uses=1),
            ObjectiveProgress(objective_id='review', attempted=True,
                              needs_review=True),
        ),
        review_queue=(ReviewItem(objective_id='review', difficulty='target_form'),),
    )
    repository.create_session(state)
    api = TestClient(create_app(repository=repository, turn_service=FakeTurnService()))
    first = api.post('/api/sessions/free-session/finish',
                     json={'expected_state_version': 3})
    second = api.post('/api/sessions/free-session/finish',
                      json={'expected_state_version': 3})
    assert first.status_code == second.status_code == 200
    body = first.json()
    assert body['status'] == 'completed'
    assert body['summary']['demonstrated'] == ['independent']
    assert body['summary']['supported'] == ['supported']
    assert body['summary']['needs_review'] == ['review']
    assert second.json()['state_version'] == body['state_version'] == 4
