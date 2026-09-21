from pathlib import Path

import pytest
from luna_tutor.curriculum.excel_importer import import_workbook

ROOT = Path(__file__).resolve().parents[4]
WORKBOOK = ROOT / "docs/Global_Success_Khung_Nghe_Noi_3_Level_v3.xlsx"

EXPECTED = {
    2: ("Our homes", 19, 7),
    3: ("My foreign friends", 20, 7),
    4: ("Our free-time activities", 22, 7),
    5: ("My future job", 23, 7),
}


def test_unit2_number_label_is_not_a_vocabulary_target():
    imported = import_workbook(WORKBOOK, grade=5, unit=2)

    assert {"23", "38", "93", "116"} <= imported.vocabulary_ids()
    assert "numbers-23" not in imported.vocabulary_ids()


def test_unit4_slash_instrument_groups_are_three_targets():
    imported = import_workbook(WORKBOOK, grade=5, unit=4)

    assert {
        "percussion-instruments",
        "wind-instruments",
        "string-instruments",
    } <= imported.vocabulary_ids()


@pytest.mark.parametrize(
    ("unit", "title", "vocabulary_count", "pattern_count"),
    [(unit, *expected) for unit, expected in EXPECTED.items()],
)
def test_units_match_reviewed_content_bounds(
    unit, title, vocabulary_count, pattern_count
):
    imported = import_workbook(WORKBOOK, grade=5, unit=unit)

    assert imported.title == title
    assert len(imported.vocabulary) == vocabulary_count
    assert len(imported.patterns) == pattern_count
    assert [len(lesson.objective_ids) for lesson in imported.lessons] == [5, 5, 10]
