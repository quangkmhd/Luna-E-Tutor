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


@pytest.mark.asyncio
async def test_teacher_gets_prior_question_and_actual_next_activity_content(state, unit_01):
    state = state.model_copy(update={'last_teacher_turn': 'Where do you live?'})
    plan = await TurnPlanner(FakeEvaluator(result()), TeachingEngine(), unit_01).plan(
        state, 'I live countryside', 'context-turn')
    request = plan.teacher_request
    assert request.previous_teacher_turn == 'Where do you live?'
    assert request.activity_context.activity_id == plan.proposed_next_state.activity_id
    assert request.activity_context.stage_id == plan.proposed_next_state.stage_id
    activity = next(a for a in unit_01.activities
                    if a.id == plan.proposed_next_state.activity_id)
    assert request.activity_context.kind == activity.kind
    assert request.activity_context.examples == tuple(activity.examples)
    assert request.activity_context.objectives
    assert 'wait for his question' in request.next_teaching_move


@pytest.mark.asyncio
async def test_teacher_vocabulary_context_has_concrete_word_not_only_generic_instruction(unit_01):
    from luna_tutor.domain.state import LessonState
    state = LessonState(session_id='context', unit_id=unit_01.id, stage_id='lesson-01',
                        activity_id='lesson-01.introduce-city',
                        objective_id='unit01.lesson01.vocabulary.city',
                        last_teacher_turn='City. City. What does city mean?')
    evidence = EvaluatorResult(turn_id='placeholder', state_version=0,
                              response_kind='asks_meaning', emotional_signals=[],
                              objective_evidence=[], needs_clarification=False,
                              ambiguity_reason=None)
    plan = await TurnPlanner(FakeEvaluator(evidence), TeachingEngine(), unit_01).plan(
        state, 'What does city mean?', 'meaning-context')
    assert plan.teacher_request.activity_context.target_words == ('city',)
    assert plan.teacher_request.activity_context.model_repetitions == 2
    assert plan.teacher_request.activity_context.response_opportunity_required is True
    assert 'Model city twice' not in plan.teacher_request.next_teaching_move
    assert 'meaning' in plan.teacher_request.next_teaching_move.lower()


@pytest.mark.asyncio
async def test_uncertain_input_is_preserved_through_service(state, unit_01):
    from luna_tutor.teaching.turn_service import TurnService
    from luna_tutor.domain.decisions import TeacherUtterance
    evidence = EvaluatorResult(turn_id='placeholder', state_version=0,
        response_kind='insufficient_data', emotional_signals=[], objective_evidence=[],
        needs_clarification=True, ambiguity_reason='Input is uncertain.')
    evaluator = FakeEvaluator(evidence)
    class Teacher:
        async def respond(self, request):
            return TeacherUtterance(spoken_text='Did you mean the city or the countryside?',
                                    delivery_intent='reassuring')
    service = TurnService(TurnPlanner(evaluator, TeachingEngine(), unit_01), Teacher())
    completed = await service.process(state, 'countryside', 'uncertain', transcript_status='uncertain')
    assert evaluator.requests[0].transcript_status == 'uncertain'
    assert completed.plan.decision.count_attempt is False
    assert completed.plan.decision.progression_action == 'stay'
    assert 'confirm' in completed.plan.teacher_request.next_teaching_move
    assert 'Model' not in completed.plan.teacher_request.next_teaching_move


@pytest.mark.asyncio
async def test_free_talk_accepts_complete_unit1_objective_context(free_state, unit_01):
    evidence = EvaluatorResult(turn_id='placeholder', state_version=0, response_kind='answer',
        emotional_signals=[], objective_evidence=[], needs_clarification=False, ambiguity_reason=None)
    evaluator = FakeEvaluator(evidence)
    await TurnPlanner(evaluator, TeachingEngine(), unit_01).plan(
        free_state, 'Hello Emma! I live in the countryside.', 'free-talk-context')
    expected = next(a for a in unit_01.activities if a.id == 'free-talk.conversation').objective_ids
    assert len(expected) == 27
    assert [o.objective_id for o in evaluator.requests[0].active_objectives] == expected
