from pathlib import Path
import re

from luna_tutor.curriculum.lesson_script import load_lesson_script


ROOT = Path(__file__).resolve().parents[4]
LESSON = ROOT / 'curriculum/grade-03/unit-01/lesson-01/content.yaml'


def test_lesson_one_is_a_editable_three_station_script():
    lesson = load_lesson_script(LESSON)
    assert lesson.lesson == 1
    assert lesson.greeting.order == 1
    assert lesson.stations[0].steps[0].order == 2
    assert lesson.stations[0].steps[0].target == 'hello'
    assert lesson.stations[0].steps[1].order == 3
    assert lesson.stations[0].steps[1].target == 'hi'
    assert '"HELLO" [long pause] nghĩa là xin chào' in lesson.stations[0].steps[0].say
    assert '[long pause]' in lesson.stations[0].steps[0].say
    assert any('Thiếu Hi vẫn đạt' in exchange.accept
               for station in lesson.stations for step in station.steps
               for exchange in (step, *step.more) if exchange.accept)


def test_spoken_models_are_quoted_and_paused_on_both_sides():
    lesson = load_lesson_script(LESSON)
    quoted = 0
    for station in lesson.stations:
        for step in station.steps:
            for exchange in (step, *step.more):
                for match in re.finditer(r'"[^"]+"', exchange.say):
                    quoted += 1
                    assert exchange.say[:match.start()].rstrip().endswith('[long pause]')
                    assert exchange.say[match.end():].lstrip().startswith('[long pause]')
    assert quoted >= 20
