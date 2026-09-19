import pytest

from luna_tutor.domain.decisions import TeacherUtterance
from luna_tutor.domain.evidence import EvaluatorResult, ObjectiveEvidence
from luna_tutor.domain.state import LessonState
from luna_tutor.teaching.engine import TeachingEngine
from luna_tutor.teaching.planner import TurnPlanner
from luna_tutor.teaching.turn_service import TurnService


class MeaningEvaluator:
    async def evaluate(self, request):
        return EvaluatorResult(turn_id=request.turn_id, state_version=request.state_version,
                               response_kind='asks_meaning', emotional_signals=[],
                               objective_evidence=[], needs_clarification=False, ambiguity_reason=None)


class Teacher:
    def __init__(self, text, mode='model'):
        self.text, self.mode = text, mode

    async def respond(self, request):
        return TeacherUtterance(spoken_text=self.text, delivery_intent='warm',
                                generation_mode=self.mode)


def city_state(unit):
    return LessonState(session_id='delivery', unit_id=unit.id, stage_id='lesson-01',
                       activity_id='lesson-01.introduce-city',
                       objective_id='unit01.lesson01.vocabulary.city')


@pytest.mark.asyncio
@pytest.mark.parametrize('invitation', [
    'City. City. A city has tall buildings. What can you see there?',
    'The word is city. City. Now you say it, Quang!',
])
async def test_delivered_models_and_response_opportunity_unlock_next_turn(unit_01, invitation):
    state = city_state(unit_01)
    service = TurnService(TurnPlanner(MeaningEvaluator(), TeachingEngine(), unit_01),
                          Teacher(invitation))
    first = await service.process(state, 'What does city mean?', 'delivery-1')
    progress = next(p for p in first.next_state.activity_progress if p.activity_id == state.activity_id)
    assert progress.model_repetitions_delivered == 2
    assert progress.response_opportunity_given
    assert first.next_state.support_given.model_spoken_recently
    assert state.activity_progress == ()

    class AnswerEvaluator:
        async def evaluate(self, request):
            return EvaluatorResult(turn_id=request.turn_id, state_version=request.state_version,
                response_kind='answer', emotional_signals=[], needs_clarification=False,
                ambiguity_reason=None, objective_evidence=[ObjectiveEvidence(
                    objective_id=state.objective_id, meaning_status='satisfied',
                    target_form_status='not_used', evidence_quote='Tall buildings.',
                    recast_needed=False, corrected_form=None)])

    second = await TurnService(TurnPlanner(AnswerEvaluator(), TeachingEngine(), unit_01),
                               Teacher('Class. Class. What class are you in?')).process(
        first.next_state, 'Tall buildings.', 'delivery-2')
    assert second.next_state.activity_id == 'lesson-01.introduce-class'
    assert second.next_state.state_version == 2
    delivered = {p.activity_id: p for p in second.next_state.activity_progress}
    assert delivered['lesson-01.introduce-city'].feedback_delivered
    assert not delivered['lesson-01.introduce-class'].feedback_delivered


@pytest.mark.asyncio
@pytest.mark.parametrize('text,mode,expected', [
    ('City. What can you see?', 'model', 1),
    ('Countryside. Countryside. What can you see?', 'model', 0),
])
async def test_delivery_never_invents_missing_target_models(unit_01, text, mode, expected):
    state = city_state(unit_01)
    result = await TurnService(TurnPlanner(MeaningEvaluator(), TeachingEngine(), unit_01),
                               Teacher(text, mode)).process(state, 'What does city mean?', 'one')
    progress = next(p for p in result.next_state.activity_progress if p.activity_id == state.activity_id)
    assert progress.model_repetitions_delivered == expected
