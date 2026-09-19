"""Bounded Teacher wording over deterministic teaching decisions."""

import json
from importlib.resources import files
import re

from pydantic import ValidationError

from luna_tutor.domain.decisions import TeacherTurnRequest, TeacherUtterance
from luna_tutor.domain.text_observations import observe_delivery
from luna_tutor.llm.openrouter import OpenRouterError, InvalidModelOutputError


class InvalidTeacherResultError(InvalidModelOutputError):
    """Teacher output cannot safely fulfill the proposed teaching turn."""


_MARKDOWN = re.compile(r'(^|\s)(#{1,6}\s|[-*]\s|\*\*|__|```)', re.MULTILINE)
_FORCED_REPEAT = re.compile(r'\b(repeat after me|say it again|repeat it)\b', re.IGNORECASE)


def _contains_recast(text: str, correction: str) -> bool:
    """Permit conversational person changes, preserving the corrected construction."""
    def tokens(value):
        return re.findall(r"\w+(?:'\w+)?", value.replace('’', "'").casefold())

    reference = correction.replace('’', "'").casefold()
    addressed = reference
    for pattern, replacement in (
        (r"\bi'm\b", "you're"), (r'\bi am\b', 'you are'),
        (r'\bi was\b', 'you were'), (r'\bmy\b', 'your'), (r'\bi\b', 'you'),
    ):
        addressed = re.sub(pattern, replacement, addressed)
    spoken = tokens(text)
    expected = tokens(addressed)
    return bool(expected) and any(spoken[i:i + len(expected)] == expected
                                  for i in range(len(spoken) - len(expected) + 1))


def teacher_output_issues(text: str, request: TeacherTurnRequest) -> list[str]:
    issues = []
    if not text.strip() or _MARKDOWN.search(text):
        issues.append('Use non-empty plain spoken text without Markdown.')
    if request.feedback_action == 'recast' and _FORCED_REPEAT.search(text):
        issues.append('Do not demand repetition of the correction; use a natural response invitation.')
    if text.count('?') > request.constraints.max_questions:
        issues.append(f'Ask at most {request.constraints.max_questions} question(s). Combine or choose; do not ask an open question then a separate choice question.')
    if request.corrected_form and not _contains_recast(text, request.corrected_form):
        issues.append("Recast the child's meaning once using you/your, retaining the corrected grammar. Do not claim their first-person fact as your own biography.")
    if request.activity_context:
        context = request.activity_context
        models, invitation = observe_delivery(context, text)
        if models < context.remaining_model_repetitions:
            issues.append(f'Model each target word {context.remaining_model_repetitions} time(s) in this reply.')
        if context.needs_response_invitation and context.kind == 'vocabulary_introduction':
            invitation = bool(re.search(r'\b(say|saying|repeat|try|your turn|use the word)\b', text, re.IGNORECASE))
        if context.needs_response_invitation and not invitation:
            issues.append('Invite Quang to respond to the authorized activity. For a new word, invite him to say/use that word; do not replace his practice turn with a topic question. Example invitation: Can you say ' + ', '.join(context.target_words) + '?')
    return issues


def _fallback(request: TeacherTurnRequest) -> TeacherUtterance:
    if request.feedback_action == 'recast' and request.corrected_form:
        text = f'Oh, {request.corrected_form}'
    elif request.feedback_action == 'explain_meaning':
        text = 'Let us look at that together, Quang.'
    elif request.feedback_action == 'privacy_redirect':
        text = 'Keep your real number private. We are practising the words phone number.'
    elif request.feedback_action == 'clarify':
        text = 'I did not hear that clearly. Could you tell me again?'
    elif request.feedback_action == 'stop':
        text = 'Okay, Quang. We can stop here for today.'
    elif request.emotional_support:
        text = 'That is okay, Quang. We can take it one small step at a time.'
    else:
        text = 'Let us take a moment, Quang. We can try that together.'
    # Activity instructions are internal directives, never learner-facing text.
    text = re.sub(r'[*_#`]', '', text).strip()
    if text.count('?') > request.constraints.max_questions:
        first, *_ = text.split('?', 1)
        text = first.rstrip() + ('?' if request.constraints.max_questions else '.')
    return TeacherUtterance(spoken_text=text, delivery_intent=(
        'reassuring' if request.emotional_support else 'encouraging'),
        generation_mode='fallback')


class GeminiTeacher:
    def __init__(self, client):
        self._client = client
        self._prompt = files('luna_tutor.prompts').joinpath(
            'teacher-system.md').read_text(encoding='utf-8')

    async def respond(self, request: TeacherTurnRequest) -> TeacherUtterance:
        feedback = []
        for attempt in range(2):
            payload = request.model_dump(mode='json')
            if feedback:
                payload['validation_feedback'] = feedback
            try:
                raw = await self._client.structured_chat([
                    {'role': 'system', 'content': self._prompt},
                    {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)},
                ], TeacherUtterance.model_json_schema(), request.turn_id)
            except OpenRouterError:
                # Network/provider failures are handled by the client/API, not a wording repair loop.
                return _fallback(request)
            try:
                utterance = TeacherUtterance.model_validate(raw)
                feedback = teacher_output_issues(utterance.spoken_text, request)
                if utterance.generation_mode != 'model':
                    feedback.append('Set generation_mode to model.')
                if not feedback:
                    return utterance
            except (ValidationError, ValueError, TypeError, KeyError):
                feedback = ['Return exactly the supplied TeacherUtterance JSON schema.']
        return _fallback(request)
