from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError
from luna_tutor.curriculum.registry import UnknownUnitError
from luna_tutor.domain.state import LessonState
from luna_tutor.domain.decisions import TeacherTurnRequest
from luna_tutor.teaching.unit_router import UnitTurnRouter


@pytest.mark.asyncio
async def test_router_uses_persisted_unit_id():
    services = {
        "grade05.unit01": AsyncMock(),
        "grade05.unit03": AsyncMock(),
    }
    router = UnitTurnRouter(services)
    state = LessonState(
        session_id="s",
        unit_id="grade05.unit03",
        stage_id="warm-up",
        activity_id="warm-up.feelings",
    )

    await router.process(state, "Hello", "t1")

    services["grade05.unit03"].process.assert_awaited_once_with(
        state, "Hello", "t1"
    )
    services["grade05.unit01"].process.assert_not_awaited()


@pytest.mark.asyncio
async def test_router_rejects_unknown_stored_unit_without_fallback():
    fallback = AsyncMock()
    router = UnitTurnRouter({"grade05.unit01": fallback})
    state = LessonState(
        session_id="s",
        unit_id="grade05.unit99",
        stage_id="warm-up",
        activity_id="warm-up.feelings",
    )

    with pytest.raises(UnknownUnitError, match="grade05.unit99"):
        await router.process(state, "Hello", "t1")

    fallback.process.assert_not_awaited()


@pytest.mark.asyncio
async def test_router_respond_uses_request_unit_even_when_grade3_is_first():
    grade3 = AsyncMock()
    grade5 = AsyncMock()
    router = UnitTurnRouter({'grade03.unit01': grade3, 'grade05.unit01': grade5})
    request = TeacherTurnRequest(
        turn_id='t1', unit_id='grade05.unit01', feedback_action='acknowledge_and_continue',
        learner_meaning='Hello', next_teaching_move='Continue the greeting',
    )

    await router.respond(request)

    grade5.respond.assert_awaited_once_with(request)
    grade3.respond.assert_not_awaited()


def test_teacher_request_requires_explicit_unit_id():
    with pytest.raises(ValidationError, match='unit_id'):
        TeacherTurnRequest(
            turn_id='t1', feedback_action='acknowledge_and_continue',
            learner_meaning='Hello', next_teaching_move='Continue',
        )
