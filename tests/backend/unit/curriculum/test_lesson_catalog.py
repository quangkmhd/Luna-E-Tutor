from pathlib import Path

import pytest

from luna_tutor.curriculum.lesson_catalog import ScriptedCatalog


ROOT = Path(__file__).resolve().parents[4] / 'curriculum'


def test_catalog_lists_only_grade3_lessons():
    catalog = ScriptedCatalog(ROOT)
    assert [unit['id'] for unit in catalog.units()] == ['grade03.unit01']
    lessons = catalog.lessons('grade03.unit01')
    assert len(lessons) == 4
    assert lessons[0]['lesson'] == 1


def test_catalog_loads_each_authored_grade3_lesson():
    catalog = ScriptedCatalog(ROOT)
    for lesson_id in range(1, 5):
        lesson = catalog.load('grade03.unit01', lesson_id)
        assert lesson.lesson == lesson_id
        assert lesson.items[0].type == 'practice'
        assert lesson.items[-1].type == 'end'


def test_catalog_rejects_removed_grade5():
    catalog = ScriptedCatalog(ROOT)
    with pytest.raises(LookupError):
        catalog.lessons('grade05.unit01')
