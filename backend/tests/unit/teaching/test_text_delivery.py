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


@pytest.mark.asyncio
async def test_recent_context_is_bounded_persisted_and_shared_without_contact_data(unit_01):
    class RecordingEvaluator(MeaningEvaluator):
        def __init__(self):
            self.requests = []
        async def evaluate(self, request):
            self.requests.append(request)
            return await super().evaluate(request)
    class RecordingTeacher(Teacher):
        def __init__(self):
            super().__init__('A city has many buildings. What would you like to know?')
            self.requests = []
        async def respond(self, request):
            self.requests.append(request)
            return await super().respond(request)
    evaluator, teacher = RecordingEvaluator(), RecordingTeacher()
    service = TurnService(TurnPlanner(evaluator, TeachingEngine(), unit_01), teacher)
    state = city_state(unit_01)
    inputs = ['What is a city?', 'Does it have schools?',
              'My number is 0912 345 678.', 'Are there parks?']
    for index, text in enumerate(inputs):
        completed = await service.process(state, text, f'memory-{index}')
        state = LessonState.model_validate_json(completed.next_state.model_dump_json())
    assert len(state.recent_context) == 6
    assert state.recent_context[0].text == 'Does it have schools?'
    assert state.recent_context[-1].role == 'teacher'
    assert '0912 345 678' not in state.model_dump_json()
    assert '[REDACTED_PHONE]' in state.recent_context[2].text
    before = state.model_dump_json()
    await service.process(state, 'What about shops?', 'memory-next')
    assert evaluator.requests[-1].recent_context == list(state.recent_context)
    assert teacher.requests[-1].recent_context == state.recent_context
    assert state.model_dump_json() == before
