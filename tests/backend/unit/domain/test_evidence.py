import pytest
from pydantic import ValidationError

from luna_tutor.domain.evidence import EvaluatorRequest, EvaluatorResult, ObjectiveEvidence


def evidence(**changes):
    return dict(objective_id='pattern.live-in', meaning_status='satisfied',
                target_form_status='correct_target_form', evidence_quote='I live in the city',
                recast_needed=False, corrected_form=None) | changes


def result(**changes):
    return dict(turn_id='t1', state_version=4, response_kind='answer',
                emotional_signals=['tired'], objective_evidence=[evidence()],
                needs_clarification=False, ambiguity_reason=None) | changes


def request(**changes):
    return dict(turn_id='t1', state_version=4, teacher_turn='Where do you live?',
                activity_type='guided_response', active_objectives=[{
                    'objective_id': 'pattern.live-in',
                    'communicative_goal': 'Say where you live',
                    'target_patterns': ['I live in ...'],
                    'acceptable_alternatives': ['My home is in ...'],
                    'evidence_criteria': 'Describe where the learner lives',
                }], support_given={'model_spoken_recently': False,
                                  'choices_given': False, 'sentence_starter_given': False},
                transcript_status='final', learner_transcript='I live in the city') | changes


def test_evaluator_result_supports_answer_and_emotion():
    parsed = EvaluatorResult.model_validate(result())
    assert parsed.emotional_signals == ['tired']
    assert parsed.objective_evidence[0].meaning_status == 'satisfied'
    assert parsed.response_kind == 'answer'


@pytest.mark.parametrize(('form', 'quote'), [
    ('not_used', 'Con sống ở thành phố'),
    ('valid_alternative', 'My home is in the city'),
    ('not_used', 'Countryside'),
])
def test_successful_meaning_does_not_require_target_form_or_recast(form, quote):
    parsed = ObjectiveEvidence.model_validate(evidence(target_form_status=form, evidence_quote=quote))
    assert parsed.meaning_status == 'satisfied'
    assert parsed.recast_needed is False


@pytest.mark.parametrize('changes', [
    {'corrected_form': 'I live in the city.'},
    {'recast_needed': True, 'corrected_form': '   ', 'target_form_status': 'error_in_target_form'},
    {'recast_needed': True, 'corrected_form': 'I live in the city.', 'target_form_status': 'valid_alternative'},
    {'recast_needed': True, 'corrected_form': 'I live in the city.', 'target_form_status': 'not_used'},
    {'meaning_status': 'wrong_semantic_category', 'target_form_status': 'error_in_target_form',
     'recast_needed': True, 'corrected_form': 'My favourite animal is a dolphin.'},
])
def test_recast_requires_a_demonstrated_error_and_correction_requires_recast(changes):
    with pytest.raises(ValidationError):
        ObjectiveEvidence.model_validate(evidence(**changes))


def test_clear_grammar_error_can_supply_a_recast():
    parsed = ObjectiveEvidence.model_validate(evidence(
        target_form_status='error_in_target_form', evidence_quote='I live city',
        recast_needed=True, corrected_form='I live in the city.'))
    assert parsed.corrected_form == 'I live in the city.'


def test_decision_only_evaluator_can_request_recast_without_generating_wording():
    parsed = ObjectiveEvidence.model_validate(evidence(
        target_form_status='error_in_target_form', evidence_quote='I live city',
        recast_needed=True, corrected_form=None))

    assert parsed.recast_needed is True
    assert parsed.corrected_form is None


@pytest.mark.parametrize('quote', ['', '  ', None])
def test_demonstrated_evidence_requires_quote(quote):
    with pytest.raises(ValidationError):
        ObjectiveEvidence.model_validate(evidence(evidence_quote=quote))


@pytest.mark.parametrize('meaning', ['not_demonstrated', 'uncertain'])
def test_absent_evidence_can_have_no_quote(meaning):
    parsed = ObjectiveEvidence.model_validate(evidence(
        meaning_status=meaning, target_form_status='uncertain', evidence_quote=None))
    assert parsed.evidence_quote is None


def test_target_form_claim_still_requires_quote_when_meaning_is_uncertain():
    with pytest.raises(ValidationError):
        ObjectiveEvidence.model_validate(evidence(meaning_status='uncertain', evidence_quote=''))


@pytest.mark.parametrize('changes', [
    {'needs_clarification': True}, {'needs_clarification': True, 'ambiguity_reason': ' '},
    {'state_version': '4'}, {'state_version': True}, {'state_version': -1},
    {'response_kind': 'advance_lesson'}, {'progression_action': 'next'},
    {'objective_evidence': [evidence(meaning_status='correct')]},
    {'objective_evidence': [evidence(target_form_status='mastered')]},
    {'objective_evidence': [evidence(recast_needed='false')]},
    {'objective_evidence': [evidence(), evidence()]},
])
def test_result_rejects_invalid_or_controller_owned_data(changes):
    with pytest.raises(ValidationError):
        EvaluatorResult.model_validate(result(**changes))


def test_uncertainty_and_multiple_objectives_roundtrip_as_json():
    parsed = EvaluatorResult.model_validate(result(
        needs_clarification=True, ambiguity_reason='The final clause is incomplete',
        objective_evidence=[evidence(), evidence(objective_id='vocab.city')]))
    assert EvaluatorResult.model_validate_json(parsed.model_dump_json()) == parsed


def test_request_preserves_actual_support_and_uncertain_transcript():
    parsed = EvaluatorRequest.model_validate(request(
        transcript_status='uncertain', learner_transcript='', attempt_count=1,
        stt_issue=True, support_given={'model_spoken_recently': True,
                                    'choices_given': False, 'sentence_starter_given': False}))
    assert parsed.support_given.model_spoken_recently is True
    assert parsed.learner_transcript == ''  # Empty is not a silence judgement.
    assert parsed.stt_issue is True


@pytest.mark.parametrize('changes', [
    {'expected_label': 'correct'}, {'attempt_count': 3},
    {'recent_context': [{'role': 'learner', 'text': 'Hello'}] * 7},
    {'learner_transcript': 'Call 0912 345 678'},
])
def test_evaluator_request_is_bounded_sanitized_and_has_no_gold_labels(changes):
    with pytest.raises(ValidationError):
        EvaluatorRequest.model_validate(request(**changes))
