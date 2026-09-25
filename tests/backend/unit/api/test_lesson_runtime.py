from fastapi.testclient import TestClient

from luna_tutor.api.lesson_runtime import build_lesson_runtime_app


def test_runtime_boots_without_provider_key_to_list_grade3_only():
    app = build_lesson_runtime_app({'ENV': 'test', 'TUTOR_LLM_MODE': 'fixture'})
    with TestClient(app) as api:
        assert [unit['id'] for unit in api.get('/api/units').json()] == ['grade03.unit01']
        assert api.get('/api/units/grade05.unit01/lessons').status_code == 404
        response = api.post('/api/sessions', json={
            'unit_id': 'grade03.unit01', 'lesson_id': 1})
        assert response.status_code == 200
    assert response.json()['messages'][0]['text'].startswith(
            "Hi. My name is Luna. I'm your English tutor.")
    assert response.json()['patterns'][:2] == ["Hi. I'm Mai.", "Hello. I'm Minh."]


def test_live_runtime_constructs_pipecat_teacher_without_calling_provider():
    app = build_lesson_runtime_app({'OPENROUTER_API_KEY': 'test-key'})
    with TestClient(app) as api:
        assert api.get('/api/units').status_code == 200
