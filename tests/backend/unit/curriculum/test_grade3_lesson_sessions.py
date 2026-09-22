from pathlib import Path

import pytest

from luna_tutor.curriculum.registry import CurriculumRegistry
from luna_tutor.teaching.scripted_lesson import ScriptedLessonService


ROOT = Path(__file__).resolve().parents[4] / 'curriculum'


@pytest.mark.parametrize('lesson_id,title,first_word,review_prompt,conversation_prompt', [
    (2, 'Hỏi thăm sức khỏe và cảm ơn', 'how', 'How are you?', "I'm Tom from England"),
    (3, 'Chào tạm biệt và chào theo thời điểm', 'goodbye', 'Goodbye, Mai.', "Good evening, {tên}!"),
    (4, 'Ôn tập Unit 1', 'hello', 'Xin chào!', "I'm Emma from England"),
])
def test_grade3_followup_lessons_are_separate_three_station_sessions(
    lesson_id: int, title: str, first_word: str, review_prompt: str,
    conversation_prompt: str,
):
    registry = CurriculumRegistry(ROOT, ('grade03.unit01',))
    script = registry.get_lesson_script('grade03.unit01', lesson_id)
    service = ScriptedLessonService(script, evaluator=None, teacher=None)
    state = service.fresh_state(f'lesson-{lesson_id}')

    assert script.title == title
    assert state.lesson_id == lesson_id
    assert state.stage_id == 'greeting'
    assert state.opening_message == script.greeting.say
    assert [station.id for station in script.stations] == [
        'vocabulary', 'patterns', 'conversation',
    ]
    assert script.stations[0].steps[0].target == first_word
    assert any(review_prompt in opportunity.say for opportunity in service.opportunities)
    assert any(conversation_prompt in opportunity.say for opportunity in service.opportunities)
    assert {opportunity.stage for opportunity in service.opportunities} == {
        'greeting', 'vocabulary', 'patterns', 'conversation',
    }
    assert [step.order for step in script.steps()] == list(range(2, len(script.steps()) + 2))


def test_unit_one_lists_four_learner_sessions_in_order():
    registry = CurriculumRegistry(ROOT, ('grade03.unit01',))
    assert [(script.lesson, script.title) for script in registry.list_lesson_scripts('grade03.unit01')] == [
        (1, 'Chào hỏi và giới thiệu tên'),
        (2, 'Hỏi thăm sức khỏe và cảm ơn'),
        (3, 'Chào tạm biệt và chào theo thời điểm'),
        (4, 'Ôn tập Unit 1'),
    ]
