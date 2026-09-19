import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "voice/server"))
from luna_tutor.curriculum.loader import load_unit
from luna_tutor.domain.decisions import TeacherUtterance
from luna_tutor.domain.evidence import EvaluatorResult, ObjectiveEvidence
from luna_tutor.domain.state import ActivityProgress, LessonState
from luna_tutor.teaching.engine import TeachingEngine
from luna_tutor.teaching.planner import TurnPlanner
from luna_tutor.teaching.turn_service import TurnService

ROOT = Path(__file__).resolve().parents[2]


def make_service(fail=False):
    unit = load_unit(ROOT / "curriculum/grade-05/unit-01")

    class Evaluator:
        async def evaluate(self, request):
            return EvaluatorResult(
                turn_id=request.turn_id,
                state_version=request.state_version,
                response_kind="answer",
                emotional_signals=[],
                needs_clarification=False,
                ambiguity_reason=None,
                objective_evidence=[
                    ObjectiveEvidence(
                        objective_id="unit01.lesson01.pattern.live_in",
                        meaning_status="satisfied",
                        target_form_status="correct_target_form",
                        evidence_quote=request.learner_transcript,
                        recast_needed=False,
                        corrected_form=None,
                    )
                ],
            )

    class Teacher:
        def __init__(self):
            self.requests = []

        async def respond(self, request):
            self.requests.append(request)
            if fail:
                raise TimeoutError("teacher unavailable")
            return TeacherUtterance(
                spoken_text="Now ask me where I live.", delivery_intent="warm"
            )

    teacher = Teacher()
    state = LessonState(
        session_id="flow-test",
        unit_id=unit.id,
        stage_id="lesson-01",
        activity_id="lesson-01.home",
        objective_id="unit01.lesson01.pattern.live_in",
        completed_stage_ids=("warm-up",),
        activity_progress=tuple(
            ActivityProgress(
                activity_id=a.id,
                status="completed" if a.id != "lesson-01.home" else "in_progress",
                response_opportunity_given=True,
            )
            for a in unit.activities
            if a.stage_id == "lesson-01" and a.id != "lesson-01.ask-luna"
        ),
    )
    return (
        TurnService(TurnPlanner(Evaluator(), TeachingEngine(), unit), teacher),
        teacher,
        state,
    )


@pytest.mark.asyncio
async def test_native_flow_restores_activity_and_routes_bounded_teacher_context(
    monkeypatch,
):
    from pipecat.flows import FlowManager
    from text_pipeline import PipecatTurnService

    nodes = []
    original = FlowManager.set_node_from_config

    async def record(self, node):
        await original(self, node)
        nodes.append(self.current_node)

    monkeypatch.setattr(FlowManager, "set_node_from_config", record)
    service, teacher, state = make_service()
    turn = await PipecatTurnService(service).process(
        state, "I live in the city. {{untrusted}}", "flow-1"
    )
    assert nodes == ["lesson-01.home", "lesson-01.ask-luna"]
    assert len(teacher.requests) == 1
    assert teacher.requests[0] == turn.plan.teacher_request
    assert "{{untrusted}}" in teacher.requests[0].learner_meaning
    assert turn.next_state.activity_id == "lesson-01.ask-luna"
    assert state.state_version == 0


@pytest.mark.asyncio
async def test_native_flow_teacher_failure_cannot_complete_turn():
    from text_pipeline import PipecatTurnService

    service, teacher, state = make_service(fail=True)
    with pytest.raises(TimeoutError):
        await PipecatTurnService(service).process(
            state, "I live in the city.", "flow-error"
        )
    assert len(teacher.requests) == 1
    assert not state.applied_turn_ids


@pytest.mark.asyncio
async def test_typed_flow_never_initializes_default_audio_turn_models(monkeypatch):
    import pipecat.turns.user_turn_strategies as strategies
    from text_pipeline import PipecatTurnService

    def forbidden():
        pytest.fail("Typed turns must not initialize default audio turn strategies")

    monkeypatch.setattr(strategies, "default_user_turn_start_strategies", forbidden)
    monkeypatch.setattr(strategies, "default_user_turn_stop_strategies", forbidden)
    service, _, state = make_service()
    await PipecatTurnService(service).process(state, "I live in the city.", "text-only")


@pytest.mark.asyncio
async def test_native_flow_transition_failure_does_not_call_teacher(monkeypatch):
    from pipecat.flows import FlowManager
    from text_pipeline import PipecatTurnService

    original = FlowManager.set_node_from_config

    async def fail(self, node):
        if node["respond_immediately"]:
            raise ValueError("transition failed")
        await original(self, node)

    monkeypatch.setattr(FlowManager, "set_node_from_config", fail)
    service, teacher, state = make_service()
    with pytest.raises(ValueError, match="transition failed"):
        await PipecatTurnService(service).process(
            state, "I live in the city.", "bad-transition"
        )
    assert teacher.requests == []
    assert state.state_version == 0


@pytest.mark.asyncio
async def test_native_flows_keep_parallel_sessions_separate():
    import asyncio

    from text_pipeline import PipecatTurnService

    service, teacher, state = make_service()
    adapter = PipecatTurnService(service)
    a, b = await asyncio.gather(
        adapter.process(state, "I live in the city.", "parallel-a"),
        adapter.process(
            state.model_copy(update={"session_id": "other"}),
            "I live in the countryside.",
            "parallel-b",
        ),
    )
    assert a.next_state.session_id == "flow-test"
    assert b.next_state.session_id == "other"
    assert a.plan.learner_text != b.plan.learner_text
    assert len(teacher.requests) == 2
