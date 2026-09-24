import pytest

from luna_tutor.curriculum.lesson_content import ScriptedLesson
from luna_tutor.llm.jev_turn_evaluator import TurnEvaluation as Code
from luna_tutor.teaching.lesson_conversation import ScriptedConversation, Spoken


def lesson():
    return ScriptedLesson.model_validate({
        'lesson': 1, 'title': 'Hello', 'items': [
            {'type': 'practice', 'say': 'Say hello.', 'learner_goal': 'Say Hello.'},
            {'type': 'practice', 'say': 'Say goodbye.', 'learner_goal': 'Say Goodbye.'},
            {'type': 'end', 'say': 'Done.'},
        ]})


class FakeTeacher:
    def __init__(self):
        self.messages = []
        self.rules = []

    def jev_history(self):
        return list(self.messages)

    def snapshot(self):
        return list(self.messages)

    def restore(self, messages):
        self.messages = messages

    def record_say(self, text):
        self.messages.append({'role': 'assistant', 'content': text})

    def record_query(self, text):
        self.messages.append({'role': 'user', 'content': text})

    def record_output(self, text):
        self.messages.append({'role': 'assistant', 'content': text})

    async def respond(self, instruction):
        self.rules.append(instruction)
        return 'Teacher correction.'


class FakeEvaluator:
    def __init__(self, *codes):
        self.codes = iter(codes)
        self.calls = []

    async def evaluate_turn(self, **kwargs):
        self.calls.append(kwargs)
        return next(self.codes)


@pytest.mark.asyncio
async def test_text_passed_uses_one_jev_code_and_original_next_say():
    teacher = FakeTeacher()
    jev = FakeEvaluator(Code.PASSED)
    conversation = ScriptedConversation(lesson(), jev, teacher, mode='text')
    assert conversation.start() == [Spoken('Say hello.', 'say')]
    assert await conversation.submit('t1', 'Hello') == [Spoken('Say goodbye.', 'say')]
    assert jev.calls[0]['history'] == [{'role': 'assistant', 'content': 'Say hello.'}]
    assert teacher.rules == []
    assert conversation.controller.phase == 'ready'


@pytest.mark.asyncio
async def test_voice_waits_for_teacher_then_next_say_delivery():
    teacher = FakeTeacher()
    jev = FakeEvaluator(Code.PASSED_WITH_REPLY)
    conversation = ScriptedConversation(lesson(), jev, teacher, mode='voice')
    assert conversation.start() == [Spoken('Say hello.', 'say')]
    assert conversation.controller.phase == 'delivering_script'
    assert conversation.delivery_finished() == []
    assert conversation.controller.phase == 'ready'
    assert await conversation.submit('t1', 'Hello, how are you?') == [
        Spoken('Teacher correction.', 'teacher')]
    assert 'Kênh hiện tại là Text' not in teacher.rules[0].description
    assert conversation.controller.phase == 'delivering_teacher'
    assert conversation.delivery_finished() == [Spoken('Say goodbye.', 'say')]
    assert conversation.controller.phase == 'delivering_script'
    assert conversation.delivery_finished() == []
    assert conversation.controller.phase == 'ready'
    assert teacher.messages == [
        {'role': 'assistant', 'content': 'Say hello.'},
        {'role': 'user', 'content': 'Hello, how are you?'},
        {'role': 'assistant', 'content': 'Teacher correction.'},
        {'role': 'assistant', 'content': 'Say goodbye.'},
    ]


@pytest.mark.asyncio
async def test_duplicate_id_does_not_call_jev_twice_or_increase_failed_count():
    teacher = FakeTeacher()
    jev = FakeEvaluator(Code.ATTEMPT_FAILED)
    conversation = ScriptedConversation(lesson(), jev, teacher, mode='text')
    conversation.start()
    first = await conversation.submit('same', 'Wrong')
    assert first == [Spoken('Teacher correction.', 'teacher')]
    assert await conversation.submit('same', 'Wrong') == first
    assert len(jev.calls) == 1
    assert conversation.controller.attempt_count == 1
    assert 'Kênh hiện tại là Text' in teacher.rules[0].description


@pytest.mark.asyncio
async def test_jev_error_keeps_goal_counter_and_history():
    teacher = FakeTeacher()
    class BrokenEvaluator:
        async def evaluate_turn(self, **kwargs):
            raise RuntimeError('provider failure')
    conversation = ScriptedConversation(lesson(), BrokenEvaluator(), teacher, mode='text')
    conversation.start()
    with pytest.raises(RuntimeError, match='provider failure'):
        await conversation.submit('t1', 'Hello')
    assert conversation.controller.attempt_count == 0
    assert conversation.controller.phase == 'ready'
    assert teacher.messages == [{'role': 'assistant', 'content': 'Say hello.'}]


@pytest.mark.asyncio
async def test_teacher_error_keeps_goal_counter_and_history():
    teacher = FakeTeacher()
    async def fail(_instruction):
        raise RuntimeError('teacher failure')
    teacher.respond = fail
    conversation = ScriptedConversation(
        lesson(), FakeEvaluator(Code.ATTEMPT_FAILED), teacher, mode='text')
    conversation.start()
    with pytest.raises(RuntimeError, match='teacher failure'):
        await conversation.submit('t1', 'Wrong')
    assert conversation.controller.attempt_count == 0
    assert conversation.controller.phase == 'ready'
    assert teacher.messages == [{'role': 'assistant', 'content': 'Say hello.'}]
