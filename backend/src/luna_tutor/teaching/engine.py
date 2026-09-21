"""Pure teaching policy: evidence describes a turn; this module decides a move.

Decisions are proposals. Their evidence records replace the corresponding
ObjectiveProgress records. The caller commits activity completion, counters,
and delivery-dependent effects together with the Teacher turn, never here.
"""

import re

from luna_tutor.curriculum.models import Activity, Stage, UnitCurriculum
from luna_tutor.domain.decisions import TeachingDecision
from luna_tutor.domain.evidence import EvaluatorResult, ObjectiveEvidence
from luna_tutor.domain.state import ActivityProgress, LessonState, ObjectiveProgress

_SUCCESSFUL_FORMS = {'correct_target_form', 'valid_alternative'}
_KNOWN_MEANING = {'satisfied', 'partially_satisfied'}
_SUPPORT_ORDER = {'independent': 0, 'context_hint': 1, 'choices': 2, 'sentence_starter': 3, 'model': 4}
# Function words must not make unrelated review topics look relevant.
_CONTEXT_STOP_WORDS = frozenset('a an the i my me you your we our it is are am in on at to of and or do does very'.split())


def _independent(state: LessonState) -> bool:
    support = state.support_given
    return not (support.model_spoken_recently or support.choices_given or support.sentence_starter_given)


def _english_success(item: ObjectiveEvidence, curriculum: UnitCurriculum) -> bool:
    if item.meaning_status != 'satisfied':
        return False
    objective = next(o for o in curriculum.objectives if o.id == item.objective_id)
    if objective.pattern_ids:
        return item.target_form_status in _SUCCESSFUL_FORMS
    if item.target_form_status not in _SUCCESSFUL_FORMS | {'not_used'}:
        return False
    # Vocabulary has no sentence-form target. Require the actual English word,
    # so a Vietnamese explanation alone is not counted as English word use.
    words = [w.text for w in curriculum.vocabulary if w.id in objective.vocabulary_ids]
    return bool(words) and all(re.search(r'(?<!\w)' + re.escape(word) + r'(?!\w)',
                                        item.evidence_quote or '', re.IGNORECASE) for word in words)


def _word_imitation(activity: Activity, evidence: EvaluatorResult,
                    curriculum: UnitCurriculum, learner_text: str) -> bool:
    """Recognize the requested word without claiming independent meaning/use."""
    if activity.kind != 'vocabulary_introduction' or evidence.response_kind != 'answer':
        return False
    objective_id = activity.objective_ids[0]
    item = next((item for item in evidence.objective_evidence
                 if item.objective_id == objective_id), None)
    if item and item.target_form_status == 'correct_target_form':
        return True
    objective = next(obj for obj in curriculum.objectives if obj.id == objective_id)
    words = [word.text for word in curriculum.vocabulary
             if word.id in objective.vocabulary_ids]
    normalize = lambda value: ' '.join(re.findall(r'[^\W_]+', value.casefold()))
    return len(words) == 1 and normalize(learner_text) == normalize(words[0])


def _progress(state: LessonState, activity: Activity) -> ActivityProgress:
    return next((item for item in state.activity_progress if item.activity_id == activity.id),
                ActivityProgress(activity_id=activity.id))


def _handled(progress: ActivityProgress, activity: Activity) -> bool:
    return (progress.status == 'completed'
            or (progress.status == 'support_limit_reached'
                and activity.max_attempts == 2
                and bool(progress.completion_reason)))


def _ready_for_response(progress: ActivityProgress, activity: Activity) -> bool:
    rule = activity.completion_rule
    return (progress.response_opportunity_given
            and progress.model_repetitions_delivered >= rule.model_repetitions)


def _record_evidence(state: LessonState, evidence: EvaluatorResult, curriculum: UnitCurriculum) -> tuple[list[ObjectiveProgress], list[str], list[str]]:
    previous = {item.objective_id: item for item in state.objective_progress}
    queued = {item.objective_id for item in state.review_queue}
    updates, add, remove = [], [], []
    independent = _independent(state)
    for item in evidence.objective_evidence:
        if item.meaning_status not in _KNOWN_MEANING:
            continue
        old = previous.get(item.objective_id, ObjectiveProgress(objective_id=item.objective_id))
        english_use = _english_success(item, curriculum)
        unresolved_form = item.target_form_status == 'error_in_target_form'
        if unresolved_form:
            add.append(item.objective_id)
        if english_use and independent and item.objective_id in queued:
            remove.append(item.objective_id)
        needs_review = old.needs_review or item.objective_id in queued or unresolved_form
        if english_use and independent:
            needs_review = False
        updates.append(ObjectiveProgress(
            objective_id=item.objective_id, introduced=old.introduced, attempted=True,
            supported_uses=old.supported_uses + int(english_use and not independent),
            independent_uses=old.independent_uses + int(english_use and independent),
            needs_review=needs_review,
        ))
    return updates, add, remove


def _next_move(state: LessonState, curriculum: UnitCurriculum, stage: Stage,
               activity: Activity) -> dict:
    """Complete this activity, then find the first unhandled required activity.

    Checking the entire stage (not just its suffix) prevents a sparse/restored
    snapshot from skipping a required activity. Success is never a mastery gate.
    """
    remaining = [item for item in curriculum.activities if item.stage_id == stage.id
                 and item.required and item.id != activity.id
                 and not _handled(_progress(state, item), item)]
    if remaining:
        target = remaining[0]
        return dict(progression_action='move_to_next_objective', next_activity_id=target.id,
                    next_objective_id=next(iter(target.objective_ids), None))
    stages = {item.id: item for item in curriculum.stages}
    completed = set(state.completed_stage_ids) | {stage.id}
    for exit_id in stage.exits:
        if exit_id == 'finish':
            return dict(progression_action='finish')
        target_stage = stages[exit_id]
        if not set(target_stage.prerequisite_stage_ids) <= completed:
            continue
        target = next(item for item in curriculum.activities
                      if item.stage_id == exit_id and item.required)
        return dict(progression_action='move_to_next_stage', next_stage_id=exit_id,
                    next_activity_id=target.id, next_objective_id=(None if target_stage.review else
                                                               next(iter(target.objective_ids), None)))
    return dict(progression_action='stay')


def _tokens(text: str) -> set[str]:
    return set(re.findall(r'[^\W_]+', text.casefold())) - _CONTEXT_STOP_WORDS


def _select_review(state: LessonState, evidence: EvaluatorResult, curriculum: UnitCurriculum,
                   stage: Stage, excluded: set[str], learner_text: str = '') -> str | None:
    """Rank only contextually connected items, using the available typed data.

    Context is the learner's current text (or evidence quotes for older callers),
    never the Teacher's last prompt. Topic relevance does not establish learning.
    Importance is required curriculum opportunity count; support prefers the
    lighter opportunity; recency prefers older applied turns. Curriculum order
    is a stable final tie break, independent of review queue insertion order.
    """
    if stage.review is None:
        return None
    context = (_tokens(learner_text) if learner_text else
               set().union(*(_tokens(item.evidence_quote or '') for item in evidence.objective_evidence)))
    if not context:
        return None
    objectives = {item.id: item for item in curriculum.objectives}
    vocabulary = {item.id: item.text for item in curriculum.vocabulary}
    positions = {item.id: index for index, item in enumerate(curriculum.objectives)}
    turn_positions = {turn_id: index for index, turn_id in enumerate(state.applied_turn_ids)}
    latest_turn = state.applied_turn_ids[-1] if state.applied_turn_ids else None
    candidates: list[tuple[tuple, str]] = []
    for item in state.review_queue:
        if item.objective_id in excluded:
            continue
        # A review immediately revisited after the last turn is a disguised retry.
        if item.last_seen_turn_id is not None and item.last_seen_turn_id == latest_turn:
            continue
        objective = objectives[item.objective_id]
        target_words = set().union(*(_tokens(vocabulary[vid]) for vid in objective.vocabulary_ids))
        topic = _tokens(item.learner_context) | _tokens(item.evidence_quote or '') | target_words
        relevance = len(context & topic)
        if relevance == 0:
            continue
        importance = sum(item.objective_id in activity.objective_ids
                         for activity in curriculum.activities if activity.required)
        scores = {
            'contextual_relevance': -relevance,
            'importance': -importance,
            'required_support': _SUPPORT_ORDER[item.support_level],
            'recency': turn_positions.get(item.last_seen_turn_id, -1),
        }
        key = tuple(scores[name] for name in stage.review.rank_by) + (positions[item.objective_id],)
        candidates.append((key, item.objective_id))
    return min(candidates)[1] if candidates else None


class TeachingEngine:
    """Deterministic decisions over validated curriculum and session snapshots."""

    def decide(self, state: LessonState, evidence: EvaluatorResult,
               curriculum: UnitCurriculum, *, learner_text: str = '') -> TeachingDecision:
        # Safety short-circuits every teaching branch, including positive evidence.
        if state.stop_requested:
            return TeachingDecision(feedback_action='stop', progression_action='save_and_stop')
        if state.privacy_event:
            return TeachingDecision(feedback_action='privacy_redirect', progression_action='stay')
        if state.status != 'active':
            return TeachingDecision(feedback_action='none', progression_action=(
                'finish' if state.status == 'completed' else 'save_and_stop'))
        stage, activity = self._validate_context(state, evidence, curriculum)
        if (evidence.needs_clarification or evidence.response_kind == 'insufficient_data'
                or any(item.meaning_status == 'uncertain' or item.target_form_status == 'uncertain'
                       for item in evidence.objective_evidence)):
            return TeachingDecision(feedback_action='clarify', progression_action='stay')

        progress = _progress(state, activity)
        emotion = bool(evidence.emotional_signals)
        if stage.id == 'warm-up':
            if evidence.response_kind == 'no_response':
                move = (_next_move(state, curriculum, stage, activity)
                        if progress.no_response_count >= 1 else dict(progression_action='stay'))
                return TeachingDecision(feedback_action='offer_support', **move)
            # Warm-up cannot manufacture curriculum evidence or practice targets.
            move = dict(progression_action='stay')
            if _handled(progress, activity) or (
                    activity.kind == 'emotion_check' and progress.response_opportunity_given):
                move = _next_move(state, curriculum, stage, activity)
            return TeachingDecision(feedback_action='reassure' if emotion else 'acknowledge_and_continue',
                                    emotional_support=emotion, **move)

        updates, add, remove = _record_evidence(state, evidence, curriculum)
        base = dict(mastery_updates=updates, review_queue_add=add, review_queue_remove=remove,
                    emotional_support=emotion)
        kind = evidence.response_kind
        # Questions retain evidence, but do not consume learner attempts.
        if kind in {'asks_meaning', 'asks_teacher'}:
            move = dict(progression_action='stay')
            if kind == 'asks_teacher' and activity.kind == 'ask_teacher' and (
                    _handled(progress, activity) or _ready_for_response(progress, activity)):
                move = _next_move(state, curriculum, stage, activity)
            return TeachingDecision(feedback_action=('explain_meaning' if kind == 'asks_meaning'
                                                    else 'answer_teacher_question'), **move, **base)

        targets = (set(activity.completion_rule.meaning_objective_ids or activity.objective_ids)
                   if stage.review is None else
                   {state.objective_id} if state.objective_id else set(activity.objective_ids))
        meaningful = any(item.objective_id in targets and item.meaning_status == 'satisfied'
                         for item in evidence.objective_evidence)
        word_imitation = _word_imitation(activity, evidence, curriculum, learner_text)
        recast = next((item for item in evidence.objective_evidence if item.recast_needed), None)
        feedback = ('recast' if recast else 'reassure' if emotion else
                    'redirect' if kind == 'off_topic' else
                    'acknowledge_and_continue' if meaningful or word_imitation else 'offer_support')
        base['feedback_action'] = feedback
        if recast:
            base['corrected_form'] = recast.corrected_form
        if emotion and not meaningful:
            return TeachingDecision(progression_action='reduce_difficulty', **base)
        if kind == 'off_topic':
            return TeachingDecision(progression_action='stay', **base)

        if stage.review is not None:
            return self._free_talk(state, evidence, curriculum, stage, activity, progress, base, learner_text)

        if _handled(progress, activity):
            return TeachingDecision(**_next_move(state, curriculum, stage, activity), **base)
        if not _ready_for_response(progress, activity):
            return TeachingDecision(progression_action='stay', **base)
        if activity.completion_rule.mode == 'delivered':
            return TeachingDecision(progression_action='stay', **base)

        attempts = max(state.attempt_count, progress.attempt_count)
        count = attempts < activity.max_attempts
        base['count_attempt'] = count
        # A question activity needs a question, even when an answer is fluent.
        demonstrated = set(progress.demonstrated_meaning_ids) | {
            item.objective_id for item in evidence.objective_evidence
            if item.meaning_status == 'satisfied'}
        complete_meaning = (targets <= demonstrated if activity.completion_rule.require_all_meanings
                            else meaningful)
        target_form_error = any(item.objective_id in targets and item.recast_needed
                                for item in evidence.objective_evidence)
        successful_activity = ((complete_meaning and meaningful or word_imitation)
                               and activity.kind != 'ask_teacher' and not target_form_error)
        if successful_activity:
            return TeachingDecision(**_next_move(state, curriculum, stage, activity), **base)
        if attempts + int(count) >= activity.max_attempts:
            add.extend(oid for oid in (sorted(targets if activity.kind == 'ask_teacher' else targets - demonstrated) if targets else [])
                       if oid not in add and oid not in remove)
            if activity.max_attempts == 2:
                move = _next_move(state, curriculum, stage, activity)
                return TeachingDecision(support_limit_exit=move['progression_action'] != 'stay',
                                        **move, **base)
            return TeachingDecision(progression_action='reduce_difficulty', **base)
        return TeachingDecision(progression_action='stay', **base)

    @staticmethod
    def _validate_context(state: LessonState, evidence: EvaluatorResult,
                          curriculum: UnitCurriculum) -> tuple[Stage, Activity]:
        if evidence.state_version != state.state_version or evidence.turn_id in state.applied_turn_ids:
            raise ValueError('Evidence is stale or already applied')
        if state.unit_id != curriculum.id:
            raise ValueError('State must belong to the supplied curriculum')
        objectives = {item.id for item in curriculum.objectives}
        referenced = {item.objective_id for item in evidence.objective_evidence}
        referenced.update(item.objective_id for item in state.review_queue)
        if state.objective_id:
            referenced.add(state.objective_id)
        if not referenced <= objectives:
            raise ValueError('Unknown objective in teaching context')
        stage = next((item for item in curriculum.stages if item.id == state.stage_id), None)
        if stage is None:
            raise ValueError('Unknown teaching stage')
        activities = [item for item in curriculum.activities if item.stage_id == stage.id]
        activity = next((item for item in activities if item.id == state.activity_id), None)
        if state.activity_id is None:
            activity = next((item for item in activities if item.required
                             and not _handled(_progress(state, item), item)), activities[-1])
        if activity is None:
            raise ValueError('Activity must belong to the current stage')
        if state.objective_id and state.objective_id not in activity.objective_ids:
            raise ValueError('Current objective must belong to the current activity')
        return stage, activity

    @staticmethod
    def _free_talk(state: LessonState, evidence: EvaluatorResult, curriculum: UnitCurriculum,
                   stage: Stage, activity: Activity, progress: ActivityProgress,
                   base: dict, learner_text: str = '') -> TeachingDecision:
        if _handled(progress, activity):
            return TeachingDecision(**_next_move(state, curriculum, stage, activity), **base)
        excluded = set(base['review_queue_remove']) | set(base['review_queue_add'])
        limit = activity.max_attempts
        attempts = state.attempt_count
        if base['feedback_action'] == 'offer_support' and not state.objective_id and evidence.response_kind == 'answer':
            base['feedback_action'] = 'acknowledge_and_continue'
        if state.objective_id:
            count = attempts < limit
            base['count_attempt'] = count
            successful = any(item.objective_id == state.objective_id and _english_success(item, curriculum)
                             for item in evidence.objective_evidence)
            if not successful and attempts + int(count) >= limit:
                if state.objective_id not in base['review_queue_add']:
                    base['review_queue_add'].append(state.objective_id)
                excluded.add(state.objective_id)
        # Never prompt the learner to repeat evidence they just supplied.
        excluded.update(item.objective_id for item in evidence.objective_evidence if _english_success(item, curriculum))
        selected = _select_review(state, evidence, curriculum, stage, excluded, learner_text)
        return TeachingDecision(progression_action='stay', next_objective_id=selected, **base)
