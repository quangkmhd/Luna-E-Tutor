from fastapi.testclient import TestClient

from luna_tutor.api.runtime import build_runtime_app


def client(tmp_path):
    app = build_runtime_app({'ENV': 'test', 'TUTOR_LLM_MODE': 'fixture',
                             'TUTOR_DATABASE_PATH': str(tmp_path / 'db.sqlite3')})
    return TestClient(app)


def test_topic_speaking_lifecycle_is_separate_from_unit(tmp_path):
    with client(tmp_path) as api:
        topics = api.get('/api/speaking/topics')
        assert topics.status_code == 200
        created = api.post('/api/speaking/sessions', json={
            'grade': 5, 'topic': 'Food', 'words': ['juice', 'sandwich']}).json()
        assert created['config']['topic'] == 'Food'
        assert 'unit_id' not in created
        result = api.post(f"/api/speaking/sessions/{created['session_id']}/turns", json={
            'turn_id': 't1', 'text': 'I like juice.', 'expected_version': 0})
        assert result.status_code == 200
        assert result.json()['state']['version'] == 1
        summary = api.post(f"/api/speaking/sessions/{created['session_id']}/finish", json={
            'expected_version': 1})
        assert summary.status_code == 200
        assert summary.json()['state']['status'] == 'completed'


def test_grade_four_and_stale_version_are_rejected(tmp_path):
    with client(tmp_path) as api:
        assert api.post('/api/speaking/sessions', json={
            'grade': 4, 'topic': 'Food', 'words': ['juice']}).status_code == 422
        created = api.post('/api/speaking/sessions', json={
            'grade': 5, 'topic': 'Food', 'words': ['juice']}).json()
        response = api.post(f"/api/speaking/sessions/{created['session_id']}/turns", json={
            'turn_id': 't1', 'text': 'Hello', 'expected_version': 3})
        assert response.status_code == 409


def test_word_suggestions_support_custom_topics(tmp_path):
    with client(tmp_path) as api:
        response = api.post('/api/speaking/suggestions', json={'topic': 'Space picnic'})
        assert response.status_code == 200
        assert 1 <= len(response.json()['words']) <= 8
