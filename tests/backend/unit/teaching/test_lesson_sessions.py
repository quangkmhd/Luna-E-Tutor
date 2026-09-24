import pytest

from luna_tutor.curriculum.lesson_content import ScriptedLesson
from luna_tutor.llm.jev_turn_evaluator import TurnEvaluation
from luna_tutor.teaching.lesson_sessions import ScriptedSessionStore


class Evaluator:
    async def evaluate_turn(self, **kwargs):
        return TurnEvaluation.PASSED


class Teacher:
    def __init__(self):
        self.messages = []

    def snapshot(self):
        return list(self.messages)

    def restore(self, messages):
        self.messages = messages

    def jev_history(self):
        return list(self.messages)

    def record_say(self, text):
        self.messages.append(('assistant', text))

    def record_query(self, text):
        self.messages.append(('user', text))

    def record_output(self, text):
        self.messages.append(('assistant', text))

    async def respond(self, instruction):
        return 'Teacher reply.'


class Catalog:
    unit = {'id': 'grade03.unit01', 'grade': 3, 'unit': 1, 'title': 'Hello'}

    def load(self, _unit_id, _lesson_id):
        return ScriptedLesson.model_validate({
            'lesson': 1, 'title': 'Hello', 'items': [
                {'type': 'practice', 'say': 'Say hello.', 'learner_goal': 'Say Hello.'},
                {'type': 'end', 'say': 'Done.'},
            ]})


class IllustratedCatalog(Catalog):
    def load(self, _unit_id, _lesson_id):
        return ScriptedLesson.model_validate({
            'lesson': 1, 'title': 'Hello', 'items': [
                {'type': 'practice', 'say': 'Say hello.',
                 'learner_goal': 'Say Hello.', 'image_url': '/hello.png'},
                {'type': 'end', 'say': 'Done.'},
            ]})


class NarratedCatalog(Catalog):
    def load(self, _unit_id, _lesson_id):
        return ScriptedLesson.model_validate({
            'lesson': 1, 'title': 'Hello', 'items': [
                {'type': 'narration', 'say': 'Welcome.'},
                {'type': 'practice', 'say': 'Say hello.', 'learner_goal': 'Say Hello.'},
                {'type': 'end', 'say': 'Done.'},
            ]})


def make_store():
    return ScriptedSessionStore(Catalog(), lambda: Evaluator(), lambda: Teacher())


@pytest.mark.asyncio
async def test_opening_image_remains_on_its_message_after_lesson_advances():
    store = ScriptedSessionStore(IllustratedCatalog(), lambda: Evaluator(), lambda: Teacher())
    session = store.create('grade03.unit01', 1)
    await store.submit(session.id, 't1', 'Hello', session.version)
    assert session.messages[0]['image_url'] == '/hello.png'


@pytest.mark.asyncio
async def test_text_session_resets_by_creating_new_and_does_not_resume_after_exit():
    store = make_store()
    first = store.create('grade03.unit01', 1)
    assert first.messages == [{'role': 'teacher', 'text': 'Say hello.'}]
    await store.submit(first.id, 't1', 'Hello', first.version)
    assert first.status == 'completed'
    assert [item['text'] for item in first.messages] == [
        'Say hello.', 'Hello', 'Done.']
    await store.close(first.id)
    with pytest.raises(LookupError):
        store.get(first.id)
    second = store.create('grade03.unit01', 1)
    assert second.version == 0
    assert second.messages == [{'role': 'teacher', 'text': 'Say hello.'}]


@pytest.mark.asyncio
async def test_voice_switch_replays_active_say_then_waits_for_ack():
    store = make_store()
    session = store.create('grade03.unit01', 1)
    assert [item.text for item in await store.start_voice(session.id)] == ['Say hello.']
    with pytest.raises(RuntimeError, match='delivery'):
        await store.submit(session.id, 't1', 'Hello', session.version)
    assert await store.finish_voice_delivery(session.id) == []
    first_output = await store.submit(session.id, 't1', 'Hello', session.version, source='voice')
    assert [item.text for item in first_output] == ['Done.']
    assert await store.submit(session.id, 't1', 'Hello', 0, source='voice') == first_output
    assert session.version == 1
    assert session.status == 'active'
    assert [item['text'] for item in session.messages] == ['Say hello.', 'Hello']
    assert await store.finish_voice_delivery(session.id) == []
    assert session.status == 'completed'
    assert session.messages[-1]['text'] == 'Done.'


@pytest.mark.asyncio
async def test_voice_replays_full_opening_and_pending_output_after_reconnect():
    store = ScriptedSessionStore(NarratedCatalog(), lambda: Evaluator(), lambda: Teacher())
    session = store.create('grade03.unit01', 1)
    assert [item.text for item in await store.start_voice(session.id)] == [
        'Welcome.', 'Say hello.']
    assert [item.text for item in await store.start_voice(session.id)] == [
        'Welcome.', 'Say hello.']
    await store.finish_voice_delivery(session.id)
    output = await store.submit(session.id, 't1', 'Hello', session.version, source='voice')
    assert [item.text for item in output] == ['Done.']
    assert await store.start_voice(session.id) == output
    assert await store.finish_voice_delivery(session.id) == []
    assert session.status == 'completed'
