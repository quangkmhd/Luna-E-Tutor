from pathlib import Path

import pytest
from luna_tutor.curriculum.loader import load_unit
from luna_tutor.domain.evidence import EvaluatorResult, ObjectiveEvidence
from luna_tutor.domain.state import ActivityProgress, LessonState
from luna_tutor.teaching.engine import TeachingEngine
from luna_tutor.teaching.planner import TurnPlanner

ROOT = Path(__file__).resolve().parents[4]


class UnexpectedEvaluator:
    async def evaluate(self, request):
        raise AssertionError("private address must not reach the evaluator")


@pytest.fixture
def unit_02():
    return load_unit(ROOT / "curriculum/grade-05/unit-02")


@pytest.mark.asyncio
async def test_private_address_is_removed_before_evaluation_and_state_storage(unit_02):
    activity_id = "lesson-02.fictional-address"
    state = LessonState(
        session_id="unit-02-address",
        unit_id=unit_02.id,
        stage_id="lesson-02",
        activity_id=activity_id,
        objective_id="unit02.lesson02.pattern.address",
        attempt_count=1,
        activity_progress=(
            ActivityProgress(
                activity_id=activity_id,
                status="in_progress",
                response_opportunity_given=True,
            ),
        ),
    )
    private_address = "I live at 19 River Lane."

    plan = await TurnPlanner(
        UnexpectedEvaluator(), TeachingEngine(), unit_02
    ).plan(state, private_address, "private-address")

    assert plan.learner_text == "[REDACTED_ADDRESS]"
    assert plan.privacy_event
    assert plan.decision.feedback_action == "privacy_redirect"
    assert not plan.decision.count_attempt
    assert plan.proposed_next_state.attempt_count == state.attempt_count
    assert private_address not in repr(plan)
    assert all(
        private_address not in repr(item)
        for item in plan.proposed_next_state.recent_context
    )
    assert all(
        item.evidence_quote != private_address
        for item in plan.evidence.objective_evidence
    )


def test_unit02_privacy_result_has_no_objective_evidence():
    result = EvaluatorResult.contact_removed("turn", 0)
    assert result.objective_evidence == []


def _result(objective_id, *, meaning, form, quote, kind="answer"):
    evidence = []
    if quote is not None:
        evidence.append(
            ObjectiveEvidence(
                objective_id=objective_id,
                meaning_status=meaning,
                target_form_status=form,
                evidence_quote=quote,
                recast_needed=False,
                corrected_form=None,
            )
        )
    return EvaluatorResult(
        turn_id="turn",
        state_version=0,
        response_kind=kind,
        emotional_signals=[],
        objective_evidence=evidence,
        needs_clarification=False,
        ambiguity_reason=None,
    )


def _introduction_state(unit_02, *, attempts=0):
    activity_id = "lesson-01.introduce-building"
    return LessonState(
        session_id="unit-02-building",
        unit_id=unit_02.id,
        stage_id="lesson-01",
        activity_id=activity_id,
        objective_id="unit02.lesson01.vocabulary.building",
        completed_stage_ids=("warm-up",),
        attempt_count=attempts,
        activity_progress=(
            ActivityProgress(
                activity_id=activity_id,
                status="in_progress",
                model_repetitions_delivered=2,
                response_opportunity_given=True,
            ),
        ),
    )


def test_unit02_correct_answer_advances(unit_02):
    objective_id = "unit02.lesson01.vocabulary.building"
    decision = TeachingEngine().decide(
        _introduction_state(unit_02),
        _result(
            objective_id,
            meaning="satisfied",
            form="correct_target_form",
            quote="building",
        ),
        unit_02,
    )
    assert decision.progression_action == "move_to_next_objective"
    assert decision.next_activity_id == "lesson-01.introduce-flat"


def test_unit02_first_failure_stays_with_support(unit_02):
    decision = TeachingEngine().decide(
        _introduction_state(unit_02),
        _result(
            "unit02.lesson01.vocabulary.building",
            meaning="not_demonstrated",
            form="not_used",
            quote=None,
            kind="does_not_know",
        ),
        unit_02,
    )
    assert decision.progression_action == "stay"
    assert decision.feedback_action == "offer_support"
    assert decision.count_attempt


def test_unit02_second_failure_advances_and_queues_review(unit_02):
    objective_id = "unit02.lesson01.vocabulary.building"
    decision = TeachingEngine().decide(
        _introduction_state(unit_02, attempts=1),
        _result(
            objective_id,
            meaning="not_demonstrated",
            form="not_used",
            quote=None,
            kind="does_not_know",
        ),
        unit_02,
    )
    assert decision.progression_action == "move_to_next_objective"
    assert decision.support_limit_exit
    assert objective_id in decision.review_queue_add


def test_unit02_vietnamese_can_satisfy_meaning_without_target_form(unit_02):
    objective_id = "unit02.lesson01.pattern.home_type"
    completed = tuple(
        ActivityProgress(activity_id=activity.id, status="completed")
        for activity in unit_02.activities
        if activity.stage_id == "lesson-01"
        and activity.id != "lesson-01.home-type"
        and activity.kind == "vocabulary_introduction"
    )
    state = LessonState(
        session_id="unit-02-vietnamese",
        unit_id=unit_02.id,
        stage_id="lesson-01",
        activity_id="lesson-01.home-type",
        objective_id=objective_id,
        completed_stage_ids=("warm-up",),
        activity_progress=(
            *completed,
            ActivityProgress(
                activity_id="lesson-01.home-type",
                status="in_progress",
                response_opportunity_given=True,
            ),
        ),
    )
    decision = TeachingEngine().decide(
        state,
        _result(
            objective_id,
            meaning="satisfied",
            form="not_used",
            quote="Nhân vật sống trong ngôi nhà.",
        ),
        unit_02,
    )
    update = next(
        item for item in decision.mastery_updates
        if item.objective_id == objective_id
    )
    assert update.attempted
    assert update.independent_uses == 0
    assert decision.progression_action == "move_to_next_objective"
