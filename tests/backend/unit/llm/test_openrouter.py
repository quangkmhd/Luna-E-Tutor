import json
import traceback

import httpx
import pytest

from luna_tutor.config import Settings
from luna_tutor.llm.openrouter import (
    InvalidModelOutputError, OpenRouterClient, ProviderError,
)

ENDPOINT = 'https://openrouter.ai/api/v1/chat/completions'
SCHEMA = {'type': 'object', 'properties': {'ok': {'type': 'boolean'}},
          'required': ['ok'], 'additionalProperties': False}
MESSAGES = [{'role': 'user', 'content': 'Hello'}]
pytestmark = pytest.mark.asyncio


async def test_text_chat_returns_plain_assistant_text_without_json_schema(
        respx_mock, completion_response):
    route = respx_mock.post(ENDPOINT).mock(
        return_value=completion_response('Good answer, Quang! Can you say city?'))

    async with OpenRouterClient(Settings('test-key')) as client:
        result = await client.text_chat(MESSAGES, 'turn-plain-text')

    body = json.loads(route.calls.last.request.content)
    assert result == 'Good answer, Quang! Can you say city?'
    assert body['reasoning'] == {'effort': 'minimal'}
    assert 'response_format' not in body


async def test_request_uses_strict_schema_pinned_model_timeout_and_redacted_contact(
        respx_mock, completion_response):
    route = respx_mock.post(ENDPOINT).mock(return_value=completion_response({'ok': True}))
    messages = [{'role': 'user', 'content': 'Call 0912 345 678. I live in the city.'}]
    async with OpenRouterClient(Settings('test-key', request_timeout_seconds=7.5)) as client:
        result = await client.structured_chat(messages, SCHEMA, 'turn-1')
    request = route.calls.last.request
    body = json.loads(request.content)
    assert result == {'ok': True}
    assert request.headers['Authorization'] == 'Bearer test-key'
    assert body['model'] == 'google/gemini-3.5-flash-lite'
    assert body['temperature'] == 0
    assert body['stream'] is False
    assert body['reasoning'] == {'effort': 'minimal'}
    assert body['provider']['require_parameters'] is True
    assert body['response_format']['type'] == 'json_schema'
    assert body['response_format']['json_schema']['strict'] is True
    assert body['response_format']['json_schema']['schema'] == SCHEMA
    assert set(request.extensions['timeout'].values()) == {7.5}
    assert '0912' not in request.content.decode()
    assert '[REDACTED_PHONE]' in request.content.decode()
    assert messages[0]['content'].startswith('Call 0912')  # Caller input is unchanged.


@pytest.mark.parametrize('status', [429, 502, 503, 504])
async def test_retries_only_transient_http_status_once_with_bounded_jitter(
        status, respx_mock, completion_response, monkeypatch):
    waits = []

    async def sleep(delay):
        waits.append(delay)

    monkeypatch.setattr('luna_tutor.llm.openrouter.asyncio.sleep', sleep)
    route = respx_mock.post(ENDPOINT).mock(side_effect=[
        httpx.Response(status, text='private provider body'),
        completion_response({'ok': True}),
    ])
    async with OpenRouterClient(Settings('test-key')) as client:
        assert await client.structured_chat(MESSAGES, SCHEMA, 'turn-1') == {'ok': True}
    assert route.call_count == 2
    assert len(waits) == 1
    assert 0.25 <= waits[0] <= 0.75


async def test_transient_failure_is_bounded_and_does_not_retain_provider_body(
        respx_mock, monkeypatch, caplog):
    async def sleep(_):
        pass

    monkeypatch.setattr('luna_tutor.llm.openrouter.asyncio.sleep', sleep)
    route = respx_mock.post(ENDPOINT).respond(503, text='0912 345 678 test-key')
    async with OpenRouterClient(Settings('test-key')) as client:
        with pytest.raises(ProviderError) as caught:
            await client.structured_chat(MESSAGES, SCHEMA, 'turn-1')
    error = caught.value
    assert route.call_count == 2
    assert error.status_code == 503
    assert error.request_id == 'turn-1'
    diagnostics = str(error) + repr(vars(error)) + ''.join(traceback.format_exception(error)) + caplog.text
    assert '0912' not in diagnostics
    assert 'test-key' not in diagnostics
    assert not hasattr(error, 'response')


@pytest.mark.parametrize('status', [400, 401, 403, 404, 408, 422, 500, 501, 302])
async def test_non_retryable_http_status_raises_without_retry(status, respx_mock):
    route = respx_mock.post(ENDPOINT).respond(status, text='private response')
    async with OpenRouterClient(Settings('test-key')) as client:
        with pytest.raises(ProviderError) as caught:
            await client.structured_chat(MESSAGES, SCHEMA, 'turn-1')
    assert caught.value.status_code == status
    assert route.call_count == 1


@pytest.mark.parametrize('exception', [httpx.ConnectError, httpx.ReadTimeout])
async def test_transport_errors_are_safe_provider_failures_without_retry(
        exception, respx_mock):
    route = respx_mock.post(ENDPOINT).mock(side_effect=exception('private test-key 0912345678'))
    async with OpenRouterClient(Settings('test-key')) as client:
        with pytest.raises(ProviderError) as caught:
            await client.structured_chat(MESSAGES, SCHEMA, 'turn-1')
    assert route.call_count == 1
    assert caught.value.status_code is None
    assert caught.value.request_id == 'turn-1'
    assert caught.value.__context__ is None
    assert 'private' not in ''.join(traceback.format_exception(caught.value))


@pytest.mark.parametrize('content', [
    'not json', '```json\n{}\n```', '[]', 'null', '{"x": NaN}', '{"x":1,"x":2}',
])
async def test_invalid_model_content_is_not_retried(content, respx_mock, completion_response):
    route = respx_mock.post(ENDPOINT).mock(return_value=completion_response(content))
    async with OpenRouterClient(Settings('test-key')) as client:
        with pytest.raises(InvalidModelOutputError) as caught:
            await client.structured_chat(MESSAGES, SCHEMA, 'turn-1')
    assert route.call_count == 1
    assert caught.value.status_code == 200
    assert caught.value.__context__ is None


@pytest.mark.parametrize('body', [{}, {'choices': []}, {'choices': [{'message': {'content': None}}]}])
async def test_invalid_envelope_is_not_retried(body, respx_mock):
    route = respx_mock.post(ENDPOINT).respond(200, json=body)
    async with OpenRouterClient(Settings('test-key')) as client:
        with pytest.raises(InvalidModelOutputError):
            await client.structured_chat(MESSAGES, SCHEMA, 'turn-1')
    assert route.call_count == 1


async def test_truncated_output_is_rejected_even_when_json_parses(respx_mock, completion_response):
    route = respx_mock.post(ENDPOINT).mock(return_value=completion_response({}, finish_reason='length'))
    async with OpenRouterClient(Settings('test-key')) as client:
        with pytest.raises(InvalidModelOutputError):
            await client.structured_chat(MESSAGES, SCHEMA, 'turn-1')
    assert route.call_count == 1


async def test_model_cannot_be_overridden():
    with pytest.raises(ValueError, match='model'):
        OpenRouterClient(Settings('test-key', openrouter_model='some-other-model'))


@pytest.mark.parametrize('body', [
    {'error': {'code': 502, 'message': 'test-key 0912345678'}},
    {'choices': [{'finish_reason': 'error', 'message': {'content': '{}'},
                  'error': {'code': 502, 'message': 'test-key 0912345678'}}]},
])
async def test_in_band_errors_remain_provider_failures_without_http_retry(body, respx_mock):
    route = respx_mock.post(ENDPOINT).respond(200, json=body)
    async with OpenRouterClient(Settings('test-key')) as client:
        with pytest.raises(ProviderError) as caught:
            await client.structured_chat(MESSAGES, SCHEMA, 'turn-1')
    assert caught.value.status_code == 200
    assert route.call_count == 1
    assert 'test-key' not in str(caught.value)
    assert '0912345678' not in str(caught.value)


async def test_json_message_redaction_keeps_numeric_metadata(respx_mock, completion_response):
    route = respx_mock.post(ENDPOINT).mock(return_value=completion_response({'ok': True}))
    messages = [{'role': 'user', 'content': json.dumps({
        'state_version': 12345678, 'learner_transcript': 'Call 0912 345 678',
    })}]
    async with OpenRouterClient(Settings('test-key')) as client:
        await client.structured_chat(messages, SCHEMA, 'turn-1')
    body = json.loads(route.calls.last.request.content)
    assert json.loads(body['messages'][0]['content']) == {
        'state_version': 12345678, 'learner_transcript': 'Call [REDACTED_PHONE]',
    }


async def test_injected_http_client_stays_caller_owned(respx_mock, completion_response):
    respx_mock.post(ENDPOINT).mock(return_value=completion_response({'ok': True}))
    async with httpx.AsyncClient() as http_client:
        async with OpenRouterClient(Settings('test-key'), http_client=http_client) as client:
            await client.structured_chat(MESSAGES, SCHEMA, 'turn-1')
        assert not http_client.is_closed
