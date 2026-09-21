import json

import httpx
import pytest

from luna_tutor.domain.evidence import EvaluatorRequest


@pytest.fixture
def evaluator_request():
    return EvaluatorRequest.model_validate({
        'turn_id': 'turn-1', 'unit_id': 'grade05.unit01', 'state_version': 4,
        'teacher_turn': 'Where do you live?', 'activity_type': 'guided_response',
        'active_objectives': [{
            'objective_id': 'pattern.live-in', 'communicative_goal': 'Say where you live',
            'target_patterns': ['I live in ...'],
            'acceptable_alternatives': ['My home is in ...'],
            'evidence_criteria': 'Describe where the learner lives',
        }],
        'support_given': {}, 'transcript_status': 'final',
        'learner_transcript': 'I live in the city.',
    })


@pytest.fixture
def evaluator_result():
    return {
        'turn_id': 'turn-1', 'state_version': 4, 'response_kind': 'answer',
        'emotional_signals': [], 'objective_evidence': [{
            'objective_id': 'pattern.live-in', 'meaning_status': 'satisfied',
            'target_form_status': 'correct_target_form',
            'evidence_quote': 'I live in the city.',
            'recast_needed': False, 'corrected_form': None,
        }], 'needs_clarification': False, 'ambiguity_reason': None,
    }


@pytest.fixture
def completion_response():
    def response(content, *, finish_reason='stop'):
        return httpx.Response(200, json={
            'id': 'gen-test', 'object': 'chat.completion', 'created': 1,
            'model': 'google/gemini-3.5-flash-lite',
            'choices': [{'index': 0, 'finish_reason': finish_reason,
                         'message': {'role': 'assistant', 'content': (
                             content if isinstance(content, str) else json.dumps(content))}}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 10, 'total_tokens': 20},
        })
    return response
