import json
import traceback

import pytest

from luna_tutor.config import Settings
from luna_tutor.domain.evidence import ContextTurn, EvaluatorResult
from luna_tutor.llm.evaluator import GeminiEvaluator, InvalidEvaluatorResultError
from luna_tutor.llm.openrouter import OpenRouterClient, ProviderError
from luna_tutor.prompts.loader import load_grade_system_prompt

ENDPOINT = 'https://openrouter.ai/api/v1/chat/completions'
pytestmark = pytest.mark.asyncio


async def test_evaluator_prompt_rejects_answers_that_do_not_answer_the_current_question():
    prompt = ' '.join(load_grade_system_prompt(5, 'evaluator').split())

    assert 'must answer the teacher_turn' in prompt
    assert 'must demonstrate an active objective' in prompt
    assert '“It’s the last group.”' in prompt
    assert 'wrong_semantic_category' in prompt


async def test_evaluator_returns_domain_result_and_sends_only_sanitized_request(
        respx_mock, completion_response, evaluator_request, evaluator_result):
    route = respx_mock.post(ENDPOINT).mock(return_value=completion_response(evaluator_result))
    # Defensive boundary: even an unvalidated copy cannot leak to the provider.
    request = evaluator_request.model_copy(update={
        'learner_transcript': 'Call 0912 345 678. I live in the city.',
        'recent_context': [ContextTurn(role='learner', text='Hello').model_copy(
            update={'text': 'Call 0987654321'})],
    })
    async with OpenRouterClient(Settings('test-key')) as client:
        result = await GeminiEvaluator(client).evaluate(request)
    assert isinstance(result, EvaluatorResult)
    assert result.objective_evidence[0].meaning_status == 'satisfied'
    body = json.loads(route.calls.last.request.content)
    assert all(number not in json.dumps(body) for number in ['0912', '0987654321'])
    payload = json.loads(body['messages'][-1]['content'])
    assert payload['learner_transcript'] == 'Call [REDACTED_PHONE]. I live in the city.'
    assert payload['recent_context'][0]['text'] == 'Call [REDACTED_PHONE]'
    assert payload['support_given']['model_spoken_recently'] is False
    assert 'expected_label' not in payload
    schema = body['response_format']['json_schema']['schema']
    assert schema['additionalProperties'] is False
    assert set(schema['required']) == {
        'turn_id', 'state_version', 'response_kind', 'emotional_signals',
        'objective_evidence', 'needs_clarification', 'ambiguity_reason',
    }
    assert schema['$defs']['ObjectiveEvidence']['additionalProperties'] is False


@pytest.mark.parametrize('changes', [
    {'turn_id': 'stale-turn'}, {'state_version': 3}, {'state_version': '4'},
    {'response_kind': 'advance_lesson'}, {'progression_action': 'next'},
    {'teacher_text': 'Well done!'}, {'needs_clarification': True},
    {'ambiguity_reason': 'Unclear despite no clarification flag'},
    {'response_kind': 'insufficient_data'},
    {'emotional_signals': ['0912345678']},
])
async def test_invalid_or_uncorrelated_output_is_rejected_once(
        changes, respx_mock, completion_response, evaluator_request, evaluator_result):
    route = respx_mock.post(ENDPOINT).mock(return_value=completion_response(evaluator_result | changes))
    async with OpenRouterClient(Settings('test-key')) as client:
        with pytest.raises(InvalidEvaluatorResultError) as caught:
            await GeminiEvaluator(client).evaluate(evaluator_request)
    assert route.call_count == 1
    assert caught.value.request_id == 'turn-1'
    assert caught.value.status_code == 200
    assert caught.value.__context__ is None
    assert '0912345678' not in ''.join(traceback.format_exception(caught.value))


@pytest.mark.parametrize('changes', [
    {'objective_id': 'unknown'}, {'evidence_quote': 'I live in the countryside.'},
    {'evidence_quote': 'Where do you live?'}, {'evidence_quote': 'i live in the city.'},
    {'evidence_quote': None}, {'recast_needed': True},
    {'corrected_form': 'I live in the city.'},
    {'meaning_status': 'mastered'}, {'target_form_status': 'valid_alternative',
                                    'recast_needed': True, 'corrected_form': 'I live in the city.'},
])
async def test_bad_evidence_is_rejected_after_bounded_recast_repair(
        changes, respx_mock, completion_response, evaluator_request, evaluator_result):
    evaluator_result['objective_evidence'][0].update(changes)
    route = respx_mock.post(ENDPOINT).mock(return_value=completion_response(evaluator_result))
    async with OpenRouterClient(Settings('test-key')) as client:
        with pytest.raises(InvalidEvaluatorResultError):
            await GeminiEvaluator(client).evaluate(evaluator_request)
    assert route.call_count == (2 if {'recast_needed', 'corrected_form'} & changes.keys() else 1)


@pytest.mark.parametrize('changes', [
    {'transcript_status': 'incomplete'}, {'transcript_status': 'uncertain'},
    {'stt_issue': True}, {'audio_issue': True}, {'learner_transcript': ''},
])
async def test_operational_uncertainty_cannot_be_accepted_as_clear_learner_evidence(
        changes, respx_mock, completion_response, evaluator_request, evaluator_result):
    respx_mock.post(ENDPOINT).mock(return_value=completion_response(evaluator_result))
    async with OpenRouterClient(Settings('test-key')) as client:
        with pytest.raises(InvalidEvaluatorResultError):
            await GeminiEvaluator(client).evaluate(evaluator_request.model_copy(update=changes))


async def test_uncertain_transcript_can_return_clarification_without_learner_failure(
        respx_mock, completion_response, evaluator_request, evaluator_result):
    evaluator_result.update(response_kind='insufficient_data', needs_clarification=True,
                            ambiguity_reason='The transcript is incomplete')
    evaluator_result['objective_evidence'][0].update(
        meaning_status='uncertain', target_form_status='uncertain', evidence_quote=None)
    respx_mock.post(ENDPOINT).mock(return_value=completion_response(evaluator_result))
    async with OpenRouterClient(Settings('test-key')) as client:
        result = await GeminiEvaluator(client).evaluate(evaluator_request.model_copy(update={
            'transcript_status': 'uncertain', 'learner_transcript': '', 'stt_issue': True}))
    assert result.needs_clarification
    assert result.objective_evidence[0].meaning_status == 'uncertain'


async def test_provider_failure_propagates_without_fabricated_evaluation(
        respx_mock, evaluator_request):
    route = respx_mock.post(ENDPOINT).respond(401, text='secret provider body')
    async with OpenRouterClient(Settings('test-key')) as client:
        with pytest.raises(ProviderError):
            await GeminiEvaluator(client).evaluate(evaluator_request)
    assert route.call_count == 1


async def test_multiple_objectives_and_emotion_are_preserved(
        respx_mock, completion_response, evaluator_request, evaluator_result):
    objective = evaluator_request.active_objectives[0].model_copy(update={'objective_id': 'vocab.city'})
    request = evaluator_request.model_copy(update={
        'learner_transcript': "I'm tired. I live in the city.",
        'active_objectives': [*evaluator_request.active_objectives, objective],
    })
    evaluator_result['emotional_signals'] = ['tired']
    evaluator_result['objective_evidence'].append(evaluator_result['objective_evidence'][0] | {
        'objective_id': 'vocab.city', 'evidence_quote': 'city'})
    respx_mock.post(ENDPOINT).mock(return_value=completion_response(evaluator_result))
    async with OpenRouterClient(Settings('test-key')) as client:
        result = await GeminiEvaluator(client).evaluate(request)
    assert result.emotional_signals == ['tired']
    assert [item.objective_id for item in result.objective_evidence] == ['pattern.live-in', 'vocab.city']


async def test_redaction_marker_cannot_be_the_demonstrated_evidence(
        respx_mock, completion_response, evaluator_request, evaluator_result):
    evaluator_result['objective_evidence'][0]['evidence_quote'] = '[REDACTED_PHONE]'
    respx_mock.post(ENDPOINT).mock(return_value=completion_response(evaluator_result))
    async with OpenRouterClient(Settings('test-key')) as client:
        with pytest.raises(InvalidEvaluatorResultError):
            await GeminiEvaluator(client).evaluate(evaluator_request.model_copy(update={
                'learner_transcript': 'Call [REDACTED_PHONE]'}))


async def test_duplicate_evidence_is_rejected(
        respx_mock, completion_response, evaluator_request, evaluator_result):
    evaluator_result['objective_evidence'] *= 2
    respx_mock.post(ENDPOINT).mock(return_value=completion_response(evaluator_result))
    async with OpenRouterClient(Settings('test-key')) as client:
        with pytest.raises(InvalidEvaluatorResultError):
            await GeminiEvaluator(client).evaluate(evaluator_request)


@pytest.mark.parametrize('kind', ['asks_meaning', 'uncertain_transcript'])
async def test_meaning_question_and_uncertain_transcript_cannot_be_recast(
        kind, respx_mock, completion_response, evaluator_request, evaluator_result):
    request = evaluator_request.model_copy(update={'learner_transcript': 'I live city'})
    evaluator_result['objective_evidence'][0].update(
        evidence_quote='I live city', target_form_status='error_in_target_form',
        recast_needed=True, corrected_form='I live in the city.')
    if kind == 'asks_meaning':
        evaluator_result['response_kind'] = 'asks_meaning'
    else:
        request = request.model_copy(update={'transcript_status': 'uncertain'})
        evaluator_result.update(needs_clarification=True, ambiguity_reason='Unreliable transcription')
    respx_mock.post(ENDPOINT).mock(return_value=completion_response(evaluator_result))
    async with OpenRouterClient(Settings('test-key')) as client:
        with pytest.raises(InvalidEvaluatorResultError):
            await GeminiEvaluator(client).evaluate(request)


async def test_invalid_request_copy_is_rejected_before_network(respx_mock, evaluator_request):
    request = evaluator_request.model_copy(update={'state_version': '4'})
    async with OpenRouterClient(Settings('test-key')) as client:
        with pytest.raises(ValueError, match='Invalid evaluator request'):
            await GeminiEvaluator(client).evaluate(request)
    assert respx_mock.calls.call_count == 0


async def test_numeric_correlation_ids_round_trip_without_collapsing(
        respx_mock, completion_response, evaluator_request, evaluator_result):
    provider_turn_ids = []

    def respond(http_request):
        payload = json.loads(json.loads(http_request.content)['messages'][-1]['content'])
        provider_turn_ids.append(payload['turn_id'])
        return completion_response(evaluator_result | {
            'turn_id': payload['turn_id'], 'state_version': payload['state_version'],
            'objective_evidence': [evaluator_result['objective_evidence'][0] | {
                'objective_id': objective['objective_id'],
            } for objective in payload['active_objectives']],
        })

    respx_mock.post(ENDPOINT).mock(side_effect=respond)
    objective_ids = ['pattern.12345678', 'pattern.87654321']
    objectives = [evaluator_request.active_objectives[0].model_copy(update={'objective_id': value})
                  for value in objective_ids]
    async with OpenRouterClient(Settings('test-key')) as client:
        evaluator = GeminiEvaluator(client)
        for turn_id in ['turn-12345678', 'turn-87654321']:
            result = await evaluator.evaluate(evaluator_request.model_copy(update={
                'turn_id': turn_id, 'state_version': 12345678, 'active_objectives': objectives,
            }))
            assert result.turn_id == turn_id
            assert result.state_version == 12345678
            assert [item.objective_id for item in result.objective_evidence] == objective_ids
    assert provider_turn_ids[0] != provider_turn_ids[1]


@pytest.mark.parametrize('turn_id', ['turn-12345678', 'turn-87654321'])
async def test_changed_turn_id_cannot_be_accepted_after_redaction(
        turn_id, respx_mock, completion_response, evaluator_request, evaluator_result):
    respx_mock.post(ENDPOINT).mock(return_value=completion_response(
        evaluator_result | {'turn_id': 'turn-[REDACTED_PHONE]'}))
    async with OpenRouterClient(Settings('test-key')) as client:
        with pytest.raises(InvalidEvaluatorResultError):
            await GeminiEvaluator(client).evaluate(evaluator_request.model_copy(
                update={'turn_id': turn_id}))


async def test_another_turns_provider_id_is_rejected(
        respx_mock, completion_response, evaluator_request, evaluator_result):
    provider_turn_ids = []

    def respond(http_request):
        payload = json.loads(json.loads(http_request.content)['messages'][-1]['content'])
        provider_turn_ids.append(payload['turn_id'])
        return completion_response(evaluator_result | {'turn_id': provider_turn_ids[0]})

    respx_mock.post(ENDPOINT).mock(side_effect=respond)
    async with OpenRouterClient(Settings('test-key')) as client:
        evaluator = GeminiEvaluator(client)
        await evaluator.evaluate(evaluator_request.model_copy(update={'turn_id': 'turn-12345678'}))
        with pytest.raises(InvalidEvaluatorResultError):
            await evaluator.evaluate(evaluator_request.model_copy(update={'turn_id': 'turn-87654321'}))


async def test_provider_alias_cannot_collide_with_a_literal_caller_id(
        respx_mock, completion_response, evaluator_request, evaluator_result):
    provider_turn_ids = []

    def respond(http_request):
        payload = json.loads(json.loads(http_request.content)['messages'][-1]['content'])
        provider_turn_ids.append(payload['turn_id'])
        return completion_response(evaluator_result | {'turn_id': payload['turn_id']})

    respx_mock.post(ENDPOINT).mock(side_effect=respond)
    async with OpenRouterClient(Settings('test-key')) as client:
        evaluator = GeminiEvaluator(client)
        first = await evaluator.evaluate(evaluator_request.model_copy(update={'turn_id': 'turn-12345678'}))
        literal_id = provider_turn_ids[0]
        second = await evaluator.evaluate(evaluator_request.model_copy(update={'turn_id': literal_id}))
    assert first.turn_id == 'turn-12345678'
    assert second.turn_id == literal_id
    assert provider_turn_ids[0] != provider_turn_ids[1]


@pytest.mark.parametrize(('transcript', 'quote'), [
    ('[REDACTED_PHONE]', 'PHONE'),
    ('[REDACTED_PHONE]', 'REDACTED'),
    ('[REDACTED_PHONE]', '[REDACTED'),
    ('[REDACTED_PHONE]', 'PHONE]'),
    ('[REDACTED_PHONE]', '_'),
    ('[REDACTED_PHONE] [REDACTED_PHONE]', 'PHONE'),
    ('My [REDACTED_PHONE] is private.', 'PHONE] is private.'),
    ('My [REDACTED_PHONE] is private.', 'My [REDACTED'),
    ('My [REDACTED_PHONE] is private.', 'My [REDACTED_PHONE] is private.'),
    ('ci[REDACTED_PHONE]ty', 'city'),
])
async def test_evidence_requires_an_occurrence_outside_redaction_spans(
        transcript, quote, respx_mock, completion_response, evaluator_request, evaluator_result):
    evaluator_result['objective_evidence'][0]['evidence_quote'] = quote
    respx_mock.post(ENDPOINT).mock(return_value=completion_response(evaluator_result))
    async with OpenRouterClient(Settings('test-key')) as client:
        with pytest.raises(InvalidEvaluatorResultError):
            await GeminiEvaluator(client).evaluate(evaluator_request.model_copy(
                update={'learner_transcript': transcript}))


@pytest.mark.parametrize('transcript', [
    'PHONE [REDACTED_PHONE]', '[REDACTED_PHONE] PHONE',
    '[REDACTED_PHONE] PHONE [REDACTED_PHONE]',
])
async def test_real_quote_is_allowed_when_same_text_also_occurs_inside_a_marker(
        transcript, respx_mock, completion_response, evaluator_request, evaluator_result):
    evaluator_result['objective_evidence'][0]['evidence_quote'] = 'PHONE'
    respx_mock.post(ENDPOINT).mock(return_value=completion_response(evaluator_result))
    async with OpenRouterClient(Settings('test-key')) as client:
        result = await GeminiEvaluator(client).evaluate(evaluator_request.model_copy(
            update={'learner_transcript': transcript}))
    assert result.objective_evidence[0].evidence_quote == 'PHONE'


@pytest.mark.parametrize('bad_changes', [
    {'target_form_status': 'error_in_target_form', 'recast_needed': True, 'corrected_form': None},
    {'target_form_status': 'correct_target_form', 'recast_needed': True, 'corrected_form': 'I live in the city.'},
])
async def test_inconsistent_recast_gets_one_repair_with_original_request(
        bad_changes, respx_mock, completion_response, evaluator_request, evaluator_result):
    import copy
    bad = copy.deepcopy(evaluator_result)
    bad['objective_evidence'][0].update(bad_changes)
    route = respx_mock.post(ENDPOINT).mock(side_effect=[
        completion_response(bad), completion_response(evaluator_result)])
    async with OpenRouterClient(Settings('test-key')) as client:
        result = await GeminiEvaluator(client).evaluate(evaluator_request)
    assert result == EvaluatorResult.model_validate(evaluator_result)
    assert route.call_count == 2
    first = json.loads(json.loads(route.calls[0].request.content)['messages'][-1]['content'])
    second = json.loads(json.loads(route.calls[1].request.content)['messages'][-1]['content'])
    feedback = second.pop('validation_feedback')
    assert second == first
    assert feedback
    assert 'expected_label' not in second


@pytest.mark.parametrize(('status', 'http_attempts'), [(401, 1), (503, 2)])
async def test_provider_failure_during_repair_does_not_start_another_model_draft(
        status, http_attempts, respx_mock, completion_response, evaluator_request, evaluator_result):
    import httpx
    evaluator_result['objective_evidence'][0].update(recast_needed=True)
    route = respx_mock.post(ENDPOINT).mock(side_effect=[
        completion_response(evaluator_result),
        *[httpx.Response(status, text='unavailable') for _ in range(http_attempts)]])
    async with OpenRouterClient(Settings('test-key')) as client:
        with pytest.raises(ProviderError):
            await GeminiEvaluator(client).evaluate(evaluator_request)
    assert route.call_count == 1 + http_attempts


async def test_repaired_draft_still_rejects_quote_not_in_learner_input(
        respx_mock, completion_response, evaluator_request, evaluator_result):
    import copy
    first = copy.deepcopy(evaluator_result)
    first['objective_evidence'][0]['recast_needed'] = True
    second = copy.deepcopy(evaluator_result)
    second['objective_evidence'][0]['evidence_quote'] = 'An invented learner statement.'
    route = respx_mock.post(ENDPOINT).mock(side_effect=[
        completion_response(first), completion_response(second)])
    async with OpenRouterClient(Settings('test-key')) as client:
        with pytest.raises(InvalidEvaluatorResultError):
            await GeminiEvaluator(client).evaluate(evaluator_request)
    assert route.call_count == 2
