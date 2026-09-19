"""Evidence-only Gemini evaluation; no teaching decisions or Teacher prose."""

from importlib.resources import files

from pydantic import ValidationError

from luna_tutor.domain.evidence import EvaluatorRequest, EvaluatorResult
from luna_tutor.llm.openrouter import (
    InvalidModelOutputError, OpenRouterClient, _redact_contact,
)


class InvalidEvaluatorResultError(InvalidModelOutputError):
    """Model output failed the evidence contract or request correlation."""


def _provider_id(value: str) -> str:
    """Alias digit-heavy metadata without collisions or redaction exemptions.

    Escape the prefix too, so a literal caller ID cannot equal another ID's
    alias. Letter-only hex preserves identity without looking like contact text.
    """
    prefix = 'correlation-'
    if value.startswith(prefix) or _redact_contact(value) != value:
        return prefix + value.encode().hex().translate(str.maketrans('0123456789abcdef',
                                                                    'abcdefghijklmnop'))
    return value


def _correlates(request: EvaluatorRequest, result: EvaluatorResult) -> bool:
    if result.turn_id != request.turn_id or result.state_version != request.state_version:
        return False
    if result.needs_clarification != (result.ambiguity_reason is not None):
        return False
    if result.response_kind == 'insufficient_data' and not result.needs_clarification:
        return False
    uncertain_input = (request.transcript_status != 'final' or request.stt_issue
                       or request.audio_issue or not request.learner_transcript.strip())
    if uncertain_input and not result.needs_clarification:
        return False
    allowed_ids = {objective.objective_id for objective in request.active_objectives}
    # Search separate real-text spans so marker fragments and quotes crossing
    # a redaction boundary cannot masquerade as learner-provided evidence.
    evidence_spans = request.learner_transcript.split('[REDACTED_PHONE]')
    for evidence in result.objective_evidence:
        if evidence.objective_id not in allowed_ids:
            return False
        if evidence.evidence_quote is not None and (
                not evidence.evidence_quote.strip()
                or not any(evidence.evidence_quote in span for span in evidence_spans)):
            return False
        if uncertain_input and (evidence.meaning_status == 'wrong_semantic_category'
                                or evidence.target_form_status == 'error_in_target_form'):
            return False
        if result.response_kind == 'asks_meaning' and evidence.recast_needed:
            return False
    return True


class GeminiEvaluator:
    def __init__(self, client: OpenRouterClient):
        self._client = client
        self._prompt = files('luna_tutor.prompts').joinpath('evaluator.md').read_text(encoding='utf-8')

    async def evaluate(self, request: EvaluatorRequest) -> EvaluatorResult:
        """Sanitize, request evidence, then strictly validate and correlate it.

        The caller owns client lifetime and handles exceptions as operational
        failures. No state is mutated and no substitute evaluation is invented.
        """
        # Revalidate a fresh sanitized snapshot: Pydantic model_copy and mutable
        # nested lists can otherwise bypass the original request validation.
        sanitized = _redact_contact(request.model_dump(mode='json', warnings=False))
        # Correlation metadata is not learner content. Preserve the caller's
        # exact identifiers locally, then use safe aliases on the provider wire.
        sanitized['turn_id'] = request.turn_id
        for objective, original in zip(sanitized['active_objectives'], request.active_objectives):
            objective['objective_id'] = original.objective_id
        validated_request = None
        try:
            validated_request = EvaluatorRequest.model_validate(sanitized)
        except ValidationError:
            pass
        if validated_request is None:
            raise ValueError('Invalid evaluator request')
        request = validated_request
        provider_request = request.model_copy(update={
            'turn_id': _provider_id(request.turn_id),
            'active_objectives': [objective.model_copy(update={
                'objective_id': _provider_id(objective.objective_id),
            }) for objective in request.active_objectives],
        })
        original_objective_ids = {_provider_id(objective.objective_id): objective.objective_id
                                  for objective in request.active_objectives}
        raw = await self._client.structured_chat([
            {'role': 'system', 'content': self._prompt},
            {'role': 'user', 'content': provider_request.model_dump_json()},
        ], EvaluatorResult.model_json_schema(), request.turn_id)
        result = None
        # Reject provider-introduced contact even in fields not typed SanitizedText.
        if _redact_contact(raw) == raw:
            try:
                result = EvaluatorResult.model_validate(raw)
            except ValidationError:
                pass
        del raw
        if result is not None and _correlates(provider_request, result):
            result = result.model_copy(update={
                'turn_id': request.turn_id,
                'objective_evidence': [evidence.model_copy(update={
                    'objective_id': original_objective_ids[evidence.objective_id],
                }) for evidence in result.objective_evidence],
            })
        else:
            result = None
        if result is None or not _correlates(request, result):
            raise InvalidEvaluatorResultError(
                status_code=200, request_id=request.turn_id,
                reason='Invalid or uncorrelated evaluator evidence',
            )
        return result
