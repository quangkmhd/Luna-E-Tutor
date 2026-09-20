import pytest
from pydantic import ValidationError

from luna_tutor.domain.decisions import CompletedTurn, PlannedTurn, TeacherTurnRequest, TeachingDecision
from luna_tutor.domain.state import LessonState


def state(**changes):
    return dict(session_id='session-1', unit_id='grade-05.unit-01', state_version=4,
                stage_id='lesson-01', activity_id='lesson-01.live-in', objective_id='pattern.live-in') | changes


def teacher_request(**changes):
    return dict(turn_id='t1', feedback_action='acknowledge_and_continue', corrected_form=None,
                learner_meaning='Lives in the city', next_teaching_move='Ask about class',
                constraints={'max_questions': 1, 'require_repetition': False,
                             'allow_pronunciation_claims': False}) | changes


def plan(**changes):
    return dict(turn_id='t1', state_version=4, learner_text='I live in the city', privacy_event=False,
                evidence={'turn_id': 't1', 'state_version': 4, 'response_kind': 'answer',
                          'emotional_signals': ['tired'], 'objective_evidence': [{
                              'objective_id': 'pattern.live-in', 'meaning_status': 'satisfied',
                              'target_form_status': 'correct_target_form',
                              'evidence_quote': 'I live in the city', 'recast_needed': False,
                              'corrected_form': None}],
                          'needs_clarification': False, 'ambiguity_reason': None},
                decision={'feedback_action': 'acknowledge_and_continue', 'progression_action': 'stay'},
                teacher_request=teacher_request(),
                proposed_next_state=state(state_version=5, applied_turn_ids=['t1'])) | changes


def test_state_keeps_activity_completion_separate_from_learning_evidence():
    parsed = LessonState.model_validate(state(
        activity_progress=[{'activity_id': 'lesson-01.live-in', 'status': 'support_limit_reached',
                            'completion_reason': 'Two attempts with support', 'attempt_count': 2}],
        objective_progress=[{'objective_id': 'pattern.live-in', 'introduced': True,
                             'attempted': True, 'independent_uses': 0, 'supported_uses': 1,
                             'needs_review': True}],
        review_queue=[{'objective_id': 'pattern.live-in', 'difficulty': 'target_form',
                       'evidence_quote': 'I live city', 'support_level': 'model',
                       'last_seen_turn_id': 't0'}]))
    assert parsed.objective_progress[0].independent_uses == 0
    assert parsed.review_queue[0].objective_id == 'pattern.live-in'
    assert LessonState.model_validate_json(parsed.model_dump_json()) == parsed


@pytest.mark.parametrize('changes', [
    {'state_version': -1}, {'attempt_count': 3}, {'attempt_count': True},
    {'activity_progress': [{'activity_id': 'a1', 'status': 'support_limit_reached'}]},
    {'applied_turn_ids': ['t1', 't1']}, {'mastered': True},
])
def test_state_rejects_invalid_progress(changes):
    with pytest.raises(ValidationError):
        LessonState.model_validate(state(**changes))


def test_state_snapshot_is_frozen_and_does_not_share_input_collections():
    turns = ['t0']
    parsed = LessonState.model_validate(state(applied_turn_ids=turns))
    turns.append('t1')
    assert parsed.applied_turn_ids == ('t0',)
    with pytest.raises(ValidationError):
        parsed.state_version = 5


def test_feedback_and_progression_can_coexist():
    parsed = TeachingDecision(feedback_action='recast', progression_action='move_to_next_objective',
                              corrected_form='I live in the city.', emotional_support=True,
                              next_objective_id='pattern.class', review_queue_add=['pattern.live-in'])
    assert parsed.progression_action == 'move_to_next_objective'
    assert parsed.emotional_support is True


def test_recast_request_can_delegate_missing_wording_to_teacher():
    parsed = TeacherTurnRequest.model_validate(teacher_request(
        feedback_action='recast', corrected_form=None))

    assert parsed.feedback_action == 'recast'
    assert parsed.corrected_form is None


@pytest.mark.parametrize('changes', [
    {'corrected_form': 'Unexpected correction'},
    {'progression_action': 'stay'}, {'state': state()},
    {'constraints': {'require_repetition': True}},
    {'constraints': {'max_questions': 2}},
    {'learner_meaning': 'Call 0912345678'},
])
def test_teacher_input_has_only_bounded_expression_authority(changes):
    with pytest.raises(ValidationError):
        TeacherTurnRequest.model_validate(teacher_request(**changes))


def test_planned_turn_contains_no_teacher_wording_and_copies_evidence():
    incoming = plan()
    parsed = PlannedTurn.model_validate(incoming)
    incoming['evidence']['emotional_signals'].append('sad')
    assert parsed.evidence.emotional_signals == ['tired']
    with pytest.raises(ValidationError):
        PlannedTurn.model_validate(plan(teacher_utterance={'spoken_text': 'Good job'}))


@pytest.mark.parametrize('changes', [
    {'turn_id': 'old'}, {'state_version': 3},
    {'learner_text': 'A different answer'}, {'learner_text': 'Call 0912345678'},
    {'proposed_next_state': state(state_version=4, applied_turn_ids=['t1'])},
    {'proposed_next_state': state(state_version=5)},
    {'teacher_request': teacher_request(turn_id='other')},
    {'teacher_request': teacher_request(feedback_action='clarify')},
])
def test_plan_rejects_mismatched_or_unsanitized_turn_components(changes):
    with pytest.raises(ValidationError):
        PlannedTurn.model_validate(plan(**changes))


def test_completed_turn_requires_valid_utterance_and_matching_next_state():
    planned = PlannedTurn.model_validate(plan())
    completed = CompletedTurn(plan=planned, teacher_utterance={
        'spoken_text': 'You live in the city. What class are you in?',
        'delivery_intent': 'warm', 'generation_mode': 'model'}, next_state=planned.proposed_next_state)
    assert completed.next_state.state_version == 5
    assert CompletedTurn.model_validate_json(completed.model_dump_json()) == completed
    with pytest.raises(ValidationError):
        completed.next_state = LessonState.model_validate(state())
    with pytest.raises(ValidationError):
        CompletedTurn(plan=planned, teacher_utterance={'spoken_text': '  ', 'delivery_intent': 'warm'},
                      next_state=planned.proposed_next_state)
    with pytest.raises(ValidationError):
        CompletedTurn(plan=planned, teacher_utterance=completed.teacher_utterance,
                      next_state=LessonState.model_validate(state(state_version=6)))


def test_completion_records_teacher_text_without_changing_planned_progress():
    planned = PlannedTurn.model_validate(plan())
    next_state = planned.proposed_next_state.model_dump() | {'last_teacher_turn': 'What class are you in?'}
    completed = CompletedTurn(plan=planned, teacher_utterance={
        'spoken_text': 'What class are you in?', 'delivery_intent': 'warm'}, next_state=next_state)
    assert completed.next_state.last_teacher_turn == 'What class are you in?'
    assert planned.proposed_next_state.last_teacher_turn == ''
    with pytest.raises(ValidationError):
        CompletedTurn(plan=planned, teacher_utterance=completed.teacher_utterance,
                      next_state=next_state | {'attempt_count': 1})
    with pytest.raises(ValidationError):
        CompletedTurn(plan=planned, teacher_utterance=completed.teacher_utterance,
                      next_state=next_state | {'last_teacher_turn': 'Invented wording'})


def test_completed_turn_snapshots_model_inputs_before_storage():
    planned = PlannedTurn.model_validate(plan())
    completed = CompletedTurn(plan=planned, teacher_utterance={
        'spoken_text': 'Hello', 'delivery_intent': 'warm'}, next_state=planned.proposed_next_state)
    planned.evidence.emotional_signals.append('sad')
    planned.decision.review_queue_add.append('vocab.city')
    assert completed.plan.evidence.emotional_signals == ['tired']
    assert completed.plan.decision.review_queue_add == []
