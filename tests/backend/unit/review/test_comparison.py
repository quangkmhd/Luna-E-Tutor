from types import SimpleNamespace

import pytest

from luna_tutor.domain.decisions import TeacherUtterance, TeachingDecision
from luna_tutor.domain.evidence import EvaluatorResult
from luna_tutor.domain.state import LessonState
from luna_tutor.review.comparison import ComparisonService


@pytest.fixture
def state():
    return LessonState(
        session_id='session-1', unit_id='grade05.unit01', state_version=3,
        stage_id='lesson-01', activity_id='lesson-01.live-in',
        objective_id='unit01.lesson01.pattern.live_in')


def evidence(turn_id, version):
    return EvaluatorResult(
        turn_id=turn_id, state_version=version, response_kind='answer',
        emotional_signals=[], objective_evidence=[], needs_clarification=False,
        ambiguity_reason=None)


class RecordingTurnService:
    def __init__(self, label):
        self.label = label
        self.states = []
        self.texts = []

    async def plan(self, state, learner_text, turn_id):
        self.states.append(state)
        self.texts.append(learner_text)
        return SimpleNamespace(
            evidence=evidence(turn_id, state.state_version),
            decision=TeachingDecision(
                feedback_action='acknowledge_and_continue', progression_action='stay'),
            teacher_request=SimpleNamespace(turn_id=turn_id),
        )

    async def respond(self, request):
        return TeacherUtterance(
            spoken_text=f'{self.label} teacher output', delivery_intent='encouraging')


@pytest.mark.asyncio
async def test_comparison_runs_same_immutable_state_through_two_full_branches(state):
    gemini = RecordingTurnService('Gemini evaluator')
    jev = RecordingTurnService('Jev evaluator')
    before = state.model_dump()

    result = await ComparisonService(gemini, jev).compare(state, 'I live city.', 'review-1')

    assert gemini.states == [state]
    assert jev.states == [state]
    assert gemini.texts == jev.texts == ['I live city.']
    assert state.model_dump() == before
    assert result.gemini.teacher_output == 'Gemini evaluator teacher output'
    assert result.jev.teacher_output == 'Jev evaluator teacher output'
    assert result.gemini.evaluator_model == 'google/gemini-3.5-flash-lite'
    assert result.jev.evaluator_model == '~typesafe/jev-latest'
    assert result.teacher_model == 'google/gemini-3.5-flash-lite'
    assert result.state_version == state.state_version


@pytest.mark.asyncio
async def test_comparison_returns_plan_teacher_and_total_latency(state):
    result = await ComparisonService(
        RecordingTurnService('Gemini'), RecordingTurnService('Jev'),
    ).compare(state, 'Hello', 'review-2')

    for branch in (result.gemini, result.jev):
        assert branch.planning_latency_ms >= 0
        assert branch.teacher_latency_ms >= 0
        assert branch.total_latency_ms >= branch.planning_latency_ms
        assert branch.total_latency_ms >= branch.teacher_latency_ms
