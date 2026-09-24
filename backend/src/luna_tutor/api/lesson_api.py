"""Session-local Grade 3 scripted teaching HTTP API."""

from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import APIError
from pydantic import BaseModel, ConfigDict, Field

from luna_tutor.curriculum.lesson_catalog import GRADE3_UNIT_ID, ScriptedCatalog
from luna_tutor.llm.openrouter import InvalidModelOutputError, ProviderError
from luna_tutor.speech.language_segments import plain_speech_text
from luna_tutor.teaching.lesson_sessions import ScriptedSession, ScriptedSessionStore
from luna_tutor.teaching.teacher_context import InvalidTeacherOutputError


class _Input(BaseModel):
    model_config = ConfigDict(extra='forbid')


class CreateSessionInput(_Input):
    unit_id: str
    lesson_id: int = Field(default=1, ge=1)
    previous_session_id: str | None = None


class TurnInput(_Input):
    turn_id: str = Field(min_length=1)
    learner_text: str = Field(min_length=1, max_length=8000)
    expected_state_version: int = Field(ge=0)
    source: Literal['text', 'voice'] = 'text'


def _error(status: int, code: str, message: str, retryable: bool = False):
    raise HTTPException(status_code=status, detail={
        'code': code, 'message': message, 'retryable': retryable})


def _view(session: ScriptedSession, catalog: ScriptedCatalog) -> dict:
    controller = session.conversation.controller
    item = controller.lesson.items[controller.item_index] if controller.item_index >= 0 else None
    return {
        'session_id': session.id,
        'unit_id': session.unit_id,
        'lesson_id': session.lesson_id,
        'unit': catalog.unit,
        'state_version': session.version,
        'stage_id': item.type if item else 'narration',
        'activity_id': f'item-{controller.item_index + 1}' if item else None,
        'objective_id': f'item-{controller.item_index + 1}' if item and item.type == 'practice' else None,
        'status': session.status,
        'messages': [
            {**message, 'text': plain_speech_text(message['text'])}
            if message['role'] == 'teacher' else message.copy()
            for message in session.messages
        ],
        'flashcards': [card.model_dump() for card in controller.lesson.cards],
    }


def create_lesson_api(catalog: ScriptedCatalog, store: ScriptedSessionStore,
                        *, allowed_origins: list[str] | None = None,
                        lifespan=None) -> FastAPI:
    app = FastAPI(title='Luna Grade 3 Tutor', lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins or ['http://localhost:3000'],
        allow_credentials=False,
        allow_methods=['GET', 'POST'],
        allow_headers=['Content-Type'],
    )

    @app.get('/api/units')
    def units():
        return catalog.units()

    @app.get('/api/units/{unit_id}/lessons')
    def lessons(unit_id: str):
        if unit_id != GRADE3_UNIT_ID:
            _error(404, 'UNKNOWN_UNIT', f'Unknown curriculum unit {unit_id}.')
        try:
            return catalog.lessons(unit_id)
        except LookupError:
            _error(404, 'UNKNOWN_UNIT', f'Unknown curriculum unit {unit_id}.')

    @app.post('/api/sessions')
    async def create_session(body: CreateSessionInput):
        try:
            return _view(store.create(body.unit_id, body.lesson_id), catalog)
        except LookupError:
            _error(400, 'UNKNOWN_LESSON', 'Unknown Grade 3 lesson.')
        except ValueError:
            _error(422, 'INVALID_LESSON_CONTENT',
                   'Bài học đang chờ cập nhật học liệu theo định dạng mới.')

    @app.post('/api/sessions/reset')
    async def reset_session(body: CreateSessionInput):
        session = await create_session(body)
        if body.previous_session_id:
            try:
                await store.close(body.previous_session_id)
            except LookupError:
                pass
        return session

    @app.get('/api/sessions')
    def list_sessions():
        return [_view(session, catalog) for session in store.list_active()]

    @app.get('/api/sessions/{session_id}')
    def get_session(session_id: str):
        try:
            return _view(store.get(session_id), catalog)
        except LookupError:
            _error(404, 'SESSION_NOT_FOUND', 'Session was not found.')

    @app.post('/api/sessions/{session_id}/turns')
    async def submit_turn(session_id: str, body: TurnInput):
        try:
            output = await store.submit(
                session_id, body.turn_id, body.learner_text,
                body.expected_state_version, source=body.source)
            return {'turn_id': body.turn_id,
                    'session': _view(store.get(session_id), catalog),
                    'output': [item.__dict__ for item in output]}
        except LookupError:
            _error(404, 'SESSION_NOT_FOUND', 'Session was not found.')
        except InvalidModelOutputError:
            _error(503, 'INVALID_EVALUATION', 'The tutor could not assess that turn.', True)
        except ProviderError:
            _error(503, 'PROVIDER_UNAVAILABLE', 'The tutor service is temporarily unavailable.', True)
        except APIError:
            _error(503, 'PROVIDER_UNAVAILABLE', 'The tutor service is temporarily unavailable.', True)
        except InvalidTeacherOutputError:
            _error(503, 'INVALID_TEACHER_OUTPUT', 'Luna chưa thể trả lời lượt này.', True)
        except ValueError as error:
            _error(422, 'INVALID_TURN', str(error))
        except RuntimeError as error:
            _error(409, 'SESSION_NOT_READY', str(error))

    @app.post('/api/sessions/{session_id}/voice/start')
    async def start_voice(session_id: str):
        try:
            output = await store.start_voice(session_id)
            return {'session': _view(store.get(session_id), catalog),
                    'output': [item.__dict__ for item in output]}
        except LookupError:
            _error(404, 'SESSION_NOT_FOUND', 'Session was not found.')
        except RuntimeError as error:
            _error(409, 'SESSION_NOT_READY', str(error))

    @app.post('/api/sessions/{session_id}/voice/delivery-finished')
    async def finish_voice_delivery(session_id: str):
        try:
            output = await store.finish_voice_delivery(session_id)
            return {'session': _view(store.get(session_id), catalog),
                    'output': [item.__dict__ for item in output]}
        except LookupError:
            _error(404, 'SESSION_NOT_FOUND', 'Session was not found.')
        except RuntimeError as error:
            _error(409, 'SESSION_NOT_READY', str(error))

    @app.post('/api/sessions/{session_id}/abandon')
    async def abandon(session_id: str):
        try:
            session = store.get(session_id)
            view = _view(session, catalog)
            await store.close(session_id)
            return {**view, 'status': 'abandoned'}
        except LookupError:
            _error(404, 'SESSION_NOT_FOUND', 'Session was not found.')

    return app
