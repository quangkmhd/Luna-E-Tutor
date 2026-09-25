from unittest.mock import AsyncMock

import pytest

from luna_tutor.llm.jev_turn_evaluator import JevTurnEvaluator, TurnEvaluation
from luna_tutor.llm.openrouter import InvalidModelOutputError


@pytest.mark.asyncio
async def test_jev_receives_only_goal_query_and_prior_history():
    client = AsyncMock()
    client.decisions.return_value = {'answers': {
        'turn_evaluation': {'type': 'choice', 'choice': 'PASSED_WITH_REPLY'}}}
    evaluator = JevTurnEvaluator(client)
    result = await evaluator.evaluate_turn(
        learner_goal='Ask Luna how she is.',
        learner_query='How are you?',
        history=[{'role': 'assistant', 'content': 'Ask me how I am.'}],
        turn_id='turn-1',
    )
    assert result is TurnEvaluation.PASSED_WITH_REPLY
    call = client.decisions.await_args.kwargs
    assert call['state'] == {
        'learner_goal': 'Ask Luna how she is.',
        'learner_query': 'How are you?',
        'history': [{'role': 'assistant', 'content': 'Ask me how I am.'}],
    }
    assert list(call['questions']) == ['turn_evaluation']
    assert set(call['questions']['turn_evaluation']['criteria']) == {
        code.value for code in TurnEvaluation}
    assert call['request_id'] == 'turn-1'


@pytest.mark.asyncio
@pytest.mark.parametrize(('answer', 'reason'), [
    ({}, 'Missing Jev turn_evaluation choice'),
    ({'turn_evaluation': {'type': 'choice', 'choice': 'NEW_CODE'}},
     'Unknown Jev turn_evaluation choice'),
    ({'turn_evaluation': {'type': 'text', 'choice': 'PASSED'}},
     'Invalid Jev turn_evaluation type'),
    ({'turn_evaluation': {'type': 'choice', 'choice': ['PASSED']}},
     'Invalid Jev turn_evaluation choice type'),
])
async def test_invalid_jev_output_does_not_become_a_teaching_decision(answer, reason):
    client = AsyncMock()
    client.decisions.return_value = {'answers': answer}
    with pytest.raises(InvalidModelOutputError) as caught:
        await JevTurnEvaluator(client).evaluate_turn(
            learner_goal='Say hello.', learner_query='Hi', history=[], turn_id='turn-2')
    assert caught.value.reason == reason
