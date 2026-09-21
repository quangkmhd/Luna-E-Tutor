import pytest

from luna_tutor.domain.state import ActivityProgress, ObjectiveProgress

HOME = 'unit01.lesson01.pattern.live_in'
CITY = 'unit01.lesson01.vocabulary.city'


def test_two_failed_attempts_moves_on_and_queues_review(engine, state, evidence, unit_01):
    state = state.model_copy(update={'attempt_count': 1})
    decision = engine.decide(state, evidence(meaning='not_demonstrated', form='not_used', quote=None), unit_01)
    assert decision.progression_action == 'move_to_next_objective'
    assert decision.next_activity_id == 'lesson-01.ask-luna'
    assert decision.review_queue_add == [state.objective_id]
    assert decision.mastery_updates == []
    assert decision.count_attempt


def test_exhausted_point_does_not_allow_a_third_attempt(engine, state, evidence, unit_01):
    decision = engine.decide(state.model_copy(update={'attempt_count': 2}),
                             evidence(items=[]), unit_01)
    assert decision.progression_action == 'move_to_next_objective'
    assert not decision.count_attempt
    assert decision.review_queue_add == [HOME]


@pytest.mark.parametrize('kind', ['asks_meaning', 'asks_teacher', 'insufficient_data'])
def test_nonattempt_does_not_trigger_support_limit_exit(engine, state, evidence, unit_01, kind):
    decision = engine.decide(state.model_copy(update={'attempt_count': 1}),
                             evidence(items=[], kind=kind), unit_01)
    assert decision.progression_action == 'stay'
    assert not decision.count_attempt
    assert decision.review_queue_add == []


def test_valid_alternative_is_success_without_recast(engine, state, evidence, unit_01):
    decision = engine.decide(state, evidence(form='valid_alternative'), unit_01)
    assert decision.feedback_action == 'acknowledge_and_continue'
    assert decision.review_queue_add == []


@pytest.mark.parametrize(('models', 'opportunity', 'progression'), [
    (0, True, 'stay'), (1, True, 'stay'), (2, False, 'stay'),
    (2, True, 'move_to_next_objective'),
])
def test_word_completion_requires_delivered_models_and_response_opportunity(
        engine, state, evidence, unit_01, models, opportunity, progression):
    state = state.model_copy(update={
        'activity_id': 'lesson-01.introduce-city', 'objective_id': CITY,
        'activity_progress': (ActivityProgress(activity_id='lesson-01.introduce-city',
            status='in_progress', model_repetitions_delivered=models,
            response_opportunity_given=opportunity),),
    })
    decision = engine.decide(state, evidence(objective_id=CITY, quote='city'), unit_01)
    assert decision.progression_action == progression
    assert decision.count_attempt is (models == 2 and opportunity)
    if progression != 'stay':
        assert decision.next_activity_id == 'lesson-01.introduce-class'


@pytest.mark.parametrize(('word', 'activity_id', 'objective_id', 'next_activity'), [
    ('city', 'lesson-01.introduce-city', CITY, 'lesson-01.introduce-class'),
    ('class', 'lesson-01.introduce-class', 'unit01.lesson01.vocabulary.class',
     'lesson-01.introduce-countryside'),
])
def test_correct_imitation_completes_word_step_without_claiming_meaning(
        engine, state, evidence, unit_01, word, activity_id, objective_id, next_activity):
    prior = tuple(ActivityProgress(activity_id=item.id, status='completed')
                  for item in unit_01.activities if item.stage_id == 'lesson-01'
                  and item.id == 'lesson-01.introduce-city' and activity_id != item.id)
    state = state.model_copy(update={
        'activity_id': activity_id, 'objective_id': objective_id,
        'last_teacher_turn': f'Can you say “{word}”?',
        'activity_progress': prior + (ActivityProgress(
            activity_id=activity_id, status='in_progress',
            model_repetitions_delivered=2, response_opportunity_given=True),),
    })
    result = evidence(objective_id=objective_id, meaning='not_demonstrated',
                      form='correct_target_form', quote=word)
    decision = engine.decide(state, result, unit_01)
    assert decision.feedback_action == 'acknowledge_and_continue'
    assert decision.progression_action == 'move_to_next_objective'
    assert decision.next_activity_id == next_activity
    assert not decision.support_limit_exit
    assert decision.review_queue_add == []
    assert decision.mastery_updates == []


def test_stage_cannot_skip_unhandled_required_activity(engine, state, evidence, unit_01):
    state = state.model_copy(update={'activity_id': 'lesson-01.ask-luna', 'activity_progress': (
        ActivityProgress(activity_id='lesson-01.ask-luna', status='in_progress', response_opportunity_given=True),
    )})
    decision = engine.decide(state, evidence(kind='asks_teacher'), unit_01)
    assert decision.progression_action == 'move_to_next_objective'
    assert decision.next_activity_id == 'lesson-01.introduce-city'
    assert decision.next_stage_id is None


def test_stage_moves_after_required_activities_with_no_mastery_threshold(engine, state, evidence, unit_01):
    progress = tuple(ActivityProgress(activity_id=a.id, status='completed')
                     for a in unit_01.activities if a.stage_id == 'lesson-01' and a.id != 'lesson-01.ask-luna')
    state = state.model_copy(update={
        'activity_id': 'lesson-01.ask-luna', 'objective_id': HOME,
        'activity_progress': (*progress, ActivityProgress(activity_id='lesson-01.ask-luna',
            status='in_progress', response_opportunity_given=True)),
        'objective_progress': (ObjectiveProgress(objective_id=HOME, needs_review=True),),
    })
    decision = engine.decide(state, evidence(items=[], kind='asks_teacher'), unit_01)
    assert decision.feedback_action == 'answer_teacher_question'
    assert decision.progression_action == 'move_to_next_stage'
    assert decision.next_stage_id == 'lesson-02'
    assert decision.next_activity_id == 'lesson-02.introduce-dolphin'
    assert decision.mastery_updates == []


def test_ask_teacher_activity_cannot_finish_from_an_answer_only(engine, state, evidence, unit_01):
    state = state.model_copy(update={'activity_id': 'lesson-01.ask-luna', 'activity_progress': (
        ActivityProgress(activity_id='lesson-01.ask-luna', status='in_progress', response_opportunity_given=True),
    )})
    decision = engine.decide(state, evidence(), unit_01)
    assert decision.progression_action == 'stay'


def test_ask_teacher_can_exit_after_two_failures_without_fabricating_question(engine, state, evidence, unit_01):
    prior = tuple(ActivityProgress(activity_id=a.id, status='completed') for a in unit_01.activities
                  if a.stage_id == 'lesson-01' and a.id != 'lesson-01.ask-luna')
    state = state.model_copy(update={'activity_id': 'lesson-01.ask-luna', 'attempt_count': 1,
        'activity_progress': (*prior, ActivityProgress(activity_id='lesson-01.ask-luna',
            status='in_progress', response_opportunity_given=True))})
    decision = engine.decide(state, evidence(items=[], kind='does_not_know'), unit_01)
    assert decision.progression_action == 'move_to_next_stage'
    assert decision.review_queue_add == [HOME]
    assert decision.mastery_updates == []
    assert not state.activity_progress[-1].learner_asked_teacher


def test_free_talk_requires_all_prerequisite_stages(engine, state, evidence, unit_01):
    progress = tuple(ActivityProgress(activity_id=a.id, status='completed') for a in unit_01.activities
                     if a.stage_id == 'level-03')
    state = state.model_copy(update={'stage_id': 'level-03', 'activity_id': 'level-03.ask-luna',
        'objective_id': 'unit01.level03.pattern.describe_countryside', 'activity_progress': progress})
    decision = engine.decide(state, evidence(items=[], kind='asks_teacher'), unit_01)
    assert decision.progression_action == 'stay'
    assert decision.next_stage_id is None
    ready = state.model_copy(update={'completed_stage_ids': ('warm-up', 'lesson-01', 'lesson-02', 'lesson-03', 'level-02')})
    decision = engine.decide(ready, evidence(items=[], kind='asks_teacher'), unit_01)
    assert decision.progression_action == 'move_to_next_stage'
    assert decision.next_stage_id == 'free-talk'
    assert decision.next_objective_id is None  # No arbitrary first-vocabulary review focus.


@pytest.mark.parametrize(('activity', 'status', 'next_id'), [
    ('warm-up.hello', 'in_progress', None),
    ('warm-up.hello', 'completed', 'warm-up.feelings'),
    ('warm-up.feelings', 'in_progress', 'lesson-01.introduce-city'),
])
def test_warm_up_greeting_and_feelings_bridge_directly_to_lesson(engine, state, evidence, unit_01, activity, status, next_id):
    prior = () if activity == 'warm-up.hello' else (ActivityProgress(activity_id='warm-up.hello', status='completed'),)
    state = state.model_copy(update={'stage_id': 'warm-up', 'activity_id': activity,
        'objective_id': None, 'completed_stage_ids': (), 'activity_progress': (*prior,
            ActivityProgress(activity_id=activity, status=status, response_opportunity_given=True))})
    decision = engine.decide(state, evidence(), unit_01)
    assert decision.next_activity_id == next_id
    assert decision.next_objective_id == (CITY if activity == 'warm-up.feelings' else None)
    assert decision.mastery_updates == []
    assert not decision.count_attempt


def test_summary_can_finish_without_objective_mastery(engine, state, evidence, unit_01):
    state = state.model_copy(update={'stage_id': 'summary', 'activity_id': 'summary.reflect',
        'objective_id': None, 'activity_progress': (ActivityProgress(activity_id='summary.reflect', status='completed'),)})
    decision = engine.decide(state, evidence(items=[]), unit_01)
    assert decision.progression_action == 'finish'
    assert decision.mastery_updates == []


def test_answered_warmup_bridges_directly_to_first_learning_opportunity(engine, state, evidence, unit_01):
    state = state.model_copy(update={'stage_id': 'warm-up', 'activity_id': 'warm-up.feelings',
        'objective_id': None, 'completed_stage_ids': (), 'activity_progress': (
            ActivityProgress(activity_id='warm-up.hello', status='completed'),
            ActivityProgress(activity_id='warm-up.feelings', status='in_progress',
                             response_opportunity_given=True))})
    decision = engine.decide(state, evidence(items=[]), unit_01)
    assert decision.next_stage_id == 'lesson-01'
    assert decision.next_activity_id == 'lesson-01.introduce-city'
    assert not decision.count_attempt
    assert decision.mastery_updates == []
