import pytest
from pathlib import Path
from luna_tutor.api.runtime import FixtureTurnService
from luna_tutor.evals.loader import load_scenarios

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.asyncio
async def test_behavior_runner_checks_actual_actions_and_state_not_gold():
    from luna_tutor.evals.behavior import BehaviorRunner
    scenario = next(s for s in load_scenarios(ROOT / 'evals/unit-01') if s.id == 'warmup-01')
    turn = scenario.turns[0].model_copy(update={
        'allowed_feedback_actions': ['recast'],
        'expected_state_effects': {'count_attempt': True},
    })
    scenario = scenario.model_copy(update={'turns': [turn]})
    records = await BehaviorRunner(ROOT, FixtureTurnService()).run([scenario])
    assert 'feedback_action' in records[0]['failures']
    assert 'state:count_attempt' in records[0]['failures']
    assert records[0]['completed_turn']['teacher_utterance']['spoken_text']
    assert records[0]['semantic_review_status'] == 'pending'


@pytest.mark.asyncio
async def test_behavior_runner_rejects_unimplemented_state_assertion():
    from luna_tutor.evals.behavior import BehaviorRunner
    scenario = next(s for s in load_scenarios(ROOT / 'evals/unit-01') if s.id == 'warmup-01')
    scenario = scenario.model_copy(update={'turns': [scenario.turns[0].model_copy(update={
        'expected_state_effects': {'invented_check': True}})]})
    with pytest.raises(ValueError, match='Unsupported state assertion'):
        await BehaviorRunner(ROOT, FixtureTurnService()).run([scenario])


@pytest.mark.asyncio
async def test_multiple_turns_use_actual_prior_output_and_state():
    from luna_tutor.evals.behavior import BehaviorRunner
    scenario = next(s for s in load_scenarios(ROOT / 'evals/unit-01') if s.id == 'warmup-01')
    turn = scenario.turns[0]
    scenario = scenario.model_copy(update={'turns': [turn, turn.model_copy(update={
        'teacher_turn': 'This invented question must not replace actual history.',
        'learner_text': 'Hello again.'})]})
    records = await BehaviorRunner(ROOT, FixtureTurnService()).run([scenario])
    assert len(records) == 2
    assert records[1]['initial_state']['state_version'] == 1
    assert records[1]['initial_state']['last_teacher_turn'] == (
        records[0]['completed_turn']['teacher_utterance']['spoken_text'])


@pytest.mark.asyncio
async def test_failed_turn_does_not_fabricate_state_for_following_turn():
    from luna_tutor.evals.behavior import BehaviorRunner
    scenario = next(s for s in load_scenarios(ROOT / 'evals/unit-01') if s.id == 'warmup-01')
    turn = scenario.turns[0]
    scenario = scenario.model_copy(update={'turns': [turn.model_copy(update={
        'learner_text': 'fixture: provider failure'}), turn]})
    records = await BehaviorRunner(ROOT, FixtureTurnService()).run([scenario])
    assert len(records) == 1
    assert records[0]['failures'] == ['turn_execution']
    assert records[0]['error']['type'] == 'ProviderError'
    assert 'completed_turn' not in records[0]


@pytest.mark.asyncio
async def test_runner_rejects_new_activity_without_response_opportunity():
    from luna_tutor.evals.behavior import BehaviorRunner
    from luna_tutor.domain.evidence import EvaluatorResult
    from luna_tutor.domain.decisions import TeacherUtterance
    from luna_tutor.teaching.engine import TeachingEngine
    from luna_tutor.teaching.planner import TurnPlanner
    from luna_tutor.teaching.turn_service import TurnService
    from luna_tutor.curriculum.loader import load_unit
    class Evaluator:
        async def evaluate(self, request):
            return EvaluatorResult(turn_id=request.turn_id,state_version=request.state_version,
                response_kind='asks_teacher',emotional_signals=[],objective_evidence=[],
                needs_clarification=False,ambiguity_reason=None)
    class BadTeacher:
        async def respond(self, request):
            return TeacherUtterance(spoken_text='My hobby is reading. Cottage. Cottage.',delivery_intent='warm')
    unit=load_unit(ROOT/'curriculum/grade-05/unit-01')
    service=TurnService(TurnPlanner(Evaluator(),TeachingEngine(),unit),BadTeacher())
    scenario=next(s for s in load_scenarios(ROOT/'evals/unit-01') if s.id=='regression-ask-hobby')
    records=await BehaviorRunner(ROOT,service).run([scenario])
    assert 'missing_response_opportunity' in records[0]['failures']
