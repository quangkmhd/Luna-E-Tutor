"""Small asynchronous OpenRouter adapter with safe, bounded failures."""

import asyncio
import json
import math
import random
from typing import Any, Self

import httpx

from luna_tutor.config import Settings
from luna_tutor.domain.privacy import redact_sensitive_contact

_ENDPOINT = 'https://openrouter.ai/api/v1/chat/completions'
_RETRYABLE_STATUSES = {429, 502, 503, 504}


class OpenRouterError(RuntimeError):
    """Safe diagnostics only: never attach HTTP requests, bodies, or credentials."""

    def __init__(self, *, status_code: int | None, request_id: str, reason: str):
        self.status_code = status_code
        self.request_id = redact_sensitive_contact(request_id).text
        self.reason = reason
        super().__init__(f'{reason} (status={status_code}, request_id={self.request_id})')


class ProviderError(OpenRouterError):
    """Transport or provider failure, never evidence of a learner error."""


class InvalidModelOutputError(OpenRouterError):
    """Unusable model output, never retried or converted to learner evidence."""


def _redact_contact(value: Any) -> Any:
    """Copy JSON-compatible data, replacing contact text before serialization."""
    if isinstance(value, str):
        return redact_sensitive_contact(value).text
    if isinstance(value, list):
        return [_redact_contact(item) for item in value]
    if isinstance(value, dict):
        return {key: _redact_contact(item) for key, item in value.items()}
    return value


def _message_content(content: str) -> str:
    # Evaluator messages contain a JSON document. Redact its text values without
    # corrupting numeric metadata (for example a large state version).
    try:
        value = json.loads(content)
    except ValueError:
        value = None
    if isinstance(value, (dict, list)):
        return json.dumps(_redact_contact(value), ensure_ascii=False, allow_nan=False)
    return redact_sensitive_contact(content).text


def _unique_object(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def _invalid_constant(_: str):
    raise ValueError('Non-standard JSON constant')


def _parse_completion(response: httpx.Response) -> tuple[dict | None, bool]:
    # Do not let a JSONDecodeError (which stores the document) escape or become
    # the context of the application exception.
    try:
        envelope = response.json()
        if 'error' in envelope:
            return None, True
        choice = envelope['choices'][0]
        if 'error' in choice or choice.get('finish_reason') == 'error':
            return None, True
        if choice.get('finish_reason') != 'stop':
            return None, False
        content = choice['message']['content']
        if not isinstance(content, str):
            return None, False
        parsed = json.loads(content, object_pairs_hook=_unique_object,
                            parse_constant=_invalid_constant)
        return (parsed if isinstance(parsed, dict) else None), False
    except (ValueError, TypeError, KeyError, IndexError, AttributeError):
        return None, False


class OpenRouterClient:
    """Use as an async context manager, or explicitly call ``aclose``.

    A supplied HTTP client remains caller-owned. HTTPX timeouts bound each
    network operation; at most two HTTP attempts are made, with no model retry.
    """

    def __init__(self, settings: Settings, *, http_client: httpx.AsyncClient | None = None):
        if not settings.openrouter_model.strip():
            raise ValueError('OPENROUTER_MODEL is required')
        if not settings.openrouter_api_key.strip():
            raise ValueError('OPENROUTER_API_KEY is required')
        if not math.isfinite(settings.request_timeout_seconds) or settings.request_timeout_seconds <= 0:
            raise ValueError('Request timeout must be finite and positive')
        self._api_key = settings.openrouter_api_key
        self._model = settings.openrouter_model
        self._timeout = settings.request_timeout_seconds
        self._owns_client = http_client is None
        self._http = http_client if http_client is not None else httpx.AsyncClient()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_):
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http.aclose()

    async def structured_chat(self, messages: list[dict[str, str]], schema: dict,
                              request_id: str) -> dict:
        """Return a JSON object; the caller validates its domain-specific schema.

        Retry only HTTP 429/502/503/504 once. Transport errors, auth errors, and
        invalid model output fail immediately with body-free typed exceptions.
        """
        payload = {
            'model': self._model, 'temperature': 0, 'stream': False,
            'messages': [{**message, 'content': _message_content(message['content'])}
                         for message in messages],
            'provider': {'require_parameters': True},
            'response_format': {'type': 'json_schema', 'json_schema': {
                'name': 'structured_result', 'strict': True, 'schema': schema,
            }},
        }
        for attempt in range(2):
            response = None
            try:
                response = await self._http.post(
                    _ENDPOINT, headers={'Authorization': f'Bearer {self._api_key}'},
                    json=payload, timeout=self._timeout, follow_redirects=False,
                )
            except httpx.RequestError:
                pass
            # Raise outside the except block: retaining an HTTPX exception as
            # __context__ would also retain its request and Authorization header.
            if response is None:
                raise ProviderError(status_code=None, request_id=request_id,
                                    reason='OpenRouter transport failure')
            status = response.status_code
            if status in _RETRYABLE_STATUSES and attempt == 0:
                await asyncio.sleep(random.uniform(0.25, 0.75))
                continue
            if not response.is_success:
                del response
                raise ProviderError(status_code=status, request_id=request_id,
                                    reason='OpenRouter HTTP failure')
            result, provider_failed = _parse_completion(response)
            del response
            if provider_failed:
                raise ProviderError(status_code=status, request_id=request_id,
                                    reason='OpenRouter generation failure')
            if result is None:
                raise InvalidModelOutputError(status_code=status, request_id=request_id,
                                              reason='Invalid structured model output')
            return result
        raise AssertionError('Unreachable retry loop')
