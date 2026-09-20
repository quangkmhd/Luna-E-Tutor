"""Pure turn planning boundary shared by web and Pipecat adapters."""

from luna_tutor.curriculum.models import Activity, Objective, UnitCurriculum
from luna_tutor.domain.decisions import (
    PlannedTurn, TeacherActivityContext, TeacherConstraints, TeacherTurnRequest,
)
from luna_tutor.domain.evidence import ActiveObjective, EvaluatorRequest, EvaluatorResult, TranscriptStatus, InputEvent
from luna_tutor.domain.privacy import redact_sensitive_contact
from luna_tutor.domain.state import ActivityProgress, LessonState, ReviewItem


from luna_tutor.teaching.descriptions import TeacherDescriptions


class TurnPlanner:
    def __init__(self, evaluator, engine, curriculum: UnitCurriculum):
        self._evaluator = evaluator
        self._engine = engine
        self._curriculum = curriculum
        self._descriptions = TeacherDescriptions()

    async def plan(self, state: LessonState, learner_text: str, turn_id: str,
                   *, transcript_status: TranscriptStatus = 'final',
                   input_event: InputEvent = 'transcript') -> PlannedTurn:
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
            transcript_status=transcript_status, input_event=input_event,
            learner_transcript=redacted.text,
            recent_context=list(state.recent_context),
            attempt_count=state.attempt_count,
        )
        if redacted.safety_event:
            evidence = EvaluatorResult.contact_removed(turn_id, state.state_version)
        else:
            evidence = await self._evaluator.evaluate(request)
        if evidence.turn_id != turn_id or evidence.state_version != state.state_version:
            raise ValueError('stale or uncorrelated evaluator result')
        decision = self._engine.decide(planning_state, evidence, self._curriculum, learner_text=redacted.text)
        target_activity = next((item for item in self._curriculum.activities
                                if item.id == decision.next_activity_id), activity)
        next_move = self._next_move_text(activity, decision, evidence)
        if activity.completion_rule.require_all_meanings and decision.progression_action == 'stay':
            progress = next((p for p in state.activity_progress if p.activity_id == activity.id), None)
            demonstrated = set(progress.demonstrated_meaning_ids if progress else ()) | {
                item.objective_id for item in evidence.objective_evidence
                if item.meaning_status == 'satisfied'}
            remaining = set(activity.completion_rule.meaning_objective_ids) - demonstrated
            if remaining and demonstrated and not evidence.needs_clarification:
                descriptions = [o.description for o in self._curriculum.objectives if o.id in remaining]
                next_move = self._descriptions.remaining(descriptions)
        teacher_request = TeacherTurnRequest(
            turn_id=turn_id,
            feedback_action=decision.feedback_action,
            corrected_form=decision.corrected_form,
            learner_meaning=redacted.text,
            next_teaching_move=next_move,
            emotional_support=decision.emotional_support,
            previous_teacher_turn=state.last_teacher_turn,
            recent_context=state.recent_context,
            review_objective=(self._active_objective(decision.next_objective_id)
                              if target_activity.kind == 'roleplay' and decision.next_objective_id else None),
            activity_context=self._teacher_context(target_activity, state, enforce_delivery=(
                target_activity.id != activity.id or decision.feedback_action not in {
                    'clarify', 'explain_meaning', 'privacy_redirect', 'reassure'})),
            constraints=TeacherConstraints(
                encouragement_required=(
                    decision.feedback_action == 'acknowledge_and_continue'
                    and target_activity.id != activity.id
                ),
                additional=self._descriptions.constraints,
            ),
        )
        proposed = self._apply(state, redacted.text, turn_id, decision, evidence)
        return PlannedTurn(
            turn_id=turn_id, state_version=state.state_version,
            learner_text=redacted.text, privacy_event=redacted.safety_event,
            evidence=evidence, decision=decision, teacher_request=teacher_request,
            proposed_next_state=proposed,
        )

    def _teacher_context(self, activity: Activity, state=None, *, enforce_delivery=True) -> TeacherActivityContext:
        stage = next(s for s in self._curriculum.stages if s.id == activity.stage_id)
        objectives = [item for item in self._curriculum.objectives
                      if item.id in activity.objective_ids and stage.review is None]
        word_ids = {word for item in objectives for word in item.vocabulary_ids}
        pattern_ids = {pattern for item in objectives for pattern in item.pattern_ids}
        delivered = next((p for p in state.activity_progress if p.activity_id == activity.id), None) if state else None
        remaining_models = max(0, activity.completion_rule.model_repetitions - (
            delivered.model_repetitions_delivered if delivered else 0)) if enforce_delivery else 0
        needs_invitation = (enforce_delivery and activity.completion_rule.response_opportunity_required
                            and not (delivered and delivered.response_opportunity_given))
        return TeacherActivityContext(
            stage_id=activity.stage_id, activity_id=activity.id, kind=activity.kind,
            role_name=stage.role.name if stage.role else None,
            role_country=stage.role.country if stage.role else None,
            objectives=tuple(item.description for item in objectives),
            target_words=tuple(item.text for item in self._curriculum.vocabulary
                               if item.id in word_ids),
            target_patterns=tuple(item.text for item in self._curriculum.patterns
                                  if item.id in pattern_ids),
            examples=(() if stage.review and state and state.stage_id == activity.stage_id
                      else tuple(activity.examples)),
            model_repetitions=activity.completion_rule.model_repetitions,
            remaining_model_repetitions=remaining_models, needs_response_invitation=needs_invitation,
            response_opportunity_required=activity.completion_rule.response_opportunity_required,
            delivery_only=activity.completion_rule.mode == 'delivered',
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
            target_words=[w.text for w in self._curriculum.vocabulary if w.id in objective.vocabulary_ids],
            acceptable_alternatives=alternatives,
            evidence_criteria=objective.evidence_criteria,
        )

    def _next_move_text(self, current: Activity, decision, evidence=None) -> str:
        if decision.feedback_action == 'privacy_redirect':
            return self._descriptions.branch('privacy_redirect')
        if decision.feedback_action == 'clarify':
            return self._descriptions.branch('clarify')
        if decision.feedback_action == 'explain_meaning':
            return self._descriptions.branch('explain_meaning')
        if decision.feedback_action == 'answer_teacher_question' and decision.next_activity_id:
            target = next(a for a in self._curriculum.activities
                          if a.id == decision.next_activity_id)
            return self._descriptions.branch('answer_teacher_question_then_move', target=target)
        if decision.feedback_action == 'answer_teacher_question':
            return self._descriptions.branch('answer_teacher_question')
        if evidence is not None and evidence.response_kind == 'no_response':
            if not decision.next_activity_id:
                return self._descriptions.branch('no_response_stay')
            target = next(a for a in self._curriculum.activities
                          if a.id == decision.next_activity_id)
            if target.completion_rule.mode == 'delivered':
                return self._descriptions.branch('no_response_move_to_delivery', target=target)
            return self._descriptions.branch('no_response_move_with_support', target=target)
        stage = next(s for s in self._curriculum.stages if s.id == current.stage_id)
        if stage.review is not None and not decision.next_activity_id:
            return self._descriptions.branch('free_talk')
        if (decision.feedback_action == 'offer_support'
                or decision.progression_action == 'reduce_difficulty'
                or decision.support_limit_exit
                or (decision.feedback_action == 'recast' and decision.progression_action == 'stay')):
            target = next((a for a in self._curriculum.activities
                           if a.id == decision.next_activity_id), current)
            if target.kind == 'ask_teacher':
                return self._descriptions.branch('support_ask_teacher')
            if target.kind == 'vocabulary_introduction' and target.id != current.id:
                return self._descriptions.branch('support_new_vocabulary', target=target)
            return self._descriptions.branch('offer_support')
        if decision.progression_action == 'finish':
            return self._descriptions.branch('finish')
        if decision.next_activity_id:
            target = next(a for a in self._curriculum.activities
                          if a.id == decision.next_activity_id)
            if target.kind == 'ask_teacher':
                return self._descriptions.branch('move_to_ask_teacher', target=target)
            return self._descriptions.branch('move_to_next_activity', target=target)
        return self._descriptions.branch('current_activity', current=current)

    def _apply(self, state: LessonState, learner_text: str, turn_id: str, decision, evidence) -> LessonState:
        objective_progress = {item.objective_id: item for item in state.objective_progress}
        objective_progress.update({item.objective_id: item for item in decision.mastery_updates})

        review = {item.objective_id: item for item in state.review_queue
                  if item.objective_id not in decision.review_queue_remove}
        for objective_id in decision.review_queue_add:
            if objective_id in review:
                review[objective_id] = review[objective_id].model_copy(update={'last_seen_turn_id': turn_id})
                continue
            review[objective_id] = ReviewItem(
                objective_id=objective_id,
                difficulty='target_form' if decision.corrected_form else 'word_recall',
                evidence_quote=None,
                learner_context=learner_text,
                last_seen_turn_id=turn_id,
            )

        progress = {item.activity_id: item for item in state.activity_progress}
        current = self._activity(state)
        old = progress.get(current.id, ActivityProgress(activity_id=current.id))
        leaving = decision.progression_action in {
            'move_to_next_objective', 'move_to_next_stage', 'finish'}
        reached_limit = leaving and decision.support_limit_exit
        is_review_stage = next(s for s in self._curriculum.stages if s.id == current.stage_id).review is not None
        progress[current.id] = old.model_copy(update={
            'status': ('support_limit_reached' if reached_limit else 'completed')
                      if leaving else 'in_progress',
            'attempt_count': 0 if is_review_stage else old.attempt_count + int(decision.count_attempt),
            'demonstrated_meaning_ids': tuple(sorted(set(old.demonstrated_meaning_ids) | {
                item.objective_id for item in evidence.objective_evidence
                if item.meaning_status == 'satisfied' and item.objective_id in current.objective_ids})),
            'no_response_count': old.no_response_count + int(evidence.response_kind == 'no_response'),
            'completion_reason': 'support limit reached' if reached_limit else old.completion_reason,
        })

        completed_stages = list(state.completed_stage_ids)
        if decision.progression_action in {'move_to_next_stage', 'finish'}:
            if state.stage_id not in completed_stages:
                completed_stages.append(state.stage_id)

        next_stage = decision.next_stage_id or state.stage_id
        next_activity = decision.next_activity_id or state.activity_id
        next_objective = decision.next_objective_id
        if decision.progression_action == 'stay' and next_objective is None and not is_review_stage:
            next_objective = state.objective_id
        next_status = 'completed' if decision.progression_action == 'finish' else state.status
        focus_changed = is_review_stage and (next_objective is None or next_objective != state.objective_id)
        next_attempt = 0 if leaving or focus_changed else state.attempt_count + int(decision.count_attempt)
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
