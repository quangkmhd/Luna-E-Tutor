from unittest.mock import AsyncMock

import pytest
from luna_tutor.llm.jev_turn_evaluator import TurnEvaluation
from luna_tutor.teaching.lesson_progression import TeacherInstruction
from luna_tutor.teaching.teacher_context import ScriptedTeacherContext


@pytest.mark.asyncio
async def test_teacher_context_keeps_say_and_conversation_but_replaces_old_rule():
    llm = AsyncMock()
    llm.run_inference.side_effect = ['<en>Try a greeting.</en>', '<en>Say hello in English.</en>']
    teacher = ScriptedTeacherContext(llm)
    teacher.record_say('Say hello.')
    teacher.record_query('What does hello mean?')
    first = TeacherInstruction(TurnEvaluation.OTHER_INTENT, 'Say Hello.', 'Explain, then redirect.')
    assert await teacher.respond(first) == '<en>Try a greeting.</en>'
    teacher.record_output('<en>Try a greeting.</en>')
    teacher.record_query('Xin chào')
    second = TeacherInstruction(TurnEvaluation.ATTEMPT_FAILED, 'Say Hello.', 'Correct one point.', 1)
    assert await teacher.respond(second) == '<en>Say hello in English.</en>'
    messages = teacher.context.get_messages()
    assert [message['role'] for message in messages] == [
        'developer', 'assistant', 'user', 'assistant', 'user']
    assert messages[0]['content'] == 'Correct one point.'
    assert messages[1]['content'] == 'Say hello.'
    assert teacher.jev_history() == [
        {'role': 'assistant', 'content': 'Say hello.'},
        {'role': 'user', 'content': 'What does hello mean?'},
        {'role': 'assistant', 'content': '<en>Try a greeting.</en>'},
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
    llm.run_inference.return_value = '<en>Try that again.</en>'
    teacher = ScriptedTeacherContext(llm)
    teacher.context.add_message({'role': 'developer', 'content': 'Obsolete turn rule.'})
    for index in range(11):
        teacher.record_say(f'Luna line {index}')
        teacher.record_query(f'Learner line {index}')
    instruction = TeacherInstruction(TurnEvaluation.OTHER_INTENT, 'Say hello', 'Reply, then return.')
    assert await teacher.respond(instruction) == '<en>Try that again.</en>'
    llm._generate_summary.assert_awaited_once()
    assert 'developer' not in summary_roles
    messages = teacher.context.get_messages()
    assert messages[0] == {'role': 'developer', 'content': 'Reply, then return.'}
    assert any('Prior lesson conversation.' in str(message['content']) for message in messages)
    assert messages[-1] == {'role': 'user', 'content': 'Learner line 10'}
    await teacher.close()


@pytest.mark.asyncio
async def test_teacher_retries_invalid_bilingual_markup_before_delivery():
    llm = AsyncMock()
    llm.run_inference.side_effect = [
        '<vi>Con làm tốt.</vi><en>Hello</vi>',
        '<vi>Con làm tốt.</vi><en>Hello.</en>',
    ]
    teacher = ScriptedTeacherContext(llm)
    instruction = TeacherInstruction(TurnEvaluation.OTHER_INTENT, 'Say hello', 'Reply briefly.')
    assert await teacher.respond(instruction) == '<vi>Con làm tốt.</vi><en>Hello.</en>'
    assert llm.run_inference.await_count == 2
    assert [message['role'] for message in teacher.context.get_messages()] == ['developer']
    await teacher.close()


@pytest.mark.asyncio
async def test_teacher_retries_unsupported_symbols_before_delivery():
    llm = AsyncMock()
    llm.run_inference.side_effect = ['<en>Great!</en>', '<en>Great.</en>']
    teacher = ScriptedTeacherContext(llm)
    instruction = TeacherInstruction(TurnEvaluation.OTHER_INTENT, 'Say hello', 'Reply briefly.')
    assert await teacher.respond(instruction) == '<en>Great.</en>'
    assert llm.run_inference.await_count == 2
    await teacher.close()


@pytest.mark.asyncio
async def test_teacher_rejects_unmarked_output_after_retry():
    from luna_tutor.teaching.teacher_context import InvalidTeacherOutputError

    llm = AsyncMock()
    llm.run_inference.side_effect = ['Hello!', '[long pause]']
    teacher = ScriptedTeacherContext(llm)
    instruction = TeacherInstruction(TurnEvaluation.OTHER_INTENT, 'Say hello', 'Reply briefly.')
    with pytest.raises(InvalidTeacherOutputError, match='language markup'):
        await teacher.respond(instruction)
    assert llm.run_inference.await_count == 2
    await teacher.close()
