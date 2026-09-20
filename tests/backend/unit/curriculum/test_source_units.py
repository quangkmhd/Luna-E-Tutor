import re
from pathlib import Path

import pytest
from luna_tutor.curriculum.excel_importer import import_workbook

ROOT = Path(__file__).resolve().parents[4]
WORKBOOK = ROOT / "docs/Global_Success_Khung_Nghe_Noi_3_Level_v3.xlsx"

EXPECTED = {
    2: ("Our homes", 19, 7, "A5", range(5, 8)),
    3: ("My foreign friends", 20, 7, "A8", range(8, 11)),
    4: ("Our free-time activities", 22, 7, "A11", range(11, 14)),
    5: ("My future job", 23, 7, "A14", range(14, 17)),
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
    ("unit", "title", "vocabulary_count", "pattern_count", "anchor", "source_rows"),
    [(unit, *expected) for unit, expected in EXPECTED.items()],
)
def test_units_match_reviewed_source_bounds(
    unit, title, vocabulary_count, pattern_count, anchor, source_rows
):
    imported = import_workbook(WORKBOOK, grade=5, unit=unit)

    assert imported.title == title
    assert imported.source.section == f"Lớp 5 (3 Level)!{anchor}"
    assert len(imported.vocabulary) == vocabulary_count
    assert len(imported.patterns) == pattern_count
    assert [len(lesson.objective_ids) for lesson in imported.lessons] == [5, 5, 10]

    sourced_items = [*imported.vocabulary, *imported.patterns, *imported.objectives]
    observed_rows = {
        int(re.search(r"\d+$", item.source.section).group()) for item in sourced_items
    }
    assert observed_rows <= set(source_rows)
