import pytest
from luna_tutor.domain.state import ActivityProgress, LessonState
from luna_tutor.llm.evaluator import GeminiEvaluator
from luna_tutor.teaching.planner import TurnPlanner


class NoCalls:
    async def structured_chat(self, *args):
        pytest.fail('An observed no-response event has no learner speech to evaluate')


@pytest.mark.asyncio
async def test_first_observed_silence_offers_choice_without_advancing_warmup(engine, unit_01):
    state = LessonState(session_id='silent', unit_id=unit_01.id, stage_id='warm-up',
        activity_id='warm-up.feelings', last_teacher_turn='How are you today?',
        activity_progress=(ActivityProgress(activity_id='warm-up.feelings',
            response_opportunity_given=True, status='in_progress'),))
    plan = await TurnPlanner(GeminiEvaluator(NoCalls()), engine, unit_01).plan(
        state, '', 'silence-1', input_event='no_response')
    assert plan.evidence.response_kind == 'no_response'
    assert not plan.evidence.needs_clarification
    assert plan.decision.feedback_action == 'offer_support'
    assert plan.decision.progression_action == 'stay'
    assert not plan.decision.count_attempt
    assert 'choice' in plan.teacher_request.next_teaching_move


@pytest.mark.asyncio
async def test_two_observed_silences_allow_support_exit_and_queue_review(engine, unit_01, state):
    planner = TurnPlanner(GeminiEvaluator(NoCalls()), engine, unit_01)
    first = await planner.plan(state, '', 'silence-1', input_event='no_response')
    assert first.decision.count_attempt
    assert first.decision.progression_action == 'stay'
    second = await planner.plan(first.proposed_next_state, '', 'silence-2', input_event='no_response')
    assert second.decision.count_attempt
    assert second.decision.progression_action == 'move_to_next_objective'
    assert state.objective_id == second.proposed_next_state.review_queue[0].objective_id
    assert 'easier' in second.teacher_request.next_teaching_move


@pytest.mark.asyncio
async def test_second_warmup_silence_moves_on_without_academic_attempts(engine, unit_01):
    state = LessonState(session_id='silent', unit_id=unit_01.id, stage_id='warm-up',
        activity_id='warm-up.feelings', last_teacher_turn='How are you today?',
        activity_progress=(ActivityProgress(activity_id='warm-up.hello', status='completed'),
                           ActivityProgress(activity_id='warm-up.feelings',
                               response_opportunity_given=True, status='in_progress')))
    planner = TurnPlanner(GeminiEvaluator(NoCalls()), engine, unit_01)
    first = await planner.plan(state, '', 'silent-1', input_event='no_response')
    second = await planner.plan(first.proposed_next_state, '', 'silent-2', input_event='no_response')
    assert second.decision.next_activity_id == 'lesson-01.introduce-city'
    assert not second.decision.count_attempt
    assert second.proposed_next_state.objective_progress == ()
    assert second.proposed_next_state.review_queue == ()


@pytest.mark.asyncio
async def test_no_response_cannot_hide_uncertain_input(engine, unit_01, state):
    with pytest.raises(ValueError, match='cannot represent an input failure'):
        await TurnPlanner(GeminiEvaluator(NoCalls()), engine, unit_01).plan(
            state, '', 'invalid', input_event='no_response', transcript_status='uncertain')
