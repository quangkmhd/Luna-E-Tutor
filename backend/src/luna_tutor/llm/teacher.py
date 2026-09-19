"""Bounded Teacher wording over deterministic teaching decisions."""

from importlib.resources import files
import re

from pydantic import ValidationError

from luna_tutor.domain.decisions import TeacherTurnRequest, TeacherUtterance
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
    for variant in (reference, addressed):
        expected = tokens(variant)
        if expected and any(spoken[i:i + len(expected)] == expected
                            for i in range(len(spoken) - len(expected) + 1)):
            return True
    return False


def _valid_spoken_text(text: str, request: TeacherTurnRequest) -> bool:
    return (
        bool(text.strip())
        and not _MARKDOWN.search(text)
        and not _FORCED_REPEAT.search(text)
        and text.count('?') <= request.constraints.max_questions
        and (request.corrected_form is None or _contains_recast(text, request.corrected_form))
    )


def _fallback(request: TeacherTurnRequest) -> TeacherUtterance:
    if request.feedback_action == 'recast' and request.corrected_form:
        text = f'Oh, {request.corrected_form}'
    elif request.feedback_action == 'explain_meaning':
        text = 'Let us look at that together, Quang.'
    elif request.feedback_action == 'privacy_redirect':
        text = 'Please use a made-up phone number, or say the digits as words.'
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
        try:
            raw = await self._client.structured_chat([
                {'role': 'system', 'content': self._prompt},
                {'role': 'user', 'content': request.model_dump_json()},
            ], TeacherUtterance.model_json_schema(), request.turn_id)
            utterance = TeacherUtterance.model_validate(raw)
            if utterance.generation_mode != 'model' or not _valid_spoken_text(
                    utterance.spoken_text, request):
                return _fallback(request)
            return utterance
        except (OpenRouterError, ValidationError, ValueError, TypeError, KeyError):
            return _fallback(request)
