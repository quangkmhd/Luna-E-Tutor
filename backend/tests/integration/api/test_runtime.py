import pytest
from fastapi.testclient import TestClient

from luna_tutor.api.runtime import build_runtime_app


def test_fixture_mode_is_rejected_outside_test_environment(tmp_path):
    with pytest.raises(RuntimeError, match='ENV=test'):
        build_runtime_app({
            'ENV': 'local', 'TUTOR_LLM_MODE': 'fixture',
            'TUTOR_DATABASE_PATH': str(tmp_path / 'db.sqlite3'),
        })


def test_fixture_runtime_supports_recast_and_free_talk_finish(tmp_path):
    app = build_runtime_app({
        'ENV': 'test', 'TUTOR_LLM_MODE': 'fixture',
        'TUTOR_DATABASE_PATH': str(tmp_path / 'db.sqlite3'),
    })
    with TestClient(app) as api:
        session = api.post('/api/sessions').json()
        recast = api.post(f"/api/sessions/{session['session_id']}/turns", json={
            'turn_id': 'recast', 'expected_state_version': 0,
            'learner_text': 'I live countryside.',
        })
        assert recast.status_code == 200
        assert 'I live in the countryside.' in recast.json()['session']['messages'][-1]['text']
        free = api.post(f"/api/sessions/{session['session_id']}/turns", json={
            'turn_id': 'free', 'expected_state_version': 1,
            'learner_text': 'fixture: go to free talk',
        }).json()['session']
        assert free['stage_id'] == 'free-talk'
        finished = api.post(f"/api/sessions/{session['session_id']}/finish", json={
            'expected_state_version': free['state_version'],
        })
        assert finished.status_code == 200
        assert finished.json()['status'] == 'completed'


def test_initial_greeting_records_authored_text_delivery(tmp_path):
    from luna_tutor.storage.session_repository import SessionRepository
    database = tmp_path / 'greeting.sqlite3'
    app = build_runtime_app({'ENV': 'test', 'TUTOR_LLM_MODE': 'fixture',
                             'TUTOR_DATABASE_PATH': str(database)})
    with TestClient(app) as api:
        session = api.post('/api/sessions').json()
    stored = SessionRepository(database).get_session(session['session_id'])
    greeting = next(p for p in stored.state.activity_progress
                    if p.activity_id == 'warm-up.hello')
    assert greeting.status == 'completed'
    assert stored.state.last_teacher_turn == session['messages'][0]['text']
