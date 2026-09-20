from fastapi.testclient import TestClient
from luna_tutor.api.app import create_app
from luna_tutor.domain.decisions import TeachingDecision
from luna_tutor.domain.evidence import EvaluatorResult
from luna_tutor.review.comparison import ComparisonBranch, ComparisonResult
from luna_tutor.storage.session_repository import SessionRepository


class UnusedTurnService:
    async def process(self, *_):
        raise AssertionError('normal turn service should not be called')


class FakeComparisonService:
    def __init__(self):
        self.calls = []

    async def compare(self, state, learner_text, comparison_id):
        self.calls.append((state, learner_text, comparison_id))
        evidence = EvaluatorResult(
            turn_id=f'{comparison_id}-gemini', state_version=state.state_version,
            response_kind='answer', emotional_signals=[], objective_evidence=[],
            needs_clarification=False, ambiguity_reason=None)
        decision = TeachingDecision(
            feedback_action='acknowledge_and_continue', progression_action='stay')
        common = {
            'evidence': evidence,
            'decision': decision,
            'planning_latency_ms': 10,
            'teacher_latency_ms': 20,
            'total_latency_ms': 30,
        }
        return ComparisonResult(
            state_version=state.state_version, stage_id=state.stage_id,
            activity_id=state.activity_id, learner_text=learner_text,
            gemini=ComparisonBranch(
                evaluator_model='google/gemini-3.5-flash-lite',
                teacher_output='Gemini branch teacher output', **common),
            jev=ComparisonBranch(
                evaluator_model='~typesafe/jev-latest',
                teacher_output='Jev branch teacher output',
                **(common | {'evidence': evidence.model_copy(update={
                    'turn_id': f'{comparison_id}-jev'})})),
        )


def test_review_returns_both_teacher_outputs_without_mutating_session(tmp_path):
    repository = SessionRepository(tmp_path / 'review.sqlite3')
    comparison = FakeComparisonService()
    api = TestClient(create_app(
        repository=repository, turn_service=UnusedTurnService(),
        comparison_service=comparison))
    session = api.post(
        '/api/sessions', json={'unit_id': 'grade05.unit01'}).json()

    response = api.post(f"/api/review/{session['session_id']}", json={
        'learner_text': 'I live city.',
    })

    assert response.status_code == 200
    body = response.json()
    assert body['gemini']['teacher_output'] == 'Gemini branch teacher output'
    assert body['jev']['teacher_output'] == 'Jev branch teacher output'
    assert body['teacher_model'] == 'google/gemini-3.5-flash-lite'
    unchanged = api.get(f"/api/sessions/{session['session_id']}").json()
    assert unchanged['state_version'] == session['state_version']
    assert unchanged['messages'] == session['messages']


def test_review_missing_session_is_404(tmp_path):
    api = TestClient(create_app(
        repository=SessionRepository(tmp_path / 'review.sqlite3'),
        turn_service=UnusedTurnService(), comparison_service=FakeComparisonService()))

    response = api.post('/api/review/missing', json={'learner_text': 'Hello'})

    assert response.status_code == 404
    assert response.json()['detail']['code'] == 'SESSION_NOT_FOUND'
