"""Explicit user-end policy; no model call or fabricated learner evidence."""
from luna_tutor.domain.state import ActivityProgress, LessonState


def finish_text_lesson(state: LessonState) -> LessonState:
    """Finish the shared Free Talk → summary lifecycle after repository guards."""
    text = "Our role-play is over. I'm Luna again. "
    if any(item.attempted for item in state.objective_progress):
        text += "Thank you for practising English with me! "
    else:
        text += "Thank you for spending time with me! "
    if state.review_queue or any(item.needs_review for item in state.objective_progress):
        text += "We can practise the things you found tricky next time. "
    text += "Your progress is saved. See you next time!"
    progress = {item.activity_id: item for item in state.activity_progress}
    if state.activity_id:
        current = progress.get(state.activity_id, ActivityProgress(activity_id=state.activity_id))
        progress[state.activity_id] = current.model_copy(update={
            'status': 'completed', 'completion_reason': 'Learner ended Free Talk.'})
    progress['summary.reflect'] = ActivityProgress(
        activity_id='summary.reflect', status='completed',
        completion_reason='Text closing delivered on learner request.')
    return state.model_copy(update={
        'state_version': state.state_version + 1, 'status': 'completed',
        'stop_requested': True, 'stage_id': 'summary', 'activity_id': 'summary.reflect',
        'objective_id': None, 'attempt_count': 0,
        'completed_stage_ids': tuple(dict.fromkeys((*state.completed_stage_ids, 'free-talk', 'summary'))),
        'activity_progress': tuple(progress.values()),
        'last_teacher_turn': text, 'closing_message': text,
    })
