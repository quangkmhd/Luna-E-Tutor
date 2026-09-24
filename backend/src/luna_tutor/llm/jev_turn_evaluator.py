"""One Jev decision for one Grade 3 practice turn."""

from copy import deepcopy
from enum import StrEnum
from pathlib import Path

import yaml

from luna_tutor.llm.openrouter import InvalidModelOutputError, OpenRouterClient


class TurnEvaluation(StrEnum):
    PASSED = 'PASSED'
    ATTEMPT_FAILED = 'ATTEMPT_FAILED'
    OTHER_INTENT = 'OTHER_INTENT'
    PASSED_WITH_REPLY = 'PASSED_WITH_REPLY'
    UNCLEAR_INPUT = 'UNCLEAR_INPUT'


RUBRIC_PATH = Path(__file__).resolve().parents[1] / 'prompts/grade3_jev_rubric.yaml'


class JevTurnEvaluator:
    def __init__(self, client: OpenRouterClient):
        self._client = client
        data = yaml.safe_load(RUBRIC_PATH.read_text(encoding='utf-8'))
        self._question = data['turn_evaluation']
        if (self._question.get('type') != 'choice'
                or set(self._question.get('criteria', {})) != {code.value for code in TurnEvaluation}):
            raise ValueError(f'Invalid Jev turn rubric: {RUBRIC_PATH}')

    async def evaluate_turn(
        self,
        learner_goal: str,
        learner_query: str,
        history: list[dict[str, str]],
        turn_id: str,
    ) -> TurnEvaluation:
        if any(message.get('role') not in {'assistant', 'user'}
               or not isinstance(message.get('content'), str) for message in history):
            raise ValueError('Jev history requires user/assistant text messages')
        envelope = await self._client.decisions(
            state={
                'learner_goal': learner_goal,
                'learner_query': learner_query,
                'history': history,
            },
            questions={'turn_evaluation': deepcopy(self._question)},
            request_id=turn_id,
        )
        answer = envelope.get('answers', {}).get('turn_evaluation')
        try:
            if not isinstance(answer, dict) or answer.get('type') != 'choice':
                raise ValueError('missing choice')
            return TurnEvaluation(answer['choice'])
        except (KeyError, TypeError, ValueError):
            raise InvalidModelOutputError(
                status_code=200, request_id=turn_id,
                reason='Invalid Jev turn evaluation',
            ) from None
