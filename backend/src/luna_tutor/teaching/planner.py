"""Pure turn planning boundary shared by web and Pipecat adapters."""

from luna_tutor.curriculum.models import Activity, Objective, UnitCurriculum
from luna_tutor.domain.decisions import PlannedTurn, TeacherConstraints, TeacherTurnRequest
from luna_tutor.domain.evidence import ActiveObjective, EvaluatorRequest
from luna_tutor.domain.privacy import redact_sensitive_contact
from luna_tutor.domain.state import ActivityProgress, LessonState, ReviewItem


class TurnPlanner:
    def __init__(self, evaluator, engine, curriculum: UnitCurriculum):
        self._evaluator = evaluator
        self._engine = engine
        self._curriculum = curriculum

    async def plan(self, state: LessonState, learner_text: str, turn_id: str) -> PlannedTurn:
        if turn_id in state.applied_turn_ids:
            raise ValueError('duplicate turn_id for this session state')
        redacted = redact_sensitive_contact(learner_text)
        planning_state = state.model_copy(update={'privacy_event': redacted.safety_event})
        activity = self._activity(planning_state)
        request = EvaluatorRequest(
            turn_id=turn_id,
            state_version=state.state_version,
            teacher_turn=state.last_teacher_turn,
            activity_type=activity.kind,
            active_objectives=[self._active_objective(objective_id)
                               for objective_id in activity.objective_ids],
            support_given=state.support_given,
            transcript_status='final',
            learner_transcript=redacted.text,
            recent_context=[],
            attempt_count=state.attempt_count,
        )
        evidence = await self._evaluator.evaluate(request)
        if evidence.turn_id != turn_id or evidence.state_version != state.state_version:
            raise ValueError('stale or uncorrelated evaluator result')
        decision = self._engine.decide(planning_state, evidence, self._curriculum)
        teacher_request = TeacherTurnRequest(
            turn_id=turn_id,
            feedback_action=decision.feedback_action,
            corrected_form=decision.corrected_form,
            learner_meaning=redacted.text,
            next_teaching_move=self._next_move_text(activity, decision),
            emotional_support=decision.emotional_support,
            constraints=TeacherConstraints(additional=(
                'Never require Quang to repeat a correction.',
                'Speak one short, natural turn without Markdown.',
            )),
        )
        proposed = self._apply(state, redacted.text, turn_id, decision)
        return PlannedTurn(
            turn_id=turn_id, state_version=state.state_version,
            learner_text=redacted.text, privacy_event=redacted.safety_event,
            evidence=evidence, decision=decision, teacher_request=teacher_request,
            proposed_next_state=proposed,
        )

    def _activity(self, state: LessonState) -> Activity:
        activities = [a for a in self._curriculum.activities if a.stage_id == state.stage_id]
        selected = next((a for a in activities if a.id == state.activity_id), None)
        if selected is None:
            selected = next((a for a in activities if a.required), None)
        if selected is None:
            raise ValueError('No active curriculum activity')
        return selected

    def _active_objective(self, objective_id: str) -> ActiveObjective:
        objective: Objective = next(o for o in self._curriculum.objectives if o.id == objective_id)
        patterns = {p.id: p for p in self._curriculum.patterns}
        target_patterns = [patterns[p].text for p in objective.pattern_ids]
        alternatives = [value for p in objective.pattern_ids
                        for value in patterns[p].acceptable_alternatives]
        return ActiveObjective(
            objective_id=objective.id,
            communicative_goal=objective.description,
            target_patterns=target_patterns,
            acceptable_alternatives=alternatives,
            evidence_criteria=objective.evidence_criteria,
        )

    def _next_move_text(self, current: Activity, decision) -> str:
        if decision.feedback_action == 'privacy_redirect':
            return 'Ask Quang to use a made-up phone number or words instead of real digits.'
        if decision.progression_action == 'finish':
            return 'Give one warm closing sentence.'
        if decision.next_activity_id:
            target = next(a for a in self._curriculum.activities
                          if a.id == decision.next_activity_id)
            return target.instruction
        return current.instruction

    def _apply(self, state: LessonState, learner_text: str, turn_id: str, decision) -> LessonState:
        objective_progress = {item.objective_id: item for item in state.objective_progress}
        objective_progress.update({item.objective_id: item for item in decision.mastery_updates})

        review = {item.objective_id: item for item in state.review_queue
                  if item.objective_id not in decision.review_queue_remove}
        for objective_id in decision.review_queue_add:
            review.setdefault(objective_id, ReviewItem(
                objective_id=objective_id,
                difficulty='target_form' if decision.corrected_form else 'word_recall',
                evidence_quote=None,
                learner_context=learner_text,
                last_seen_turn_id=turn_id,
            ))

        progress = {item.activity_id: item for item in state.activity_progress}
        current = self._activity(state)
        old = progress.get(current.id, ActivityProgress(activity_id=current.id))
        leaving = decision.progression_action in {
            'move_to_next_objective', 'move_to_next_stage', 'finish'}
        reached_limit = leaving and bool(decision.review_queue_add)
        progress[current.id] = old.model_copy(update={
            'status': ('support_limit_reached' if reached_limit else 'completed')
                      if leaving else 'in_progress',
            'attempt_count': old.attempt_count + int(decision.count_attempt),
            'completion_reason': 'support limit reached' if reached_limit else old.completion_reason,
        })

        completed_stages = list(state.completed_stage_ids)
        if decision.progression_action in {'move_to_next_stage', 'finish'}:
            if state.stage_id not in completed_stages:
                completed_stages.append(state.stage_id)

        next_stage = decision.next_stage_id or state.stage_id
        next_activity = decision.next_activity_id or state.activity_id
        next_objective = decision.next_objective_id
        if decision.progression_action == 'stay' and next_objective is None:
            next_objective = state.objective_id
        next_status = 'completed' if decision.progression_action == 'finish' else state.status
        next_attempt = 0 if leaving else state.attempt_count + int(decision.count_attempt)
        return state.model_copy(update={
            'state_version': state.state_version + 1,
            'stage_id': next_stage,
            'activity_id': next_activity,
            'objective_id': next_objective,
            'status': next_status,
            'attempt_count': next_attempt,
            'activity_progress': tuple(progress.values()),
            'objective_progress': tuple(objective_progress.values()),
            'review_queue': tuple(review.values()),
            'completed_stage_ids': tuple(completed_stages),
            'applied_turn_ids': (*state.applied_turn_ids, turn_id),
            'privacy_event': False,
        })
