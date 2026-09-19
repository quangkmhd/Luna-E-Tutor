"""Atomic in-memory orchestration; persistence is an outer adapter."""

from luna_tutor.domain.decisions import CompletedTurn, TeacherUtterance
from luna_tutor.llm.teacher import InvalidTeacherResultError
from luna_tutor.domain.evidence import TranscriptStatus, InputEvent
from luna_tutor.teaching.text_delivery import confirm_text_delivery


class TurnService:
    def __init__(self, planner, teacher):
        self._planner = planner
        self._teacher = teacher

    async def process(self, state, learner_text: str, turn_id: str,
                      *, transcript_status: TranscriptStatus = 'final',
                      input_event: InputEvent = 'transcript') -> CompletedTurn:
        metadata = {'transcript_status': transcript_status} if transcript_status != 'final' else {}
        if input_event != 'transcript':
            metadata['input_event'] = input_event
        plan = await self._planner.plan(state, learner_text, turn_id, **metadata)
        utterance = await self._teacher.respond(plan.teacher_request)
        if not isinstance(utterance, TeacherUtterance):
            utterance = TeacherUtterance.model_validate(utterance)
        if utterance.generation_mode == 'fallback':
            raise InvalidTeacherResultError(status_code=200, request_id=turn_id,
                                            reason='Teacher response could not be validated')
        plan = confirm_text_delivery(plan, utterance, state.activity_id)
        next_state = plan.proposed_next_state.model_copy(update={
            'last_teacher_turn': utterance.spoken_text,
        })
        return CompletedTurn(plan=plan, teacher_utterance=utterance, next_state=next_state)
