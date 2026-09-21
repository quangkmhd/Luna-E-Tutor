"""Teacher wording over deterministic teaching decisions."""

import json
import logging

from luna_tutor.domain.decisions import TeacherTurnRequest, TeacherUtterance
from luna_tutor.domain.privacy import redact_sensitive_contact
from luna_tutor.llm.openrouter import InvalidModelOutputError, OpenRouterError, ProviderError
from luna_tutor.prompts.loader import load_grade_system_prompt


class InvalidTeacherResultError(InvalidModelOutputError):
    """Retained for compatibility with API callers handling older results."""


logger = logging.getLogger(__name__)


def _log_text(text: str, limit: int = 500) -> str:
    """Keep diagnostics useful without retaining contact details or huge output."""
    sanitized = redact_sensitive_contact(text).text.replace('\n', '\\n')
    return sanitized if len(sanitized) <= limit else sanitized[:limit] + '...[truncated]'


class GeminiTeacher:
    def __init__(self, client, *, grade: int = 5):
        self._client = client
        self._prompt = load_grade_system_prompt(grade, 'teacher')

    async def respond(self, request: TeacherTurnRequest) -> TeacherUtterance:
        activity_id = request.activity_context.activity_id if request.activity_context else 'none'
        logger.info(
            'teacher_generation_started turn_id=%s action=%s activity_id=%s',
            request.turn_id, request.feedback_action, activity_id,
        )
        payload = request.model_dump(mode='json')
        try:
            text = await self._client.text_chat([
                {'role': 'system', 'content': self._prompt},
                {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)},
            ], request.turn_id)
        except ProviderError as error:
            logger.error(
                'teacher_provider_failed turn_id=%s status=%s reason=%s',
                request.turn_id, error.status_code, error.reason,
            )
            raise
        except OpenRouterError as error:
            logger.error(
                'teacher_model_output_failed turn_id=%s status=%s reason=%s',
                request.turn_id, error.status_code, error.reason,
            )
            raise

        utterance = TeacherUtterance(
            spoken_text=text,
            delivery_intent=('reassuring' if request.emotional_support else 'encouraging'),
            generation_mode='model',
        )
        logger.info(
            'teacher_response_forwarded turn_id=%s text=%r',
            request.turn_id, _log_text(utterance.spoken_text),
        )
        return utterance
