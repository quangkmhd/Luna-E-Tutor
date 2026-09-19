import pytest

from luna_tutor.domain.evidence import EvaluatorResult, ObjectiveEvidence
from luna_tutor.teaching.engine import TeachingEngine
from luna_tutor.teaching.planner import TurnPlanner


class FakeEvaluator:
    def __init__(self, result):
        self.result = result
        self.requests = []

    async def evaluate(self, request):
        self.requests.append(request)
        return self.result.model_copy(update={
            'turn_id': request.turn_id,
            'state_version': request.state_version,
        })


def result():
    return EvaluatorResult(
        turn_id='placeholder', state_version=0, response_kind='answer',
        emotional_signals=[], objective_evidence=[ObjectiveEvidence(
            objective_id='unit01.lesson01.pattern.live_in',
            meaning_status='satisfied', target_form_status='error_in_target_form',
            evidence_quote='I live countryside', recast_needed=True,
            corrected_form='I live in the countryside.',
        )], needs_clarification=False, ambiguity_reason=None,
    )


@pytest.mark.asyncio
async def test_planner_redacts_then_evaluates_decides_and_proposes_state(state, unit_01):
    evaluator = FakeEvaluator(result())
    planner = TurnPlanner(evaluator, TeachingEngine(), unit_01)
    plan = await planner.plan(state, 'I live countryside. My number is 0912 345 678.', 'turn-7')
    assert evaluator.requests == []
    assert plan.privacy_event
    assert plan.evidence.turn_id == 'turn-7'
    assert plan.decision.feedback_action == 'privacy_redirect'
    assert plan.teacher_request.feedback_action == 'privacy_redirect'
    assert plan.proposed_next_state.state_version == state.state_version + 1
    assert plan.proposed_next_state.applied_turn_ids[-1] == 'turn-7'
    assert state.state_version == 0
    assert state.applied_turn_ids == ()


@pytest.mark.asyncio
async def test_planner_rejects_duplicate_turn_before_evaluation(state, unit_01):
    evaluator = FakeEvaluator(result())
    planner = TurnPlanner(evaluator, TeachingEngine(), unit_01)
    duplicate = state.model_copy(update={'applied_turn_ids': ('turn-7',)})
    with pytest.raises(ValueError, match='duplicate'):
        await planner.plan(duplicate, 'I live in the city.', 'turn-7')
    assert evaluator.requests == []
