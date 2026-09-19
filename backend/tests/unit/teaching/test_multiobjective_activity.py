from luna_tutor.domain.state import LessonState, ActivityProgress
from luna_tutor.domain.evidence import EvaluatorResult, ObjectiveEvidence
from luna_tutor.teaching.planner import TurnPlanner

CLASS='unit01.lesson01.pattern.class'
HOME='unit01.lesson01.pattern.live_in'

def review_state(unit):
    return LessonState(session_id='review',unit_id=unit.id,stage_id='lesson-03',
        activity_id='lesson-03.introductions',objective_id='unit01.lesson01.vocabulary.city',
        activity_progress=(ActivityProgress(activity_id='lesson-03.introductions',
            status='in_progress',response_opportunity_given=True),))

def evidence(ids, turn='one', version=0, quote='Learner answer'):
    return EvaluatorResult(turn_id=turn,state_version=version,response_kind='answer',emotional_signals=[],
        objective_evidence=[ObjectiveEvidence(objective_id=i,meaning_status='satisfied',
            target_form_status='correct_target_form', evidence_quote=quote,
            recast_needed=False,corrected_form=None) for i in ids],
        needs_clarification=False,ambiguity_reason=None)

def test_class_and_countryside_complete_review_without_city_word(engine,unit_01):
    decision=engine.decide(review_state(unit_01),evidence([CLASS,HOME]),unit_01)
    assert decision.next_activity_id=='lesson-03.favourites'
    assert decision.feedback_action=='acknowledge_and_continue'
    assert not decision.review_queue_add

def test_class_only_does_not_complete_combined_review(engine,unit_01):
    decision=engine.decide(review_state(unit_01),evidence([CLASS]),unit_01)
    assert decision.progression_action=='stay'
    assert decision.feedback_action=='acknowledge_and_continue'

import pytest
@pytest.mark.asyncio
async def test_two_answers_accumulate_only_within_current_activity(engine,unit_01):
    class Evaluator:
        async def evaluate(self,request):
            return evidence([CLASS] if request.turn_id=='one' else [HOME],request.turn_id,request.state_version,request.learner_transcript)
    planner=TurnPlanner(Evaluator(),engine,unit_01)
    first=await planner.plan(review_state(unit_01),"I'm in Class 5B.",'one')
    assert first.decision.progression_action=='stay'
    second=await planner.plan(first.proposed_next_state,'I live in the countryside.','two')
    assert second.decision.next_activity_id=='lesson-03.favourites'
    assert not second.decision.review_queue_add


def test_support_limit_queues_only_missing_review_meaning(engine,unit_01):
    state=review_state(unit_01)
    progress=state.activity_progress[0].model_copy(update={
        'attempt_count':1, 'demonstrated_meaning_ids':(CLASS,)})
    state=state.model_copy(update={'attempt_count':1, 'activity_progress':(progress,)})
    decision=engine.decide(state,evidence([CLASS]),unit_01)
    assert decision.review_queue_add==[HOME]
