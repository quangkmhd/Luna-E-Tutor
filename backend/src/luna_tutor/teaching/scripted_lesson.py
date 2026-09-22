"""Run one compact Grade 3 lesson without changing the Grade 5 engine."""

from dataclasses import dataclass
import re

from luna_tutor.curriculum.lesson_script import LessonScript
from luna_tutor.domain.decisions import (
    CompletedTurn, PlannedTurn, TeacherConstraints, TeacherTurnRequest,
    TeacherUtterance, TeachingDecision,
)
from luna_tutor.domain.evidence import (
    ActiveObjective, ContextTurn, EvaluatorRequest, EvaluatorResult,
    InputEvent, TranscriptStatus,
)
from luna_tutor.domain.privacy import redact_sensitive_contact
from luna_tutor.domain.state import LessonState, ObjectiveProgress
from luna_tutor.llm.teacher import InvalidTeacherResultError


@dataclass(frozen=True)
class Opportunity:
    order: int
    exchange: int
    stage: str
    lead_in: tuple[str, ...]
    say: str
    accept: str
    target: str | list[str] | None
    attempts: int

    def prompt(self, *, previous_success: bool = True, name: str | None = None) -> str:
        lead = [line for line in self.lead_in
                if previous_success or not line.startswith(('Excellent!', 'Wow!', 'Scene done!'))]
        return ' [long pause] '.join((*lead, self.say)).replace('{tên}', name or 'friend')

    @property
    def activity_id(self) -> str:
        return f'lesson-{self.order:02d}.exchange-{self.exchange:02d}'

    @property
    def objective_id(self) -> str:
        return f'lesson-{self.order:02d}.objective-{self.exchange:02d}'


def _opportunities(script: LessonScript) -> tuple[tuple[Opportunity, ...], tuple[str, ...]]:
    result = []
    pending = []
    for station in script.stations:
        for step in station.steps:
            for index, exchange in enumerate((step, *step.more), start=1):
                if exchange.accept is None:
                    pending.append(exchange.say)
                    continue
                result.append(Opportunity(
                    order=step.order, exchange=index, stage=station.id,
                    lead_in=tuple(pending), say=exchange.say,
                    accept=exchange.accept, target=step.target, attempts=step.attempts,
                ))
                pending.clear()
    return tuple(result), tuple(pending)


class ScriptedLessonService:
    def __init__(self, script: LessonScript, evaluator, teacher):
        self.script = script
        self._evaluator = evaluator
        self._teacher = teacher
        self._opportunities, self._closing_lines = _opportunities(script)
        if not self._opportunities:
            raise ValueError('Lesson has no learner opportunities')

    @property
    def opportunities(self) -> tuple[Opportunity, ...]:
        return self._opportunities

    def fresh_state(self, session_id: str) -> LessonState:
        first = self._opportunities[0]
        greeting = self.script.greeting.say
        opening = first.prompt()
        return LessonState(
            session_id=session_id, unit_id='grade03.unit01',
            lesson_id=self.script.lesson, script_index=0,
            stage_id=first.stage, activity_id=first.activity_id,
            objective_id=first.objective_id,
            opening_message=greeting, opening_script=opening,
            last_teacher_turn=opening,
        )

    async def plan(self, state: LessonState, learner_text: str, turn_id: str,
                   *, transcript_status: TranscriptStatus = 'final',
                   input_event: InputEvent = 'transcript') -> PlannedTurn:
        if (state.status != 'active' or state.lesson_id != self.script.lesson
                or turn_id in state.applied_turn_ids):
            raise ValueError('Invalid lesson state or duplicate turn')
        current = self._opportunities[state.script_index]
        redacted = redact_sensitive_contact(learner_text)
        selected = ([current.target] if isinstance(current.target, str) else current.target or [])
        target_words = [word for word in selected if word in self.script.words]
        target_patterns = [self.script.patterns[key] for key in selected
                           if key in self.script.patterns]
        objective = ActiveObjective(
            objective_id=current.objective_id,
            communicative_goal=f'Respond to lesson item {current.order}',
            target_words=target_words,
            target_patterns=target_patterns,
            evidence_criteria=current.accept,
        )
        request = EvaluatorRequest(
            turn_id=turn_id, unit_id=state.unit_id, state_version=state.state_version,
            teacher_turn=state.last_teacher_turn, activity_type='scripted_lesson',
            active_objectives=[objective], support_given=state.support_given,
            transcript_status=transcript_status, input_event=input_event,
            learner_transcript=redacted.text, recent_context=list(state.recent_context),
            attempt_count=state.attempt_count,
        )
        if redacted.safety_event:
            evidence = EvaluatorResult.contact_removed(turn_id, state.state_version)
        elif input_event == 'no_response':
            evidence = EvaluatorResult.observed_no_response(turn_id, state.state_version)
        else:
            evidence = await self._evaluator.evaluate(request)
        if evidence.turn_id != turn_id or evidence.state_version != state.state_version:
            raise ValueError('Uncorrelated evaluator result')
        accepted = (
            evidence.response_kind == 'answer' and not evidence.needs_clarification
            and any(item.objective_id == current.objective_id
                    and ((item.meaning_status == 'satisfied'
                          and item.target_form_status in {
                              'correct_target_form', 'valid_alternative', 'not_used'})
                         or (current.stage == 'vocabulary' and current.target is not None
                             and item.target_form_status in {
                             'correct_target_form', 'valid_alternative'}))
                    for item in evidence.objective_evidence)
        )
        non_attempt = evidence.response_kind in {'asks_meaning', 'asks_teacher', 'off_topic'}
        unreliable = redacted.safety_event or evidence.needs_clarification or non_attempt
        # Silence receives no scripted hint. A second unsuccessful spoken try moves on.
        advance = (not unreliable and
                   (accepted or input_event == 'no_response'
                    or state.attempt_count + 1 >= current.attempts))
        next_index = state.script_index + int(advance)
        finished = next_index >= len(self._opportunities)
        target = (self._opportunities[next_index] if advance and not finished else current)
        action = ('privacy_redirect' if redacted.safety_event else
                  'clarify' if evidence.needs_clarification else
                  'explain_meaning' if evidence.response_kind == 'asks_meaning' else
                  'answer_teacher_question' if evidence.response_kind == 'asks_teacher' else
                  'redirect' if evidence.response_kind == 'off_topic' else
                  'acknowledge_and_continue' if accepted else
                  'reassure' if input_event == 'no_response' else 'offer_support')
        decision = TeachingDecision(
            feedback_action=action,
            progression_action=('finish' if finished else
                                'move_to_next_stage' if advance and target.stage != current.stage else
                                'move_to_next_objective' if advance else 'stay'),
            next_stage_id=target.stage if advance and not finished and target.stage != current.stage else None,
            next_activity_id=target.activity_id if advance and not finished else None,
            next_objective_id=target.objective_id if advance and not finished else None,
            count_attempt=not accepted and not unreliable and input_event != 'no_response',
            support_limit_exit=advance and not accepted,
        )
        progress = list(state.objective_progress)
        if accepted and not any(item.objective_id == current.objective_id for item in progress):
            progress.append(ObjectiveProgress(
                objective_id=current.objective_id, introduced=True, attempted=True,
                supported_uses=1))
        name_match = re.search(r"\bI['’]?m\s+([^\W\d_]{1,20})\b", redacted.text, re.I)
        chosen_name = (name_match.group(1) if accepted and not state.script_name
                       and 'tên' in current.accept.casefold() and name_match
                       else state.script_name)
        proposed = state.model_copy(update={
            'state_version': state.state_version + 1,
            'script_index': next_index if not finished else state.script_index,
            'script_name': chosen_name,
            'stage_id': target.stage,
            'activity_id': target.activity_id,
            'objective_id': target.objective_id,
            'status': 'completed' if finished else 'active',
            'attempt_count': 0 if advance else state.attempt_count + int(not unreliable),
            'applied_turn_ids': (*state.applied_turn_ids, turn_id),
            'objective_progress': tuple(progress),
            'privacy_event': redacted.safety_event,
        })
        teacher_request = TeacherTurnRequest(
            turn_id=turn_id, unit_id=state.unit_id, lesson_id=state.lesson_id,
            feedback_action=action,
            learner_meaning=redacted.text,
            next_teaching_move=(
                'Give one brief, honest response to the learner. Do not introduce a new task or ask a question. '
                'The next scripted line will be appended exactly afterward.' if advance else
                'Protect private content and invite a safe reply.' if redacted.safety_event else
                'Ask for a clear repeat because the input was uncertain; do not call it wrong.'
                if evidence.needs_clarification else
                'Answer the learner question briefly, then invite the same scripted response.'
                if evidence.response_kind in {'asks_meaning', 'asks_teacher'} else
                'Gently return to the same scripted response.'
                if evidence.response_kind == 'off_topic' else
                'Give brief, gentle feedback and invite one retry of the same response. '
                'Do not provide a silence hint.'
            ),
            previous_teacher_turn=state.last_teacher_turn,
            recent_context=state.recent_context,
            constraints=TeacherConstraints(max_questions=0 if advance else 1),
        )
        return PlannedTurn(
            turn_id=turn_id, state_version=state.state_version,
            learner_text=redacted.text, privacy_event=redacted.safety_event,
            evidence=evidence, decision=decision,
            teacher_request=teacher_request, proposed_next_state=proposed,
        )

    async def respond(self, request: TeacherTurnRequest) -> TeacherUtterance:
        return await self._teacher.respond(request)

    def complete(self, state: LessonState, plan: PlannedTurn,
                 utterance: TeacherUtterance) -> CompletedTurn:
        if not isinstance(utterance, TeacherUtterance):
            utterance = TeacherUtterance.model_validate(utterance)
        if utterance.generation_mode == 'fallback':
            raise InvalidTeacherResultError(
                status_code=200, request_id=plan.turn_id,
                reason='Teacher response could not be validated')
        advanced = plan.proposed_next_state.script_index != state.script_index
        if advanced and plan.proposed_next_state.status == 'active':
            next_say = self._opportunities[plan.proposed_next_state.script_index].prompt(
                previous_success=plan.decision.feedback_action == 'acknowledge_and_continue',
                name=plan.proposed_next_state.script_name)
            utterance = utterance.model_copy(update={
                'spoken_text': utterance.spoken_text + ' [long pause] ' + next_say,
            })
        elif plan.proposed_next_state.status == 'completed' and self._closing_lines:
            closing = [line for line in self._closing_lines
                       if plan.decision.feedback_action == 'acknowledge_and_continue'
                       or not line.startswith(('Excellent!', 'Wow!', 'Scene done!'))]
            if closing:
                utterance = utterance.model_copy(update={
                    'spoken_text': utterance.spoken_text + ' [long pause] '
                    + ' [long pause] '.join(closing).replace(
                        '{tên}', plan.proposed_next_state.script_name or 'friend'),
                })
        next_state = plan.proposed_next_state.model_copy(update={
            'last_teacher_turn': utterance.spoken_text,
            'recent_context': (*state.recent_context,
                               ContextTurn(role='learner', text=plan.learner_text[:2000]),
                               ContextTurn(role='teacher', text=utterance.spoken_text[:2000]))[-6:],
        })
        # The proposal and stored state must share every field except the delivered text.
        plan = plan.model_copy(update={'proposed_next_state': next_state.model_copy(update={
            'last_teacher_turn': plan.proposed_next_state.last_teacher_turn,
        })})
        return CompletedTurn(plan=plan, teacher_utterance=utterance, next_state=next_state)

    async def process(self, state: LessonState, learner_text: str, turn_id: str,
                      **kwargs) -> CompletedTurn:
        plan = await self.plan(state, learner_text, turn_id, **kwargs)
        utterance = await self.respond(plan.teacher_request)
        return self.complete(state, plan, utterance)
