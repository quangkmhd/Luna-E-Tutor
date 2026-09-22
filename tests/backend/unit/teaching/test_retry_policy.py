"""Learner errors get one supported retry before the activity advances."""

import pytest

from luna_tutor.domain.evidence import EvaluatorResult, ObjectiveEvidence
from luna_tutor.domain.state import ActivityProgress, LessonState
from luna_tutor.teaching.engine import TeachingEngine
from luna_tutor.teaching.planner import TurnPlanner


class FixedEvaluator:
    def __init__(self, item):
        self.item = item

    async def evaluate(self, request):
        return EvaluatorResult(
            turn_id=request.turn_id, state_version=request.state_version,
            response_kind='answer', emotional_signals=[],
            objective_evidence=[self.item], needs_clarification=False,
            ambiguity_reason=None,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(('activity_id', 'objective_id', 'teacher_turn', 'learner',
                          'meaning', 'form', 'correction', 'next_activity'), [
    ('lesson-01.introduce-city', 'unit01.lesson01.vocabulary.city',
     'Can you say city?', 'cidy', 'not_demonstrated', 'not_used', None,
     'lesson-01.introduce-class'),
    ('lesson-01.home', 'unit01.lesson01.pattern.live_in',
     'Where do you live?', 'I live countryside.', 'satisfied',
     'error_in_target_form', 'I live in the countryside.', 'lesson-01.ask-luna'),
    ('lesson-02.favourite-animal', 'unit01.lesson02.pattern.favourite',
     'What is your favourite animal?', 'My favourite animal is pink.',
     'wrong_semantic_category', 'valid_alternative', None,
     'lesson-02.favourite-colour'),
    ('lesson-01.place-meaning', 'unit01.lesson01.vocabulary.city',
     'Which place has tall buildings: city or countryside?', 'Countryside.',
     'wrong_semantic_category', 'not_used', None, 'lesson-01.class'),
], ids=['wrong-vocabulary', 'wrong-grammar', 'wrong-word-in-sentence',
        'wrong-sentence-meaning'])
async def test_first_error_retries_target_second_error_moves_and_queues_review(
        unit_01, activity_id, objective_id, teacher_turn, learner, meaning, form,
        correction, next_activity):
    activity = next(item for item in unit_01.activities if item.id == activity_id)
    prior = []
    for item in unit_01.activities:
        if item.id == activity_id:
            break
        if item.stage_id == activity.stage_id:
            prior.append(ActivityProgress(activity_id=item.id, status='completed'))
    state = LessonState(
        session_id='retry', unit_id=unit_01.id, stage_id=activity.stage_id,
        activity_id=activity_id, objective_id=objective_id,
        last_teacher_turn=teacher_turn,
        activity_progress=(*prior, ActivityProgress(
            activity_id=activity_id, status='in_progress',
            model_repetitions_delivered=activity.completion_rule.model_repetitions,
            response_opportunity_given=True)),
    )
    item = ObjectiveEvidence(
        objective_id=objective_id, meaning_status=meaning,
        target_form_status=form, evidence_quote=learner,
        recast_needed=correction is not None, corrected_form=correction,
    )
    planner = TurnPlanner(FixedEvaluator(item), TeachingEngine(), unit_01)

    first = await planner.plan(state, learner, 'first-error')
    assert first.decision.progression_action == 'stay'
    assert first.decision.count_attempt
    assert first.proposed_next_state.activity_id == activity_id
    assert first.proposed_next_state.attempt_count == 1
    assert first.teacher_request.constraints.require_repetition
    assert first.teacher_request.activity_context.activity_id == activity_id
    move = first.teacher_request.next_teaching_move.lower()
    if activity.kind == 'vocabulary_introduction':
        assert 'another attempt' in move or 'one more attempt' in move
        assert 'choose' in move and 'wording' in move
    else:
        assert 'try again' in move

    second = await planner.plan(first.proposed_next_state, learner, 'second-error')
    assert second.decision.progression_action == 'move_to_next_objective'
    assert second.decision.support_limit_exit
    assert second.proposed_next_state.activity_id == next_activity
    assert second.proposed_next_state.attempt_count == 0
    assert objective_id in second.decision.review_queue_add
    assert not second.teacher_request.constraints.require_repetition
    move = second.teacher_request.next_teaching_move.lower()
    assert 'correct answer or model' in move
    assert teacher_turn.lower() in second.teacher_request.previous_teacher_turn.lower()
    if activity_id == 'lesson-01.place-meaning':
        assert 'tall buildings are usually in a city' in move
        assert 'class' in move


@pytest.mark.asyncio
async def test_uncertain_transcript_does_not_spend_a_retry(unit_01):
    activity_id = 'lesson-01.introduce-city'
    state = LessonState(
        session_id='retry', unit_id=unit_01.id, stage_id='lesson-01',
        activity_id=activity_id, objective_id='unit01.lesson01.vocabulary.city',
        last_teacher_turn='Can you say city?',
        activity_progress=(ActivityProgress(activity_id=activity_id,
            status='in_progress', model_repetitions_delivered=2,
            response_opportunity_given=True),),
    )
    class UncertainEvaluator:
        async def evaluate(self, request):
            return EvaluatorResult(
                turn_id=request.turn_id, state_version=request.state_version,
                response_kind='insufficient_data', emotional_signals=[],
                objective_evidence=[], needs_clarification=True,
                ambiguity_reason='STT could not capture the word reliably.',
            )

    plan = await TurnPlanner(UncertainEvaluator(), TeachingEngine(), unit_01).plan(
        state, 'ci...', 'uncertain', transcript_status='uncertain')
    assert plan.decision.progression_action == 'stay'
    assert not plan.decision.count_attempt
    assert plan.proposed_next_state.attempt_count == 0
    assert not plan.teacher_request.constraints.require_repetition


@pytest.mark.asyncio
async def test_exact_spoken_word_advances_even_if_evaluator_marks_form_not_used(unit_01):
    activity_id = 'lesson-01.introduce-city'
    objective_id = 'unit01.lesson01.vocabulary.city'
    state = LessonState(
        session_id='retry', unit_id=unit_01.id, stage_id='lesson-01',
        activity_id=activity_id, objective_id=objective_id,
        last_teacher_turn='Can you say “city”?',
        activity_progress=(ActivityProgress(
            activity_id=activity_id, status='in_progress',
            model_repetitions_delivered=2, response_opportunity_given=True,
            successful_learner_repetitions=2),),
    )
    item = ObjectiveEvidence(
        objective_id=objective_id, meaning_status='not_demonstrated',
        target_form_status='not_used', evidence_quote=None,
        recast_needed=False, corrected_form=None,
    )
    plan = await TurnPlanner(FixedEvaluator(item), TeachingEngine(), unit_01).plan(
        state, 'city', 'exact-city')
    assert plan.decision.feedback_action == 'acknowledge_and_continue'
    assert plan.decision.next_activity_id == 'lesson-01.introduce-class'
    assert not plan.decision.support_limit_exit
    assert plan.decision.mastery_updates == []
