import pytest

from luna_tutor.curriculum.lesson_content import ScriptedLesson
from luna_tutor.llm.jev_turn_evaluator import TurnEvaluation as Code
from luna_tutor.teaching.lesson_progression import Say, ScriptedLessonSession, TeacherInstruction


def lesson():
    return ScriptedLesson.model_validate({
        'lesson': 1, 'title': 'Hello', 'items': [
            {'type': 'narration', 'say': 'Intro.'},
            {'type': 'practice', 'say': 'Say hello.', 'learner_goal': 'Say Hello.'},
            {'type': 'narration', 'say': 'Transition.'},
            {'type': 'practice', 'say': 'Say goodbye.', 'learner_goal': 'Say Goodbye.'},
            {'type': 'end', 'say': 'Finished.'},
        ]})


def ready_session():
    session = ScriptedLessonSession(lesson())
    assert session.start() == [Say('Intro.'), Say('Say hello.')]
    assert session.phase == 'delivering_script'
    session.delivery_finished()
    assert session.phase == 'ready'
    return session


def test_passed_reads_authored_lines_and_resets_only_after_delivery():
    session = ready_session()
    assert session.handle_turn('t1', 'Hello', Code.PASSED) == [
        Say('Transition.'), Say('Say goodbye.')]
    assert session.phase == 'delivering_script'
    assert session.item_index == 1
    session.delivery_finished()
    assert session.item_index == 3
    assert session.attempt_count == 0
    assert session.handle_turn('t2', 'Goodbye', Code.PASSED) == [Say('Finished.')]
    session.delivery_finished()
    assert session.phase == 'completed'


def test_four_failures_select_four_distinct_rules_then_move_on():
    session = ready_session()
    for attempt in range(1, 5):
        result = session.handle_turn(f't{attempt}', 'Wrong', Code.ATTEMPT_FAILED)
        assert len(result) == 1 and isinstance(result[0], TeacherInstruction)
        assert result[0].code == Code.ATTEMPT_FAILED
        assert result[0].attempt == attempt
        assert result[0].learner_goal == 'Say Hello.'
        assert result[0].description
        assert session.attempt_count == attempt
        if attempt < 4:
            assert session.delivery_finished() == []
            assert session.phase == 'ready'
        else:
            assert session.delivery_finished() == [Say('Transition.'), Say('Say goodbye.')]
            assert session.attempt_count == 4
    session.delivery_finished()
    assert session.attempt_count == 0


@pytest.mark.parametrize('code', [Code.OTHER_INTENT, Code.UNCLEAR_INPUT])
def test_other_intent_and_unclear_do_not_count_or_advance(code):
    session = ready_session()
    result = session.handle_turn('t1', 'question', code)
    assert result[0].code == code
    assert session.attempt_count == 0
    assert session.delivery_finished() == []
    assert session.item_index == 1


def test_passed_with_reply_answers_before_next_say():
    session = ready_session()
    result = session.handle_turn('t1', 'Hello, how are you?', Code.PASSED_WITH_REPLY)
    assert isinstance(result[0], TeacherInstruction)
    assert session.phase == 'delivering_teacher'
    assert session.delivery_finished() == [Say('Transition.'), Say('Say goodbye.')]


def test_repeated_turn_id_never_recounts_or_replays():
    session = ready_session()
    session.handle_turn('same', 'wrong', Code.ATTEMPT_FAILED)
    assert session.handle_turn('same', 'wrong', Code.ATTEMPT_FAILED) == []
    session.delivery_finished()
    assert session.handle_turn('same', 'wrong', Code.ATTEMPT_FAILED) == []
    assert session.attempt_count == 1


def test_new_turn_cannot_arrive_during_delivery():
    session = ready_session()
    session.handle_turn('t1', 'wrong', Code.ATTEMPT_FAILED)
    with pytest.raises(RuntimeError, match='not ready'):
        session.handle_turn('t2', 'hello', Code.PASSED)
