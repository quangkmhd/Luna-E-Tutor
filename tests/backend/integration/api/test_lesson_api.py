from fastapi.testclient import TestClient
from openai import APIConnectionError

from luna_tutor.api.lesson_api import create_lesson_api
from luna_tutor.curriculum.lesson_content import ScriptedLesson
from luna_tutor.llm.jev_turn_evaluator import TurnEvaluation
from luna_tutor.llm.openrouter import InvalidModelOutputError
from luna_tutor.teaching.lesson_sessions import ScriptedSessionStore


class Evaluator:
    async def evaluate_turn(self, **_kwargs):
        return TurnEvaluation.PASSED


class Teacher:
    def record_say(self, _text):
        pass

    def record_query(self, _text):
        pass

    def jev_history(self):
        return []


class Catalog:
    unit = {'id': 'grade03.unit01', 'grade': 3, 'unit': 1, 'title': 'Hello'}

    def load(self, _unit_id, _lesson_id):
        return ScriptedLesson.model_validate({
            'lesson': 1, 'title': 'Hello', 'items': [
                {'type': 'practice', 'say': 'Say hello.', 'learner_goal': 'Say Hello.'},
                {'type': 'end', 'say': 'Done.'},
            ]})


def client():
    catalog = Catalog()
    catalog.units = lambda: [catalog.unit]
    catalog.lessons = lambda unit_id: [{'lesson': 1, 'title': 'Hello'}]
    store = ScriptedSessionStore(catalog, lambda: Evaluator(), lambda: Teacher())
    return TestClient(create_lesson_api(catalog, store))


def test_text_api_uses_grade3_only_and_forgets_closed_session():
    api = client()
    assert api.get('/api/units').json() == [
        {'id': 'grade03.unit01', 'grade': 3, 'unit': 1, 'title': 'Hello'}]
    assert api.get('/api/units/grade03.unit01/lessons').json() == [
        {'lesson': 1, 'title': 'Hello'}]
    assert api.get('/api/units/grade05.unit01/lessons').status_code == 404
    created = api.post('/api/sessions', json={
        'unit_id': 'grade03.unit01', 'lesson_id': 1}).json()
    assert created['messages'] == [{'role': 'teacher', 'text': 'Say hello.'}]
    result = api.post(f"/api/sessions/{created['session_id']}/turns", json={
        'turn_id': 't1', 'learner_text': 'Hello',
        'expected_state_version': created['state_version'],
    })
    assert result.status_code == 200, result.text
    assert [item['text'] for item in result.json()['session']['messages']] == [
        'Say hello.', 'Hello', 'Done.']
    assert result.json()['session']['status'] == 'completed'
    assert api.post(f"/api/sessions/{created['session_id']}/abandon").status_code == 200
    assert api.get(f"/api/sessions/{created['session_id']}").status_code == 404


def test_voice_api_requires_replay_and_delivery_ack_before_next_turn():
    api = client()
    created = api.post('/api/sessions', json={
        'unit_id': 'grade03.unit01', 'lesson_id': 1}).json()
    session_id = created['session_id']
    assert api.post(f'/api/sessions/{session_id}/voice/start').json()['output'] == [
        {'text': 'Say hello.', 'kind': 'say', 'image_url': None}]
    early = api.post(f'/api/sessions/{session_id}/turns', json={
        'turn_id': 't1', 'learner_text': 'Hello', 'expected_state_version': 0, 'source': 'voice'})
    assert early.status_code == 409
    api.post(f'/api/sessions/{session_id}/voice/delivery-finished')
    response = api.post(f'/api/sessions/{session_id}/turns', json={
        'turn_id': 't1', 'learner_text': 'Hello', 'expected_state_version': 0, 'source': 'voice'})
    assert response.status_code == 200, response.text
    assert response.json()['output'][0]['text'] == 'Done.'
    assert response.json()['session']['status'] == 'active'
    final = api.post(f'/api/sessions/{session_id}/voice/delivery-finished')
    assert final.json()['session']['status'] == 'completed'


def test_teacher_provider_failure_is_retryable_without_advancing_session(caplog):
    class FailedEvaluator(Evaluator):
        async def evaluate_turn(self, **_kwargs):
            return TurnEvaluation.ATTEMPT_FAILED

    class FailedTeacher(Teacher):
        def snapshot(self):
            return []

        def restore(self, _messages):
            pass

        async def respond(self, _instruction):
            raise APIConnectionError(request=None)

    catalog = Catalog()
    catalog.units = lambda: [catalog.unit]
    catalog.lessons = lambda _unit_id: [{'lesson': 1, 'title': 'Hello'}]
    store = ScriptedSessionStore(catalog, FailedEvaluator, FailedTeacher)
    api = TestClient(create_lesson_api(catalog, store))
    created = api.post('/api/sessions', json={
        'unit_id': 'grade03.unit01', 'lesson_id': 1}).json()
    session_id = created['session_id']
    response = api.post(f'/api/sessions/{session_id}/turns', json={
        'turn_id': 't1', 'learner_text': 'Wrong', 'expected_state_version': 0})
    assert response.status_code == 503
    assert response.json()['detail']['retryable'] is True
    assert api.get(f'/api/sessions/{session_id}').json()['state_version'] == 0
    assert f'session_id={session_id} turn_id=t1 stage=teacher' in caplog.text
    assert 'type=APIConnectionError' in caplog.text


def test_jev_failure_log_identifies_stage_without_learner_text(caplog):
    class FailedEvaluator(Evaluator):
        async def evaluate_turn(self, **_kwargs):
            raise InvalidModelOutputError(
                status_code=200, request_id='t1',
                reason='Missing Jev turn_evaluation choice')

    catalog = Catalog()
    catalog.units = lambda: [catalog.unit]
    catalog.lessons = lambda _unit_id: [{'lesson': 1, 'title': 'Hello'}]
    store = ScriptedSessionStore(catalog, FailedEvaluator, Teacher)
    api = TestClient(create_lesson_api(catalog, store))
    created = api.post('/api/sessions', json={
        'unit_id': 'grade03.unit01', 'lesson_id': 1}).json()
    session_id = created['session_id']
    response = api.post(f'/api/sessions/{session_id}/turns', json={
        'turn_id': 't1', 'learner_text': 'private learner text',
        'expected_state_version': 0})
    assert response.status_code == 503
    assert f'session_id={session_id} turn_id=t1 stage=jev' in caplog.text
    assert 'reason=Missing Jev turn_evaluation choice' in caplog.text
    assert 'private learner text' not in caplog.text
