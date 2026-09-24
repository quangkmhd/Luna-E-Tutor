from pathlib import Path

import pytest

from luna_tutor.curriculum.lesson_content import load_scripted_lesson
from luna_tutor.llm.jev_turn_evaluator import TurnEvaluation
from luna_tutor.teaching.lesson_progression import ScriptedLessonSession


ROOT = Path(__file__).resolve().parents[4] / 'curriculum/grade-03/unit-01'


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
