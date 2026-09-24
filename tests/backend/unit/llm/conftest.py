import json

import httpx
import pytest

@pytest.fixture
def completion_response():
    def response(content, *, finish_reason='stop'):
        return httpx.Response(200, json={
            'id': 'gen-test', 'object': 'chat.completion', 'created': 1,
            'model': 'google/gemini-3.5-flash-lite',
            'choices': [{'index': 0, 'finish_reason': finish_reason,
                         'message': {'role': 'assistant', 'content': (
                             content if isinstance(content, str) else json.dumps(content))}}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 10, 'total_tokens': 20},
        })
    return response
