import pytest
from fastapi.testclient import TestClient
from luna_tutor.api.runtime import build_runtime_app


def test_fixture_mode_is_rejected_outside_test_environment(tmp_path):
    with pytest.raises(RuntimeError, match='ENV=test'):
        build_runtime_app({
            'ENV': 'local', 'TUTOR_LLM_MODE': 'fixture',
            'TUTOR_DATABASE_PATH': str(tmp_path / 'db.sqlite3'),
        })


def test_fixture_runtime_accepts_an_overridden_e2e_web_origin(tmp_path):
    app = build_runtime_app({
        'ENV': 'test', 'TUTOR_LLM_MODE': 'fixture',
        'TUTOR_DATABASE_PATH': str(tmp_path / 'db.sqlite3'),
        'E2E_WEB_ORIGIN': 'http://localhost:3092',
    })
    with TestClient(app) as api:
        response = api.options('/api/sessions', headers={
            'Origin': 'http://localhost:3092',
            'Access-Control-Request-Method': 'POST',
        })
    assert response.headers['access-control-allow-origin'] == 'http://localhost:3092'


def test_fixture_runtime_supports_recast_and_free_talk_finish(tmp_path):
    app = build_runtime_app({
        'ENV': 'test', 'TUTOR_LLM_MODE': 'fixture',
        'TUTOR_DATABASE_PATH': str(tmp_path / 'db.sqlite3'),
    })
    with TestClient(app) as api:
        session = api.post(
            '/api/sessions', json={'unit_id': 'grade05.unit01'}).json()
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
        session = api.post(
            '/api/sessions', json={'unit_id': 'grade05.unit01'}).json()
    stored = SessionRepository(database).get_session(session['session_id'])
    greeting = next(p for p in stored.state.activity_progress
                    if p.activity_id == 'warm-up.hello')
    assert greeting.status == 'completed'
    assert stored.state.last_teacher_turn == session['messages'][0]['text']


def test_each_unit_uses_its_yaml_greeting(tmp_path):
    from pathlib import Path
    from luna_tutor.curriculum.loader import load_unit

    root = Path(__file__).resolve().parents[4] / 'curriculum'
    app = build_runtime_app({'ENV': 'test', 'TUTOR_LLM_MODE': 'fixture',
                             'TUTOR_DATABASE_PATH': str(tmp_path / 'greetings.sqlite3')})
    with TestClient(app) as api:
        for manifest in sorted(root.glob('grade-*/unit-*/unit.yaml')):
            unit = load_unit(manifest)
            response = api.post('/api/sessions', json={'unit_id': unit.id})
            assert response.status_code == 200
            if unit.id == 'grade03.unit01':
                from luna_tutor.curriculum.lesson_script import load_lesson_script
                script = load_lesson_script(
                    root / 'grade-03/unit-01/lesson-01/content.yaml')
                assert response.json()['messages'][0]['text'] == script.greeting.say
            else:
                assert response.json()['messages'][0]['text'] == unit.greeting


def test_new_session_greeting_already_opens_feelings_response(tmp_path):
    from luna_tutor.storage.session_repository import SessionRepository
    database = tmp_path / 'ready-greeting.sqlite3'
    app = build_runtime_app({'ENV': 'test', 'TUTOR_LLM_MODE': 'fixture',
                             'TUTOR_DATABASE_PATH': str(database)})
    with TestClient(app) as api:
        session = api.post(
            '/api/sessions', json={'unit_id': 'grade05.unit01'}).json()
    stored = SessionRepository(database).get_session(session['session_id'])
    assert stored.state.activity_id == 'warm-up.feelings'
    assert session['messages'][0]['text'] == "Hi! My name is Luna — I'm your English tutor!"
    assert next(p for p in stored.state.activity_progress
                if p.activity_id == 'warm-up.feelings').response_opportunity_given


def test_runtime_accepts_allowed_origins_env_variable(tmp_path):
    app = build_runtime_app({
        'ENV': 'test',
        'TUTOR_LLM_MODE': 'fixture',
        'TUTOR_DATABASE_PATH': str(tmp_path / 'db.sqlite3'),
        'ALLOWED_ORIGINS': 'https://my-app.vercel.app, https://custom-domain.com',
    })
    with TestClient(app) as api:
        response = api.options('/api/sessions', headers={
            'Origin': 'https://my-app.vercel.app',
            'Access-Control-Request-Method': 'POST',
        })
    assert response.headers['access-control-allow-origin'] == 'https://my-app.vercel.app'
