from unittest.mock import AsyncMock

import pytest

from luna_tutor.teaching.teacher_context import ScriptedTeacherContext
from luna_tutor.teaching.lesson_progression import TeacherInstruction
from luna_tutor.llm.jev_turn_evaluator import TurnEvaluation


@pytest.mark.asyncio
async def test_teacher_context_keeps_say_and_conversation_but_replaces_old_rule():
    llm = AsyncMock()
    llm.run_inference.side_effect = ['Try a greeting.', 'Say hello in English.']
    teacher = ScriptedTeacherContext(llm)
    teacher.record_say('Say hello.')
    teacher.record_query('What does hello mean?')
    first = TeacherInstruction(TurnEvaluation.OTHER_INTENT, 'Say Hello.', 'Explain, then redirect.')
    assert await teacher.respond(first) == 'Try a greeting.'
    teacher.record_output('Try a greeting.')
    teacher.record_query('Xin chào')
    second = TeacherInstruction(TurnEvaluation.ATTEMPT_FAILED, 'Say Hello.', 'Correct one point.', 1)
    assert await teacher.respond(second) == 'Say hello in English.'
    messages = teacher.context.get_messages()
    assert [message['role'] for message in messages] == [
        'developer', 'assistant', 'user', 'assistant', 'user']
    assert messages[0]['content'] == 'Correct one point.'
    assert messages[1]['content'] == 'Say hello.'
    assert teacher.jev_history() == [
        {'role': 'assistant', 'content': 'Say hello.'},
        {'role': 'user', 'content': 'What does hello mean?'},
        {'role': 'assistant', 'content': 'Try a greeting.'},
        {'role': 'user', 'content': 'Xin chào'},
    ]
    await teacher.close()


@pytest.mark.asyncio
async def test_teacher_uses_pipecat_auto_summary_before_current_developer_rule():
    llm = AsyncMock()
    summary_roles = []

    async def summarize(frame):
        summary_roles.extend(message['role'] for message in frame.context.get_messages())
        return 'Prior lesson conversation.', 17

    llm._generate_summary.side_effect = summarize
    llm.run_inference.return_value = 'Try that again.'
    teacher = ScriptedTeacherContext(llm)
    teacher.context.add_message({'role': 'developer', 'content': 'Obsolete turn rule.'})
    for index in range(11):
        teacher.record_say(f'Luna line {index}')
        teacher.record_query(f'Learner line {index}')
    instruction = TeacherInstruction(TurnEvaluation.OTHER_INTENT, 'Say hello', 'Reply, then return.')
    assert await teacher.respond(instruction) == 'Try that again.'
    llm._generate_summary.assert_awaited_once()
    assert 'developer' not in summary_roles
    messages = teacher.context.get_messages()
    assert messages[0] == {'role': 'developer', 'content': 'Reply, then return.'}
    assert any('Prior lesson conversation.' in str(message['content']) for message in messages)
    assert messages[-1] == {'role': 'user', 'content': 'Learner line 10'}
    await teacher.close()
