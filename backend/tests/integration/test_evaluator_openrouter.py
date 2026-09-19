"""Opt-in smoke test: RUN_LIVE_LLM=1 uv run pytest tests/integration -v.

The opt-in is checked before loading .env. Keys and provider bodies are never
printed; this smoke test uses only synthetic, non-sensitive learner content.
"""

import os

import pytest
from dotenv import load_dotenv

from luna_tutor.config import Settings
from luna_tutor.domain.evidence import EvaluatorRequest
from luna_tutor.llm.evaluator import GeminiEvaluator
from luna_tutor.llm.openrouter import OpenRouterClient, OpenRouterError


@pytest.mark.asyncio
@pytest.mark.skipif(os.getenv('RUN_LIVE_LLM') != '1',
                    reason='Live OpenRouter calls disabled; set RUN_LIVE_LLM=1 to opt in')
async def test_live_evaluator_returns_correlated_one_word_evidence():
    load_dotenv(override=False)
    if not os.getenv('OPENROUTER_API_KEY', '').strip():
        pytest.skip('OPENROUTER_API_KEY is missing from environment and .env')
    request = EvaluatorRequest.model_validate({
        'turn_id': 'live-smoke-1', 'state_version': 0,
        'teacher_turn': 'Where do you live?', 'activity_type': 'guided_response',
        'active_objectives': [{
            'objective_id': 'pattern.live-in',
            'communicative_goal': 'Say where the learner lives',
            'target_patterns': ['I live in ...'],
            'acceptable_alternatives': ['My home is in ...'],
            'evidence_criteria': 'A place of residence, including a natural short answer',
        }], 'support_given': {}, 'transcript_status': 'final',
        'learner_transcript': 'Countryside.',
    })
    async with OpenRouterClient(Settings.from_env()) as client:
        try:
            result = await GeminiEvaluator(client).evaluate(request)
        except OpenRouterError as error:
            pytest.fail(str(error), pytrace=False)
    assert result.turn_id == 'live-smoke-1'
    assert result.state_version == 0
    assert result.response_kind == 'answer'
    assert not result.needs_clarification
    assert len(result.objective_evidence) == 1
    evidence = result.objective_evidence[0]
    assert evidence.objective_id == 'pattern.live-in'
    assert evidence.meaning_status == 'satisfied'
    assert evidence.target_form_status == 'not_used'
    assert evidence.evidence_quote and evidence.evidence_quote in 'Countryside.'
    assert not evidence.recast_needed
    assert evidence.corrected_form is None
