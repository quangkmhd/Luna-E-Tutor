from unittest.mock import AsyncMock

import pytest
from luna_tutor.curriculum.registry import UnknownUnitError
from luna_tutor.domain.state import LessonState
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
