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

    async def text_chat(self, messages, request_id):
        result = await self.structured_chat(messages, None, request_id)
        if isinstance(result, dict) and 'spoken_text' in result:
            return result['spoken_text']
        return result


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
async def test_teacher_requests_plain_text_and_assigns_internal_metadata():
    class PlainTextClient:
        def __init__(self):
            self.calls = []

        async def text_chat(self, messages, request_id):
            self.calls.append((messages, request_id))
            return 'Good answer, Quang! What do you like about the countryside?'

        async def structured_chat(self, *_args):
            pytest.fail('Teacher must not request structured JSON output')

    client = PlainTextClient()
    result = await GeminiTeacher(client).respond(request(
        feedback_action='acknowledge_and_continue', corrected_form=None,
        constraints=TeacherConstraints(encouragement_required=True)))

    assert result.spoken_text.startswith('Good answer, Quang!')
    assert result.generation_mode == 'model'
    assert result.delivery_intent == 'encouraging'
    assert client.calls[0][1] == 'turn-1'


@pytest.mark.asyncio
async def test_teacher_receives_bounded_request_without_progression_authority():
    client = FakeClient({'spoken_text': 'Oh, you live in the countryside. What do you like about it?',
                         'delivery_intent': 'encouraging', 'generation_mode': 'model'})
    utterance = await GeminiTeacher(client).respond(request())
    assert utterance.spoken_text.startswith('Oh, you live')
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


@pytest.mark.asyncio
async def test_natural_second_person_recast_is_accepted_without_fallback():
    text = 'Oh, you live in the countryside! What do you like about it?'
    client = FakeClient({'spoken_text': text, 'delivery_intent': 'warm',
                         'generation_mode': 'model'})
    result = await GeminiTeacher(client).respond(request())
    assert result.generation_mode == 'model'
    assert result.spoken_text == text


@pytest.mark.asyncio
async def test_second_person_recast_still_requires_correct_target_form():
    client = FakeClient({'spoken_text': 'Oh, you live countryside! What do you like?',
                         'delivery_intent': 'warm', 'generation_mode': 'model'})
    result = await GeminiTeacher(client).respond(request())
    assert result.generation_mode == 'fallback'


@pytest.mark.asyncio
async def test_teacher_repairs_two_questions_once_without_changing_teaching_request():
    class SequenceClient(FakeClient):
        async def structured_chat(self, messages, schema, request_id):
            self.calls.append((messages, schema, request_id))
            text = ('When is your birthday? Is it in May or June?' if len(self.calls) == 1
                    else 'Is your birthday in May or June?')
            return {'spoken_text': text, 'delivery_intent': 'warm', 'generation_mode': 'model'}
    client = SequenceClient()
    original = request(feedback_action='offer_support', corrected_form=None)
    result = await GeminiTeacher(client).respond(original)
    assert result.generation_mode == 'model'
    assert result.spoken_text == 'Is your birthday in May or June?'
    assert len(client.calls) == 2
    repaired = json.loads(client.calls[1][0][1]['content'])
    assert repaired.pop('validation_feedback')
    assert repaired == original.model_dump(mode='json')


@pytest.mark.asyncio
async def test_required_encouragement_repairs_bare_confirmation():
    class SequenceClient(FakeClient):
        async def structured_chat(self, messages, schema, request_id):
            self.calls.append((messages, schema, request_id))
            text = ('Yes, dolphins live in the ocean. Pink, pink. Can you say pink?'
                    if len(self.calls) == 1 else
                    'Dolphins live in the ocean. Good answer! Pink, pink. Can you say pink?')
            return {'spoken_text': text, 'delivery_intent': 'encouraging',
                    'generation_mode': 'model'}

    client = SequenceClient()
    result = await GeminiTeacher(client).respond(request(
        feedback_action='acknowledge_and_continue', corrected_form=None,
        constraints=TeacherConstraints(encouragement_required=True)))

    assert result.spoken_text.startswith('Dolphins live in the ocean. Good answer!')
    assert len(client.calls) == 2
    repaired = json.loads(client.calls[1][0][1]['content'])
    assert any('encouragement' in item.lower() for item in repaired['validation_feedback'])


@pytest.mark.asyncio
async def test_repair_keeps_encouragement_requirement_when_another_check_failed():
    class SequenceClient(FakeClient):
        async def structured_chat(self, messages, schema, request_id):
            self.calls.append((messages, schema, request_id))
            text = ('Good answer! First question? Second question?'
                    if len(self.calls) == 1 else
                    'Good answer! One question?')
            return {'spoken_text': text, 'delivery_intent': 'encouraging',
                    'generation_mode': 'model'}

    client = SequenceClient()
    await GeminiTeacher(client).respond(request(
        feedback_action='acknowledge_and_continue', corrected_form=None,
        constraints=TeacherConstraints(encouragement_required=True)))

    repaired = json.loads(client.calls[1][0][1]['content'])
    assert any('encouragement' in item.lower() for item in repaired['validation_feedback'])


@pytest.mark.asyncio
async def test_required_encouragement_allows_one_extra_bounded_repair():
    class SequenceClient(FakeClient):
        async def structured_chat(self, messages, schema, request_id):
            self.calls.append((messages, schema, request_id))
            text = ('Yes, that is right. One question? Second question?'
                    if len(self.calls) < 3 else
                    'Good answer! One question?')
            return {'spoken_text': text, 'delivery_intent': 'encouraging',
                    'generation_mode': 'model'}

    client = SequenceClient()
    result = await GeminiTeacher(client).respond(request(
        feedback_action='acknowledge_and_continue', corrected_form=None,
        constraints=TeacherConstraints(encouragement_required=True)))

    assert result.generation_mode == 'model'
    assert result.spoken_text == 'Good answer! One question?'
    assert len(client.calls) == 3


@pytest.mark.asyncio
async def test_teacher_repair_is_bounded():
    client = FakeClient({'spoken_text': 'First question? Second question?',
                         'delivery_intent': 'warm', 'generation_mode': 'model'})
    result = await GeminiTeacher(client).respond(request(feedback_action='offer_support', corrected_form=None))
    assert result.generation_mode == 'fallback'
    assert len(client.calls) == 2


@pytest.mark.asyncio
async def test_teacher_does_not_retry_provider_outage():
    from luna_tutor.llm.openrouter import ProviderError
    client = FakeClient(error=ProviderError(status_code=503, request_id='t', reason='unavailable'))
    with pytest.raises(ProviderError) as caught:
        await GeminiTeacher(client).respond(request())
    assert caught.value.status_code == 503
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_new_word_must_have_pending_models_and_invitation():
    from luna_tutor.domain.decisions import TeacherActivityContext
    class SequenceClient(FakeClient):
        async def structured_chat(self, messages, schema, request_id):
            self.calls.append((messages, schema, request_id))
            return {'spoken_text': ('Cottage. Cottage.' if len(self.calls) == 1
                                    else 'Cottage. Cottage. Can you say cottage?'),
                    'delivery_intent': 'warm', 'generation_mode': 'model'}
    client = SequenceClient()
    context = TeacherActivityContext(stage_id='level-03', activity_id='level-03.introduce-cottage',
        kind='vocabulary_introduction',target_words=('cottage',),model_repetitions=2,
        remaining_model_repetitions=2,needs_response_invitation=True)
    result = await GeminiTeacher(client).respond(request(
        feedback_action='answer_teacher_question',corrected_form=None,activity_context=context))
    assert result.spoken_text.endswith('Can you say cottage?')
    assert len(client.calls) == 2


@pytest.mark.asyncio
async def test_new_word_question_must_invite_using_that_word():
    from luna_tutor.domain.decisions import TeacherActivityContext
    client = FakeClient({'spoken_text': 'Cottage. Cottage. What is near your home?',
                         'delivery_intent': 'warm', 'generation_mode': 'model'})
    context = TeacherActivityContext(stage_id='level-03',activity_id='level-03.introduce-cottage',
        kind='vocabulary_introduction',target_words=('cottage',),model_repetitions=2,
        remaining_model_repetitions=2,needs_response_invitation=True)
    result = await GeminiTeacher(client).respond(request(
        feedback_action='acknowledge_and_continue',corrected_form=None,activity_context=context))
    assert result.generation_mode == 'fallback'


@pytest.mark.asyncio
async def test_recast_does_not_turn_child_fact_into_teacher_biography():
    client = FakeClient({'spoken_text': 'My birthday is in May! What is your hobby?',
                         'delivery_intent': 'warm', 'generation_mode': 'model'})
    result = await GeminiTeacher(client).respond(request(
        learner_meaning='My birthday on May.',corrected_form='My birthday is in May.'))
    assert result.generation_mode == 'fallback'


@pytest.mark.asyncio
@pytest.mark.parametrize(('correction', 'text', 'accepted'), [
    ('My town has good schools; moreover, there is an amusement park.',
     'Your town has good schools, and moreover, there is an amusement park!', True),
    ('I am in Class 5B. I live in the city.',
     "You live in the city, and you're in Class 5B!", True),
    ("I'm in Class 5B.", 'You are in Class 5B!', True),
    ('My town has good schools; moreover, there is an amusement park.',
     'Your town have good schools; moreover, there is an amusement park!', False),
    ('My town has good schools; moreover, there is an amusement park.',
     'Your town has good schools!', False),
    ('I am in Class 5B. I live in the city.',
     "You're in Class 5A, and you live in the city!", False),
])
async def test_recast_allows_clause_variation_without_dropping_corrected_facts(correction, text, accepted):
    client = FakeClient({'spoken_text': text, 'delivery_intent': 'warm', 'generation_mode': 'model'})
    result = await GeminiTeacher(client).respond(request(corrected_form=correction))
    assert (result.generation_mode == 'model') is accepted
    if accepted:
        assert result.spoken_text == text
        assert len(client.calls) == 1
