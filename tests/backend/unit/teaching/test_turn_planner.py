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
    assert 'Model city twice' not in plan.teacher_request.next_teaching_move
    assert 'meaning' in plan.teacher_request.next_teaching_move.lower()


@pytest.mark.asyncio
async def test_successful_answer_before_new_vocabulary_requires_encouragement(unit_01):
    from luna_tutor.domain.state import ActivityProgress, LessonState
    state = LessonState(
        session_id='natural-transition', unit_id=unit_01.id, stage_id='lesson-02',
        activity_id='lesson-02.introduce-dolphin',
        objective_id='unit01.lesson02.vocabulary.dolphin',
        last_teacher_turn='Would you see a dolphin in the ocean or on a mountain?',
        activity_progress=(ActivityProgress(
            activity_id='lesson-02.introduce-dolphin', status='in_progress',
            model_repetitions_delivered=2, response_opportunity_given=True),),
    )
    evidence = EvaluatorResult(
        turn_id='placeholder', state_version=0, response_kind='answer',
        emotional_signals=[], objective_evidence=[ObjectiveEvidence(
            objective_id='unit01.lesson02.vocabulary.dolphin',
            meaning_status='satisfied', target_form_status='not_used',
            evidence_quote='dưới biển', recast_needed=False, corrected_form=None,
        )], needs_clarification=False, ambiguity_reason=None,
    )
    plan = await TurnPlanner(FakeEvaluator(evidence), TeachingEngine(), unit_01).plan(
        state, 'dưới biển', 'natural-transition')

    assert plan.teacher_request.activity_context.activity_id == 'lesson-02.introduce-pink'
    assert plan.teacher_request.constraints.model_dump().get('encouragement_required') is True


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


def test_teacher_context_requires_only_undelivered_models(unit_01):
    from luna_tutor.domain.state import LessonState, ActivityProgress
    activity = next(a for a in unit_01.activities if a.id == 'lesson-01.introduce-city')
    state = LessonState(session_id='delivery-state',unit_id=unit_01.id,stage_id=activity.stage_id,
        activity_id=activity.id,activity_progress=(ActivityProgress(activity_id=activity.id,
            model_repetitions_delivered=1,response_opportunity_given=False),))
    planner = TurnPlanner(None,TeachingEngine(),unit_01)
    context = planner._teacher_context(activity,state)
    assert context.remaining_model_repetitions == 1
    assert context.needs_response_invitation
    explanation = planner._teacher_context(activity,state,enforce_delivery=False)
    assert explanation.remaining_model_repetitions == 0
    assert not explanation.needs_response_invitation


@pytest.mark.asyncio
async def test_reduced_difficulty_requests_concrete_choice_not_normal_lesson_script(unit_01):
    from luna_tutor.domain.state import LessonState, ActivityProgress
    state = LessonState(session_id='tired', unit_id=unit_01.id, stage_id='level-03',
        activity_id='level-03.contrast', objective_id='unit01.level03.pattern.however',
        last_teacher_turn='What is one good thing and one drawback of your town?',
        activity_progress=(ActivityProgress(activity_id='level-03.contrast',
            response_opportunity_given=True),))
    evidence = EvaluatorResult(turn_id='placeholder', state_version=0,
        response_kind='does_not_know', emotional_signals=['tired'], objective_evidence=[],
        needs_clarification=False, ambiguity_reason=None)
    plan = await TurnPlanner(FakeEvaluator(evidence), TeachingEngine(), unit_01).plan(
        state, "I'm tired. I don't know.", 'tired')
    assert plan.decision.progression_action == 'reduce_difficulty'
    assert plan.decision.count_attempt is False
    directive = plan.teacher_request.next_teaching_move
    assert 'two concrete' in directive
    assert 'full sentence' in directive
    assert 'Model however as a contrast' not in directive


@pytest.mark.asyncio
async def test_successful_recast_is_not_recorded_as_exhausted_support(state, unit_01):
    plan = await TurnPlanner(FakeEvaluator(result()), TeachingEngine(), unit_01).plan(
        state, 'I live countryside', 'recast-success')
    progress = next(p for p in plan.proposed_next_state.activity_progress
                    if p.activity_id == state.activity_id)
    assert progress.status == 'completed'
    assert progress.completion_reason != 'support limit reached'
    assert plan.decision.review_queue_add == [state.objective_id]


@pytest.mark.asyncio
async def test_second_unresolved_response_records_actual_support_limit(state, unit_01):
    evidence = EvaluatorResult(turn_id='placeholder', state_version=0, response_kind='does_not_know',
        emotional_signals=[], objective_evidence=[], needs_clarification=False, ambiguity_reason=None)
    state = state.model_copy(update={'attempt_count': 1})
    plan = await TurnPlanner(FakeEvaluator(evidence), TeachingEngine(), unit_01).plan(
        state, "I don't know", 'support-limit')
    progress = next(p for p in plan.proposed_next_state.activity_progress
                    if p.activity_id == state.activity_id)
    assert progress.status == 'support_limit_reached'
    assert plan.decision.support_limit_exit


@pytest.mark.asyncio
async def test_free_talk_passes_only_selected_review_and_clears_resolved_focus(free_state, unit_01):
    from luna_tutor.domain.state import ReviewItem
    home = 'unit01.lesson01.pattern.live_in'
    traffic = 'unit01.level03.vocabulary.traffic_jam'
    state = free_state.model_copy(update={'review_queue': (
        ReviewItem(objective_id=traffic, difficulty='word_recall', learner_context='many cars slow'),)})
    item = ObjectiveEvidence(objective_id=home, meaning_status='partially_satisfied',
        target_form_status='not_used', evidence_quote='Many cars move slowly near my home.',
        recast_needed=False, corrected_form=None)
    evidence = EvaluatorResult(turn_id='placeholder', state_version=0, response_kind='answer',
        emotional_signals=[], objective_evidence=[item], needs_clarification=False, ambiguity_reason=None)
    plan = await TurnPlanner(FakeEvaluator(evidence), TeachingEngine(), unit_01).plan(
        state, item.evidence_quote, 'traffic-topic')
    assert plan.decision.next_objective_id == traffic
    assert plan.teacher_request.review_objective.objective_id == traffic
    assert 'traffic jam' in plan.teacher_request.review_objective.communicative_goal
    assert plan.teacher_request.activity_context.objectives == ()
    assert plan.teacher_request.activity_context.examples == ()  # No repeated role-entry examples.

    from luna_tutor.teaching.turn_service import TurnService
    from luna_tutor.domain.decisions import TeacherUtterance
    delivered = TurnService.complete(state, plan, TeacherUtterance(
        spoken_text='Do you often see a traffic jam there?', delivery_intent='roleplay'))
    assert delivered.next_state.support_given.model_spoken_recently
    supplied = evidence.model_copy(update={'objective_evidence': [ObjectiveEvidence(
        objective_id=traffic, meaning_status='satisfied', target_form_status='not_used',
        evidence_quote='Traffic jam.', recast_needed=False, corrected_form=None)]})
    supported = await TurnPlanner(FakeEvaluator(supplied), TeachingEngine(), unit_01).plan(
        delivered.next_state, 'Traffic jam.', 'supported-word')
    assert supported.decision.review_queue_remove == []
    assert supported.proposed_next_state.objective_progress[-1].supported_uses == 1

    state = free_state.model_copy(update={'objective_id': home, 'attempt_count': 1,
        'review_queue': (ReviewItem(objective_id=home, difficulty='target_form'),)})
    evidence = evidence.model_copy(update={'objective_evidence': [ObjectiveEvidence(
        objective_id=home, meaning_status='satisfied', target_form_status='correct_target_form',
        evidence_quote='I live in the city.', recast_needed=False, corrected_form=None)]})
    plan = await TurnPlanner(FakeEvaluator(evidence), TeachingEngine(), unit_01).plan(
        state, 'I live in the city.', 'home-resolved')
    assert plan.proposed_next_state.objective_id is None
    assert plan.proposed_next_state.attempt_count == 0
    assert plan.teacher_request.review_objective is None
    assert plan.proposed_next_state.review_queue == ()


@pytest.mark.asyncio
async def test_exhausted_existing_review_is_not_immediately_selected_again(free_state, unit_01):
    from luna_tutor.domain.state import ReviewItem
    home = 'unit01.lesson01.pattern.live_in'
    state = free_state.model_copy(update={'objective_id': home, 'attempt_count': 1,
        'applied_turn_ids': ('old-turn', 'intervening-turn'),
        'review_queue': (ReviewItem(objective_id=home, difficulty='target_form',
            learner_context='city', last_seen_turn_id='old-turn'),)})
    evidence = EvaluatorResult(turn_id='placeholder', state_version=0, response_kind='answer',
        emotional_signals=[], objective_evidence=[ObjectiveEvidence(objective_id=home,
            meaning_status='satisfied', target_form_status='not_used', evidence_quote='City.',
            recast_needed=False, corrected_form=None)], needs_clarification=False, ambiguity_reason=None)
    planner = TurnPlanner(FakeEvaluator(evidence), TeachingEngine(), unit_01)
    first = await planner.plan(state, 'City.', 'exhausted-now')
    assert first.proposed_next_state.objective_id is None
    assert first.proposed_next_state.review_queue[0].last_seen_turn_id == 'exhausted-now'
    second = await planner.plan(first.proposed_next_state, 'City.', 'next-turn')
    assert second.decision.next_objective_id is None
