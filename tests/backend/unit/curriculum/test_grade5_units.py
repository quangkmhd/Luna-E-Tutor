import re
from pathlib import Path

import pytest
from luna_tutor.curriculum.loader import load_unit

ROOT = Path(__file__).resolve().parents[4]
IMPLEMENTED_UNIT_IDS = (1,)
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


@pytest.fixture(params=IMPLEMENTED_UNIT_IDS, ids=lambda number: f"unit-{number:02d}")
def grade5_unit(request):
    return load_unit(
        ROOT / f"curriculum/grade-05/unit-{request.param:02d}"
    )


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
    assert "Quang" in grade5_unit.teacher_prompt
    assert not grade5_unit.teaching_policy.recast_requires_repetition
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
