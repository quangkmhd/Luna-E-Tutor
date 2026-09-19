"""Record observable text delivery, separately from learner evidence.

This adapter is for completed text responses stored for the web client. Voice
must confirm playback instead; a generated string is not proof of spoken audio.
"""
import re

from luna_tutor.domain.decisions import PlannedTurn, TeacherUtterance
from luna_tutor.domain.evidence import SupportGiven
from luna_tutor.domain.state import ActivityProgress
from luna_tutor.domain.text_observations import observe_delivery


def confirm_text_delivery(plan: PlannedTurn, utterance: TeacherUtterance,
                          previous_activity_id: str | None) -> PlannedTurn:
    context = plan.teacher_request.activity_context
    if context is None or utterance.generation_mode == 'fallback':
        return plan
    state = plan.proposed_next_state
    if context.activity_id != state.activity_id or context.stage_id != state.stage_id:
        raise ValueError('Teacher delivery must match the authorized activity')
    text = utterance.spoken_text.casefold()
    progress = {item.activity_id: item for item in state.activity_progress}
    previous = progress.get(previous_activity_id)
    if previous is not None:
        progress[previous.activity_id] = previous.model_copy(update={
            'feedback_delivered': previous.feedback_delivered or (
                plan.decision.feedback_action not in {'none', 'privacy_redirect'}),
            'learner_asked_teacher': previous.learner_asked_teacher or (
                plan.evidence.response_kind == 'asks_teacher'),
        })
    old = progress.get(context.activity_id, ActivityProgress(activity_id=context.activity_id))
    models, opportunity = observe_delivery(context, text)
    progress[context.activity_id] = old.model_copy(update={
        'status': 'completed' if context.delivery_only else (
            'in_progress' if old.status == 'not_started' else old.status),
        'model_repetitions_delivered': min(2, old.model_repetitions_delivered + models),
        'response_opportunity_given': old.response_opportunity_given or opportunity,
    })
    review_model = plan.teacher_request.review_objective
    review_word_given = bool(review_model and any(
        re.search(r'(?<!\w)' + re.escape(word.casefold()) + r'(?!\w)', text)
        for word in review_model.target_words))
    support = SupportGiven(
        model_spoken_recently=bool(models) or review_word_given,
        choices_given=opportunity and ' or ' in text,
        sentence_starter_given=bool(re.search(r'\b(you can say|start with)\b', text)),
    )
    delivered = state.model_copy(update={
        'activity_progress': tuple(progress.values()), 'support_given': support,
    })
    # A refined proposal remains uncommitted until the outer repository stores
    # both this receipt and the validated wording in one transaction.
    return plan.model_copy(update={'proposed_next_state': delivered})
