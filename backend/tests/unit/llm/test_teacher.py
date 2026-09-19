import json

import pytest

from luna_tutor.domain.decisions import TeacherConstraints, TeacherTurnRequest
from luna_tutor.llm.teacher import GeminiTeacher


class FakeClient:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    async def structured_chat(self, messages, schema, request_id):
        self.calls.append((messages, schema, request_id))
        if self.error:
            raise self.error
        return self.result


def request(**changes):
    values = dict(
        turn_id='turn-1', feedback_action='recast',
        corrected_form='I live in the countryside.',
        learner_meaning='Quang lives in the countryside.',
        next_teaching_move='Ask what Quang likes about it.',
        emotional_support=False, constraints=TeacherConstraints(),
    )
    values.update(changes)
    return TeacherTurnRequest(**values)


@pytest.mark.asyncio
async def test_teacher_receives_bounded_request_without_progression_authority():
    client = FakeClient({'spoken_text': 'Oh, I live in the countryside. What do you like about it?',
                         'delivery_intent': 'encouraging', 'generation_mode': 'model'})
    utterance = await GeminiTeacher(client).respond(request())
    assert utterance.spoken_text.startswith('Oh, I live')
    payload = json.loads(client.calls[0][0][1]['content'])
    assert payload['feedback_action'] == 'recast'
    assert payload['corrected_form'] == 'I live in the countryside.'
    assert payload['next_teaching_move'] == 'Ask what Quang likes about it.'
    assert payload['constraints']['max_questions'] == 1
    assert 'progression_action' not in payload
    assert 'next_state' not in payload
    assert 'tools' not in payload


@pytest.mark.asyncio
async def test_invalid_teacher_output_uses_plain_deterministic_fallback():
    client = FakeClient({'spoken_text': '**Repeat after me:** I live in the countryside? Again?',
                         'delivery_intent': 'encouraging', 'generation_mode': 'model'})
    utterance = await GeminiTeacher(client).respond(request())
    assert utterance.generation_mode == 'fallback'
    assert '*' not in utterance.spoken_text
    assert utterance.spoken_text.count('?') <= 1
    assert 'repeat' not in utterance.spoken_text.casefold()
    assert 'I live in the countryside.' in utterance.spoken_text


@pytest.mark.asyncio
@pytest.mark.parametrize('action', ['answer_teacher_question', 'explain_meaning',
                                  'acknowledge_and_continue', 'offer_support'])
async def test_fallback_never_reads_internal_activity_instructions_to_learner(action):
    internal = 'Record the opportunity as handled without claiming the learner asked.'
    client = FakeClient({'unexpected': 'invalid structured response'})
    utterance = await GeminiTeacher(client).respond(request(
        feedback_action=action, corrected_form=None, next_teaching_move=internal))
    assert utterance.generation_mode == 'fallback'
    assert internal not in utterance.spoken_text
    assert 'opportunity as handled' not in utterance.spoken_text
