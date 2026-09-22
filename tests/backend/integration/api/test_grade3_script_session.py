from pathlib import Path

from fastapi.testclient import TestClient

from luna_tutor.api.app import create_app
from luna_tutor.storage.session_repository import SessionRepository
from luna_tutor.api.runtime import build_runtime_app


class UnusedService:
    async def process(self, *_args, **_kwargs):
        raise AssertionError('This test only creates a session')


def test_grade3_session_starts_lesson_one_and_rejects_unknown_lesson(tmp_path: Path):
    api = TestClient(create_app(
        repository=SessionRepository(tmp_path / 'sessions.db'),
        turn_service=UnusedService(),
    ))
    lessons = api.get('/api/units/grade03.unit01/lessons')
    assert lessons.status_code == 200
    assert lessons.json() == [{'lesson': 1, 'title': 'Chào hỏi và giới thiệu tên'}]
    response = api.post('/api/sessions', json={
        'unit_id': 'grade03.unit01', 'lesson_id': 1,
    })
    assert response.status_code == 200, response.text
    session = response.json()
    assert session['lesson_id'] == 1
    assert session['stage_id'] == 'vocabulary'
    assert 'Cô là Luna' in session['messages'][0]['text']
    assert 'HELLO nghĩa là xin chào' in session['messages'][1]['text']
    assert api.get(f"/api/sessions/{session['session_id']}").json()['lesson_id'] == 1
    bad = api.post('/api/sessions', json={
        'unit_id': 'grade03.unit01', 'lesson_id': 99,
    })
    assert bad.status_code == 400


def test_grade3_fixture_session_runs_all_three_stations(tmp_path: Path):
    app = build_runtime_app({
        'ENV': 'test', 'TUTOR_LLM_MODE': 'fixture',
        'TUTOR_DATABASE_PATH': str(tmp_path / 'fixture.db'),
    })
    with TestClient(app) as api:
        session = api.post('/api/sessions', json={
            'unit_id': 'grade03.unit01', 'lesson_id': 1,
        }).json()
        visited = {session['stage_id']}
        for n in range(40):
            if session['status'] == 'completed':
                break
            response = api.post(
                f"/api/sessions/{session['session_id']}/turns",
                json={'turn_id': f'turn-{n}', 'expected_state_version': session['state_version'],
                      'learner_text': 'Hello'},
            )
            assert response.status_code == 200, response.text
            session = response.json()['session']
            visited.add(session['stage_id'])
        assert session['status'] == 'completed'
        assert visited == {'vocabulary', 'patterns', 'conversation'}
        assert all(stage not in visited for stage in ('level-02', 'level-03', 'free-talk'))
