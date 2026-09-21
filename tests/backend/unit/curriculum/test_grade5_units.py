import re
from pathlib import Path

import pytest
from luna_tutor.curriculum.excel_importer import import_workbook
from luna_tutor.curriculum.loader import load_unit

ROOT = Path(__file__).resolve().parents[4]
WORKBOOK = ROOT / "docs/Global_Success_Khung_Nghe_Noi_3_Level_v3.xlsx"
IMPLEMENTED_UNIT_IDS = tuple(range(1, 6))
STAGE_ORDER = [
    "warm-up",
    "lesson-01",
    "lesson-02",
    "lesson-03",
    "level-02",
    "level-03",
    "free-talk",
    "summary",
]
TEACHING_STAGES = ("lesson-01", "lesson-02", "level-02", "level-03")
UNIT2_VOCABULARY = {
    "building", "flat", "house", "tower", "23", "38", "93", "116",
    "apartment", "garden", "neighbourhood", "floor",
    "underground", "beam", "mud", "skylight", "spring", "fossil-fuel", "coal",
}
UNIT3_VOCABULARY = {
    "american", "australian", "japanese", "malaysian",
    "active", "clever", "friendly", "helpful",
    "british", "canadian", "chinese", "korean", "singaporean", "thai",
    "traditional-clothes", "samba-parade", "chuseok", "rice-cakes",
    "lucky-money", "celebration",
}
UNIT4_VOCABULARY = {
    "go-for-a-walk", "play-the-violin", "surf-the-internet",
    "water-the-flowers", "always", "often", "sometimes", "usually",
    "collect-stamps", "do-puzzles", "play-board-games", "ride-a-bike",
    "electric-guitar", "drum-kit", "flute", "orchestra",
    "percussion-instruments", "wind-instruments", "string-instruments",
    "hit", "interact", "amazed",
}
UNIT5_VOCABULARY = {
    "firefighter", "gardener", "reporter", "writer",
    "grow-flowers", "report-the-news", "teach-children", "write-stories",
    "architect", "designer", "scientist", "vet",
    "fire-engine", "equipment", "rescue", "accident", "trap", "hose",
    "invent", "inventor", "create", "creative", "imagination",
}


@pytest.fixture(params=IMPLEMENTED_UNIT_IDS, ids=lambda number: f"unit-{number:02d}")
def grade5_unit(request):
    return load_unit(
        ROOT / f"curriculum/grade-05/unit-{request.param:02d}"
    )


@pytest.fixture
def unit_02():
    return load_unit(ROOT / "curriculum/grade-05/unit-02")


@pytest.fixture
def unit_03():
    return load_unit(ROOT / "curriculum/grade-05/unit-03")


@pytest.fixture
def unit_04():
    return load_unit(ROOT / "curriculum/grade-05/unit-04")


@pytest.fixture
def unit_05():
    return load_unit(ROOT / "curriculum/grade-05/unit-05")


def test_unit5_targets_match_reviewed_source(unit_05):
    assert unit_05.vocabulary_ids() == UNIT5_VOCABULARY
    assert {pattern.id for pattern in unit_05.patterns} == {
        "future-job", "job-reason", "job-duties", "family-job",
        "hypothetical-firefighter", "firefighter-rescue",
        "inventors-imagination",
    }
    imported = import_workbook(WORKBOOK, grade=5, unit=5)
    assert {
        item.id: (item.text, item.source.section)
        for item in unit_05.vocabulary
    } == {
        item.id: (item.text, item.source.section)
        for item in imported.vocabulary
    }
    assert {
        (item.text, item.source.section) for item in unit_05.patterns
    } == {
        (item.text, item.source.section) for item in imported.patterns
    }


def test_unit4_targets_and_internet_safety_match_reviewed_source(unit_04):
    assert unit_04.vocabulary_ids() == UNIT4_VOCABULARY
    assert {pattern.id for pattern in unit_04.patterns} == {
        "free-time-like", "weekend-routine", "invitation", "frequency",
        "comparative-cost", "superlative-singer", "correlative-preference",
    }
    assert all("/" not in item.text for item in unit_04.vocabulary)
    instructions = " ".join(
        activity.instruction for activity in unit_04.activities
    ).lower()
    assert "never ask for an internet username" in instructions
    imported = import_workbook(WORKBOOK, grade=5, unit=4)
    assert {
        item.id: (item.text, item.source.section)
        for item in unit_04.vocabulary
    } == {
        item.id: (item.text, item.source.section)
        for item in imported.vocabulary
    }
    assert {
        (item.text, item.source.section) for item in unit_04.patterns
    } == {
        (item.text, item.source.section) for item in imported.patterns
    }


def test_unit3_targets_and_fictional_cast_match_reviewed_source(unit_03):
    assert unit_03.vocabulary_ids() == UNIT3_VOCABULARY
    assert {pattern.id for pattern in unit_03.patterns} == {
        "nationality", "personality", "origin", "speak-english",
        "japan-childrens-day", "samba-origin", "chuseok-food",
    }
    roleplay = next(
        activity for activity in unit_03.activities
        if activity.id == "free-talk.conversation"
    )
    assert "fictional" in roleplay.instruction.lower()
    assert "real child" in roleplay.instruction.lower()

    imported = import_workbook(WORKBOOK, grade=5, unit=3)
    assert {
        item.id: (item.text, item.source.section)
        for item in unit_03.vocabulary
    } == {
        item.id: (item.text, item.source.section)
        for item in imported.vocabulary
    }
    assert {
        (item.text, item.source.section) for item in unit_03.patterns
    } == {
        (item.text, item.source.section) for item in imported.patterns
    }


def test_unit2_targets_match_reviewed_workbook_source(unit_02):
    assert unit_02.vocabulary_ids() == UNIT2_VOCABULARY
    assert {pattern.id for pattern in unit_02.patterns} == {
        "home-type",
        "address",
        "house-floors",
        "home-choice",
        "eco-house",
        "skylight-purpose",
        "house-materials",
    }


def test_unit2_authored_targets_match_imported_workbook_text_and_source(unit_02):
    imported = import_workbook(WORKBOOK, grade=5, unit=2)

    authored_vocabulary = {
        item.id: (item.text, item.source.section)
        for item in unit_02.vocabulary
    }
    imported_vocabulary = {
        item.id: (item.text, item.source.section)
        for item in imported.vocabulary
    }
    assert authored_vocabulary == imported_vocabulary

    assert {
        (item.text, item.source.section) for item in unit_02.patterns
    } == {
        (item.text, item.source.section) for item in imported.patterns
    }


def test_unit2_address_activity_is_fictional_and_privacy_bounded(unit_02):
    activity = next(
        activity
        for activity in unit_02.activities
        if activity.id == "lesson-02.fictional-address"
    )
    text = " ".join([activity.instruction, *activity.examples]).lower()
    assert "fictional" in text
    assert "real address" in text


def test_grade5_unit_stage_and_activity_contract(grade5_unit):
    assert [stage.id for stage in grade5_unit.stages] == STAGE_ORDER
    assert [
        activity.id
        for stage in grade5_unit.stages
        for activity in grade5_unit.activities
        if activity.stage_id == stage.id
    ] == [activity.id for activity in grade5_unit.activities]

    objectives = {objective.id: objective for objective in grade5_unit.objectives}
    introductions = [
        activity
        for activity in grade5_unit.activities
        if activity.kind == "vocabulary_introduction"
    ]
    introduced = {
        objectives[activity.objective_ids[0]].vocabulary_ids[0]
        for activity in introductions
    }
    assert introduced == grade5_unit.vocabulary_ids()
    for activity in introductions:
        assert len(activity.objective_ids) == 1
        assert activity.required
        assert activity.completion_rule.model_repetitions == 2
        assert activity.completion_rule.response_opportunity_required
        assert activity.completion_rule.feedback_required

    for stage_id in TEACHING_STAGES:
        activities = [
            activity
            for activity in grade5_unit.activities
            if activity.stage_id == stage_id
        ]
        assert any(
            activity.kind == "ask_teacher" and activity.required
            for activity in activities
        )


def test_grade5_unit_warmup_and_lesson_three_contract(grade5_unit):
    warm_up = [
        activity
        for activity in grade5_unit.activities
        if activity.stage_id == "warm-up"
    ]
    assert {activity.kind for activity in warm_up} == {
        "greeting",
        "emotion_check",
        "bridge",
    }
    assert all(not activity.objective_ids for activity in warm_up)

    lesson_three = [
        activity
        for activity in grade5_unit.activities
        if activity.stage_id == "lesson-03"
    ]
    level_one_objectives = {
        objective.id
        for objective in grade5_unit.objectives
        if ".lesson01." in objective.id or ".lesson02." in objective.id
    }
    assert {
        objective_id
        for activity in lesson_three
        for objective_id in activity.objective_ids
    } == level_one_objectives
    assert not any(
        f"unit{grade5_unit.unit:02d}.lesson03." in objective.id
        for objective in grade5_unit.objectives
    )
    assert all(
        activity.kind != "vocabulary_introduction" for activity in lesson_three
    )


def test_grade5_unit_free_talk_and_policy_contract(grade5_unit):
    stage = next(stage for stage in grade5_unit.stages if stage.id == "free-talk")

    assert stage.role is not None
    assert stage.role.announce_start and stage.role.announce_end
    assert stage.review is not None
    assert stage.review.allow_unresolved_on_exit
    assert stage.review.max_items_per_turn == 1
    assert stage.review.rank_by == [
        "contextual_relevance",
        "importance",
        "required_support",
        "recency",
    ]
    assert stage.review.cancel_if_independently_demonstrated
    assert stage.prerequisite_stage_ids == [
        "lesson-01",
        "lesson-02",
        "lesson-03",
        "level-02",
        "level-03",
    ]
    assert grade5_unit.teaching_policy.max_attempts == 2


def test_grade5_unit_sources_are_traceable_and_stay_in_unit_rows(grade5_unit):
    collections = [
        grade5_unit.vocabulary,
        grade5_unit.patterns,
        grade5_unit.objectives,
        grade5_unit.activities,
        grade5_unit.stages,
    ]
    for items in collections:
        for item in items:
            assert (ROOT / item.source.file).is_file()
            assert item.source.section.strip()

    first_row = 2 + (grade5_unit.unit - 1) * 3
    unit_rows = set(range(first_row, first_row + 3))
    workbook_items = [
        *grade5_unit.vocabulary,
        *grade5_unit.patterns,
        *grade5_unit.objectives,
    ]
    for item in workbook_items:
        if item.source.file.endswith(".xlsx"):
            row = int(re.search(r"\d+$", item.source.section).group())
            assert row in unit_rows
