import pytest

from luna_tutor.domain.evidence import SupportGiven
from luna_tutor.domain.state import ObjectiveProgress

HOME = 'unit01.lesson01.pattern.live_in'


@pytest.mark.parametrize(('arguments', 'feedback', 'progression', 'count', 'uses', 'review'), [
    ({}, 'acknowledge_and_continue', 'move_to_next_objective', True, 1, []),
    ({'form': 'valid_alternative', 'quote': 'My home is in the city.'},
     'acknowledge_and_continue', 'move_to_next_objective', True, 1, []),
    ({'form': 'not_used', 'quote': 'Countryside.'},
     'acknowledge_and_continue', 'move_to_next_objective', True, 0, []),
    ({'form': 'error_in_target_form', 'quote': 'I live countryside.', 'recast': True,
      'correction': 'I live in the countryside.'},
     'recast', 'move_to_next_objective', True, 0, [HOME]),
    ({'meaning': 'wrong_semantic_category', 'form': 'not_used', 'quote': 'Pink.'},
     'offer_support', 'stay', True, 0, []),
    ({'kind': 'asks_meaning', 'items': []}, 'explain_meaning', 'stay', False, 0, []),
    ({'kind': 'asks_teacher', 'items': []}, 'answer_teacher_question', 'stay', False, 0, []),
    ({'kind': 'off_topic', 'items': []}, 'redirect', 'stay', False, 0, []),
    ({'form': 'not_used', 'quote': 'Con sống ở nông thôn.'},
     'acknowledge_and_continue', 'move_to_next_objective', True, 0, []),
    ({'emotion': ['tired']}, 'reassure', 'move_to_next_objective', True, 1, []),
    ({'meaning': 'uncertain', 'form': 'uncertain', 'quote': None,
      'clarify': True, 'reason': 'Transcript is incomplete.'},
     'clarify', 'stay', False, 0, []),
    ({'kind': 'insufficient_data', 'items': []}, 'clarify', 'stay', False, 0, []),
    ({'kind': 'does_not_know', 'items': []}, 'offer_support', 'stay', True, 0, []),
], ids=['correct-target', 'valid-alternative', 'one-word', 'grammar-recast',
        'wrong-category', 'asks-meaning', 'asks-luna', 'off-topic', 'vietnamese',
        'emotion-and-success', 'uncertain-transcript', 'provider-failure', 'does-not-know'])
def test_feedback_policy_table(engine, state, evidence, unit_01,
                               arguments, feedback, progression, count, uses, review):
    decision = engine.decide(state, evidence(**arguments), unit_01)
    assert decision.feedback_action == feedback
    assert decision.progression_action == progression
    assert decision.count_attempt is count
    assert sum(update.independent_uses for update in decision.mastery_updates) == uses
    assert decision.review_queue_add == review
    assert decision.corrected_form == arguments.get('correction')
    assert decision.emotional_support is bool(arguments.get('emotion'))


@pytest.mark.parametrize(('changes', 'feedback', 'progression'), [
    ({'privacy_event': True}, 'privacy_redirect', 'stay'),
    ({'stop_requested': True}, 'stop', 'save_and_stop'),
    ({'stop_requested': True, 'privacy_event': True}, 'stop', 'save_and_stop'),
])
def test_safety_short_circuits_success_questions_and_attempt_limit(
        engine, state, evidence, unit_01, changes, feedback, progression):
    state = state.model_copy(update={**changes, 'attempt_count': 2})
    decision = engine.decide(state, evidence(kind='asks_meaning', emotion=['sad']), unit_01)
    assert decision.feedback_action == feedback
    assert decision.progression_action == progression
    assert not decision.count_attempt
    assert decision.mastery_updates == []
    assert decision.review_queue_add == []
    assert decision.next_objective_id is None
    assert decision.corrected_form is None


@pytest.mark.parametrize('reason', ['provider timeout', 'STT failed', 'audio unavailable', 'partial transcript'])
def test_operational_issues_precede_emotion_and_leave_attempts_and_evidence_unchanged(
        engine, state, evidence, unit_01, reason):
    decision = engine.decide(state.model_copy(update={'attempt_count': 2}),
                             evidence(clarify=True, reason=reason, emotion=['sad']), unit_01)
    assert decision.feedback_action == 'clarify'
    assert decision.progression_action == 'stay'
    assert not decision.count_attempt
    assert decision.mastery_updates == []
    assert decision.review_queue_add == []


@pytest.mark.parametrize('support', [
    SupportGiven(model_spoken_recently=True), SupportGiven(choices_given=True),
    SupportGiven(sentence_starter_given=True),
])
def test_recent_support_cannot_be_recorded_as_independent_use(engine, state, evidence, unit_01, support):
    decision = engine.decide(state.model_copy(update={'support_given': support}), evidence(), unit_01)
    assert decision.mastery_updates[0].supported_uses == 1
    assert decision.mastery_updates[0].independent_uses == 0


def test_positive_evidence_accumulates_without_overwriting_history(engine, state, evidence, unit_01):
    old = ObjectiveProgress(objective_id=HOME, introduced=True, attempted=True,
                            supported_uses=2, independent_uses=3)
    state = state.model_copy(update={'objective_progress': (old,)})
    decision = engine.decide(state, evidence(), unit_01)
    assert decision.mastery_updates == [ObjectiveProgress(
        objective_id=HOME, introduced=True, attempted=True, supported_uses=2, independent_uses=4)]
    assert state.objective_progress == (old,)


def test_emotional_aside_reduces_pressure_without_counting_failure(engine, state, evidence, unit_01):
    decision = engine.decide(state, evidence(items=[], emotion=['sad']), unit_01)
    assert decision.feedback_action == 'reassure'
    assert decision.progression_action == 'reduce_difficulty'
    assert decision.emotional_support
    assert not decision.count_attempt
    assert decision.mastery_updates == []


def test_wrong_category_never_creates_recast_or_positive_evidence(engine, state, evidence, unit_01):
    decision = engine.decide(state, evidence(meaning='wrong_semantic_category',
        form='correct_target_form', quote='My favourite animal is pink.'), unit_01)
    assert decision.feedback_action == 'offer_support'
    assert decision.mastery_updates == []
    assert decision.corrected_form is None


def test_multiple_form_errors_generate_only_one_recast_and_preserve_both_evidence_items(
        engine, state, evidence, unit_01):
    one = evidence(form='error_in_target_form', recast=True, correction='I live in the city.').objective_evidence[0]
    two = one.model_copy(update={'objective_id': 'unit01.lesson01.pattern.class',
                                 'corrected_form': "I'm in class 5A."})
    decision = engine.decide(state, evidence(items=[one, two]), unit_01)
    assert decision.feedback_action == 'recast'
    assert decision.corrected_form == 'I live in the city.'
    assert decision.review_queue_add == [HOME, 'unit01.lesson01.pattern.class']
    assert len(decision.mastery_updates) == 2


def test_question_still_preserves_independent_evidence_without_consuming_attempt(
        engine, state, evidence, unit_01):
    decision = engine.decide(state, evidence(kind='asks_meaning'), unit_01)
    assert decision.feedback_action == 'explain_meaning'
    assert not decision.count_attempt
    assert decision.mastery_updates[0].independent_uses == 1


def test_decision_is_repeatable_and_does_not_mutate_inputs(engine, state, evidence, unit_01):
    result = evidence()
    before = (state.model_dump(), result.model_dump(), unit_01.model_dump())
    first = engine.decide(state, result, unit_01)
    assert first == engine.decide(state, result, unit_01)
    assert before == (state.model_dump(), result.model_dump(), unit_01.model_dump())


@pytest.mark.parametrize('change', [
    {'state_version': 1}, {'objective_evidence': [] , 'turn_id': 'already-applied'},
])
def test_stale_or_replayed_evidence_is_rejected(engine, state, evidence, unit_01, change):
    state = state.model_copy(update={'applied_turn_ids': ('already-applied',)})
    with pytest.raises(ValueError):
        engine.decide(state, evidence().model_copy(update=change), unit_01)
