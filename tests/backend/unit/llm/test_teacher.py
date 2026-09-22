import json
import logging

import pytest

from luna_tutor.domain.decisions import TeacherConstraints, TeacherTurnRequest
from luna_tutor.llm.teacher import GeminiTeacher


class FakeClient:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    async def text_chat(self, messages, request_id):
        self.calls.append((messages, request_id))
        if self.error:
            raise self.error
        if isinstance(self.result, dict) and 'spoken_text' in self.result:
            return self.result['spoken_text']
        return self.result


def request(**changes):
    values = dict(
        turn_id='turn-1', unit_id='grade05.unit01', feedback_action='recast',
        corrected_form='I live in the countryside.',
        learner_meaning='Quang lives in the countryside.',
        next_teaching_move='Ask what Quang likes about it.',
        emotional_support=False, constraints=TeacherConstraints(),
    )
    values.update(changes)
    return TeacherTurnRequest(**values)


@pytest.mark.asyncio
async def test_teacher_requests_plain_text_and_assigns_internal_metadata():
    client = FakeClient('Good answer, Quang! What do you like about the countryside?')

    result = await GeminiTeacher(client).respond(request())

    assert result.spoken_text.startswith('Good answer, Quang!')
    assert result.generation_mode == 'model'
    assert result.delivery_intent == 'encouraging'
    assert client.calls[0][1] == 'turn-1'


@pytest.mark.asyncio
async def test_teacher_receives_bounded_request_without_progression_authority():
    client = FakeClient('Oh, you live in the countryside. What do you like about it?')

    await GeminiTeacher(client).respond(request())

    payload = json.loads(client.calls[0][0][1]['content'])
    assert payload['feedback_action'] == 'recast'
    assert payload['corrected_form'] == 'I live in the countryside.'
    assert payload['next_teaching_move'] == 'Ask what Quang likes about it.'
    assert payload['constraints']['max_questions'] == 1
    assert 'progression_action' not in payload
    assert 'next_state' not in payload
    assert 'tools' not in payload


@pytest.mark.asyncio
async def test_teacher_receives_recast_request_without_evaluator_generated_wording():
    client = FakeClient('You live in the countryside. What do you like about it?')

    await GeminiTeacher(client).respond(request(corrected_form=None))

    payload = json.loads(client.calls[0][0][1]['content'])
    assert payload['feedback_action'] == 'recast'
    assert payload['corrected_form'] is None
    assert payload['learner_meaning'] == 'Quang lives in the countryside.'


@pytest.mark.asyncio
async def test_teacher_forwards_repeated_vocabulary_invitation_without_retry():
    client = FakeClient('Say hello again!')
    result = await GeminiTeacher(client).respond(request(
        previous_teacher_turn='Say hello again!',
    ))

    assert result.spoken_text == 'Say hello again!'
    assert len(client.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('text', [
    '**Repeat after me:** I live in the countryside? Again?',
    'First question? Second question?',
    'Oh, you live countryside!',
    'Cottage. Cottage.',
    'My birthday is in May!',
])
async def test_teacher_forwards_model_text_without_custom_validation_or_retry(text):
    client = FakeClient(text)

    result = await GeminiTeacher(client).respond(request())

    assert result.generation_mode == 'model'
    assert result.spoken_text == text
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_teacher_does_not_retry_provider_outage():
    from luna_tutor.llm.openrouter import ProviderError

    client = FakeClient(error=ProviderError(
        status_code=503, request_id='t', reason='unavailable'))

    with pytest.raises(ProviderError) as caught:
        await GeminiTeacher(client).respond(request())

    assert caught.value.status_code == 503
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_teacher_propagates_invalid_model_output_without_fallback():
    from luna_tutor.llm.openrouter import InvalidModelOutputError

    client = FakeClient(error=InvalidModelOutputError(
        status_code=200, request_id='t', reason='Invalid text model output'))

    with pytest.raises(InvalidModelOutputError):
        await GeminiTeacher(client).respond(request())

    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_teacher_logs_forwarded_response_with_turn_id(caplog):
    client = FakeClient('You are doing well! City. City. Can you say city?')

    with caplog.at_level(logging.INFO, logger='luna_tutor.llm.teacher'):
        await GeminiTeacher(client).respond(request())

    messages = [record.getMessage() for record in caplog.records]
    assert any('teacher_generation_started' in message and 'turn_id=turn-1' in message
               for message in messages)
    assert any('teacher_response_forwarded' in message and 'turn_id=turn-1' in message
               for message in messages)
