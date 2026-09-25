from pathlib import Path

import pytest

from luna_tutor.curriculum.lesson_content import load_scripted_lesson
from luna_tutor.curriculum.lesson_stations import active_station
from luna_tutor.llm.jev_turn_evaluator import TurnEvaluation
from luna_tutor.teaching.lesson_progression import ScriptedLessonSession


ROOT = Path(__file__).resolve().parents[4] / 'curriculum/grade-03/unit-01'


def test_lesson_one_warmup_precedes_station_one():
    lesson = load_scripted_lesson(ROOT / 'lesson-01/content.yaml')
    warmup = lesson.items[:6]

    assert [item.type for item in warmup] == [
        'practice', 'practice', 'practice', 'practice', 'practice', 'narration']
    assert 'Ready?' in warmup[0].say
    assert 'Con đã biết câu chào tiếng Anh nào chưa?' in warmup[1].say
    assert 'Excellent!' in warmup[2].say
    assert 'One, two, three' in warmup[2].say
    assert 'Now letters. Listen first! H.' in warmup[3].say
    assert 'And B.' in warmup[4].say
    assert "Remember H! It starts today's big word." in warmup[5].say
    assert 'Trạm 1' in lesson.items[6].say
    assert [active_station(1, index) for index in range(7)] == [
        None, None, None, None, None, None, 1]
    assert active_station(1, 14) == 2
    assert active_station(1, 21) == 3


@pytest.mark.parametrize('lesson_id', [1, 2, 3, 4])
def test_real_grade3_lesson_opens_and_advances_to_end(lesson_id):
    lesson = load_scripted_lesson(
        ROOT / f'lesson-{lesson_id:02d}' / 'content.yaml')
    assert lesson.lesson == lesson_id
    assert lesson.cards
    assert all('{tên}' not in item.say for item in lesson.items)
    assert all(item.learner_goal.strip() for item in lesson.items if item.type == 'practice')

    session = ScriptedLessonSession(lesson)
    opening = session.start()
    if lesson_id == 1:
        assert opening[0].text.startswith("<en>Hi! My name is Luna. I'm your English tutor!</en>")
    session.delivery_finished()
    attempts = 0
    while session.phase != 'completed':
        attempts += 1
        assert attempts <= len(lesson.items)
        spoken = session.handle_turn(f'turn-{attempts}', 'sample answer', TurnEvaluation.PASSED)
        assert spoken
        session.delivery_finished()
    assert attempts == sum(item.type == 'practice' for item in lesson.items)
    assert lesson.items[-1].type == 'end'
