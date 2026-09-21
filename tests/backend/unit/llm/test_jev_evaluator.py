import httpx
import pytest

from luna_tutor.config import Settings
from luna_tutor.llm.jev_evaluator import JevEvaluator
from luna_tutor.llm.openrouter import InvalidModelOutputError, OpenRouterClient


ENDPOINT = 'https://openrouter.ai/api/alpha/decisions'


def decision_response(*, response_kind='answer', meaning='satisfied',
                      form='correct_target_form', recast=0.02,
                      emotion=0.01, clarification=0.01):
    return httpx.Response(200, json={
        'model': 'typesafe/jev-1.13-20260917',
        'answers': {
            'response_kind': {'type': 'choice', 'choice': response_kind},
            'emotional_signal': {'type': 'noul', 'noul': emotion},
            'needs_clarification': {'type': 'noul', 'noul': clarification},
            'objective_0_meaning': {'type': 'choice', 'choice': meaning},
            'objective_0_form': {'type': 'choice', 'choice': form},
            'objective_0_recast': {'type': 'noul', 'noul': recast},
        },
        'usage': {'prompt_tokens': 10, 'completion_tokens': 6},
    })


@pytest.mark.asyncio
async def test_jev_uses_decisions_api_and_returns_correlated_evidence(
        respx_mock, evaluator_request):
    route = respx_mock.post(ENDPOINT).mock(return_value=decision_response())
    async with OpenRouterClient(Settings('test-key')) as client:
        result = await JevEvaluator(client).evaluate(evaluator_request)

    payload = route.calls[0].request.read()
    import json
    body = json.loads(payload)
    assert body['model'] == '~typesafe/jev-latest'
    assert body['state']['learner_transcript'] == 'I live in the city.'
    assert body['state']['active_objectives'][0]['objective_id'] == 'pattern.live-in'
    assert body['questions']['objective_0_meaning']['type'] == 'choice'
    assert body['questions']['objective_0_recast']['type'] == 'noul'
    assert 'word imitation' in body['questions']['objective_0_form']['instructions'].lower()
    assert 'description_en' not in body
    assert result.turn_id == 'turn-1'
    assert result.state_version == 4
    assert result.objective_evidence[0].evidence_quote == 'I live in the city.'
    assert result.objective_evidence[0].corrected_form is None


@pytest.mark.asyncio
async def test_jev_recast_is_a_decision_and_never_borrows_gemini_wording(
        respx_mock, evaluator_request):
    evaluator_request = evaluator_request.model_copy(update={
        'learner_transcript': 'I live city.'})
    respx_mock.post(ENDPOINT).mock(return_value=decision_response(
        meaning='satisfied', form='error_in_target_form', recast=0.98))

    async with OpenRouterClient(Settings('test-key')) as client:
        result = await JevEvaluator(client).evaluate(evaluator_request)

    item = result.objective_evidence[0]
    assert item.recast_needed is True
    assert item.corrected_form is None
    assert item.evidence_quote == 'I live city.'


@pytest.mark.asyncio
@pytest.mark.parametrize('body', [
    {'model': 'typesafe/jev', 'answers': {}},
    {'model': 'typesafe/jev', 'answers': {
        'response_kind': {'type': 'choice', 'choice': 'invented'},
    }},
])
async def test_jev_rejects_missing_or_unknown_answers(
        body, respx_mock, evaluator_request):
    respx_mock.post(ENDPOINT).mock(return_value=httpx.Response(200, json=body))

    async with OpenRouterClient(Settings('test-key')) as client:
        with pytest.raises(InvalidModelOutputError):
            await JevEvaluator(client).evaluate(evaluator_request)


@pytest.mark.asyncio
async def test_jev_uncertainty_uses_local_reason_not_generated_prose(
        respx_mock, evaluator_request):
    respx_mock.post(ENDPOINT).mock(return_value=decision_response(
        response_kind='insufficient_data', meaning='uncertain', form='uncertain',
        clarification=0.95))

    async with OpenRouterClient(Settings('test-key')) as client:
        result = await JevEvaluator(client).evaluate(evaluator_request)

    assert result.needs_clarification is True
    assert result.ambiguity_reason == 'Jev marked the learner input as unclear.'
    assert result.objective_evidence[0].evidence_quote is None
