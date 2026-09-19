import pytest

from luna_tutor.domain.decisions import TeacherUtterance
from luna_tutor.teaching.turn_service import TurnService


class FakePlanner:
    def __init__(self, plan=None, error=None):
        self.result = plan
        self.error = error

    async def plan(self, state, learner_text, turn_id):
        if self.error:
            raise self.error
        return self.result


class FakeTeacher:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error

    async def respond(self, request):
        if self.error:
            raise self.error
        return self.result


@pytest.mark.asyncio
async def test_service_returns_atomic_completed_turn_without_mutating_original(state, unit_01):
    from luna_tutor.domain.evidence import EvaluatorResult, ObjectiveEvidence
    from luna_tutor.teaching.engine import TeachingEngine
    from luna_tutor.teaching.planner import TurnPlanner

    class Evaluator:
        async def evaluate(self, request):
            return EvaluatorResult(
                turn_id=request.turn_id, state_version=request.state_version,
                response_kind='answer', emotional_signals=[], objective_evidence=[ObjectiveEvidence(
                    objective_id=state.objective_id, meaning_status='satisfied',
                    target_form_status='correct_target_form', evidence_quote='I live in the city.',
                    recast_needed=False, corrected_form=None)],
                needs_clarification=False, ambiguity_reason=None)

    planner = TurnPlanner(Evaluator(), TeachingEngine(), unit_01)
    teacher = FakeTeacher(TeacherUtterance(
        spoken_text='Great! You live in the city. What do you like about it?',
        delivery_intent='encouraging'))
    completed = await TurnService(planner, teacher).process(
        state, 'I live in the city.', 'turn-9')
    assert completed.next_state.last_teacher_turn == teacher.result.spoken_text
    assert completed.next_state.state_version == 1
    assert completed.plan.turn_id == 'turn-9'
    assert state.state_version == 0
    assert state.applied_turn_ids == ()


@pytest.mark.asyncio
async def test_teacher_failure_yields_no_completed_turn_or_state_mutation(state):
    original = state.model_dump()
    service = TurnService(FakePlanner(error=TimeoutError('provider')), FakeTeacher())
    with pytest.raises(TimeoutError):
        await service.process(state, 'hello', 'turn-10')
    assert state.model_dump() == original
