import asyncio

from luna_tutor.domain.decisions import (
    CompletedTurn,
    PlannedTurn,
    TeacherTurnRequest,
    TeacherUtterance,
    TeachingDecision,
)
from luna_tutor.domain.evidence import EvaluatorResult


def make_completed(state, learner_text: str, turn_id: str) -> CompletedTurn:
    evidence = EvaluatorResult(
        turn_id=turn_id, state_version=state.state_version,
        response_kind='answer', emotional_signals=[], objective_evidence=[],
        needs_clarification=False, ambiguity_reason=None)
    decision = TeachingDecision(
        feedback_action='acknowledge_and_continue', progression_action='stay')
    request = TeacherTurnRequest(
        turn_id=turn_id, unit_id=state.unit_id, feedback_action='acknowledge_and_continue',
        learner_meaning=learner_text, next_teaching_move='Ask one short follow-up.')
    proposed = state.model_copy(update={
        'state_version': state.state_version + 1,
        'applied_turn_ids': (*state.applied_turn_ids, turn_id),
    })
    utterance = TeacherUtterance(
        spoken_text='Thank you, Quang. Tell me a little more?',
        delivery_intent='encouraging')
    return CompletedTurn(
        plan=PlannedTurn(
            turn_id=turn_id, state_version=state.state_version,
            learner_text=learner_text, privacy_event=False, evidence=evidence,
            decision=decision, teacher_request=request,
            proposed_next_state=proposed),
        teacher_utterance=utterance,
        next_state=proposed.model_copy(update={'last_teacher_turn': utterance.spoken_text}),
    )


class FakeTurnService:
    def __init__(self, error=None, delay=0):
        self.error = error
        self.delay = delay
        self.calls = []

    async def process(self, state, learner_text, turn_id):
        self.calls.append(turn_id)
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        return make_completed(state, learner_text, turn_id)
