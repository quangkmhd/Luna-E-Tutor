from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from luna_tutor.llm.openrouter import InvalidModelOutputError, ProviderError
from luna_tutor.speaking.catalog import load_topics
from luna_tutor.speaking.models import SessionConfig, TurnInput
from luna_tutor.speaking.repository import Conflict, NotFound, SessionClosed


class SuggestRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    topic: str = Field(min_length=1, max_length=120)


class FinishRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(ge=0)


def _error(status, code, message, retryable=False):
    raise HTTPException(status_code=status, detail={
        'code': code, 'message': message, 'retryable': retryable})


def build_speaking_router(service, repository):
    router = APIRouter(prefix='/api/speaking')

    @router.get('/topics')
    async def topics(): return load_topics()

    @router.post('/suggestions')
    async def suggestions(request: SuggestRequest):
        try: return await service.models.suggest(request.topic)
        except (ProviderError, InvalidModelOutputError):
            _error(503, 'PROVIDER_UNAVAILABLE', 'Could not suggest words. Please retry.', True)

    @router.post('/sessions')
    async def create(config: SessionConfig):
        try: return await service.start(config)
        except (ProviderError, InvalidModelOutputError):
            _error(503, 'PROVIDER_UNAVAILABLE', 'Could not start the conversation.', True)

    @router.get('/sessions')
    async def list_sessions(): return repository.list_sessions()

    @router.get('/sessions/{session_id}')
    async def get(session_id: str):
        try: return repository.get(session_id)
        except NotFound: _error(404, 'SESSION_NOT_FOUND', 'Speaking session was not found.')

    @router.post('/sessions/{session_id}/turns')
    async def submit(session_id: str, turn: TurnInput):
        try: return await service.submit(session_id, turn)
        except NotFound: _error(404, 'SESSION_NOT_FOUND', 'Speaking session was not found.')
        except SessionClosed: _error(409, 'SESSION_CLOSED', 'Speaking session has ended.')
        except Conflict as error: _error(409, 'STATE_CONFLICT', str(error), True)
        except (ProviderError, InvalidModelOutputError):
            _error(503, 'PROVIDER_UNAVAILABLE', 'Could not prepare a reply. Please retry.', True)

    @router.post('/sessions/{session_id}/finish')
    async def finish(session_id: str, request: FinishRequest):
        try: return service.finish(session_id, request.expected_version)
        except NotFound: _error(404, 'SESSION_NOT_FOUND', 'Speaking session was not found.')
        except Conflict as error: _error(409, 'STATE_CONFLICT', str(error), True)

    return router
