from uuid import uuid4

from fastapi import APIRouter, Body, HTTPException

from luna_tutor.api.schemas import (
    CreateSessionRequest, MessageView, SessionView, SummaryView, TurnRequest,
    TurnResponse, VersionRequest,
)
from luna_tutor.domain.state import LessonState
from luna_tutor.llm.openrouter import InvalidModelOutputError, ProviderError
from luna_tutor.storage.session_repository import (
    SessionNotFoundError, StateConflictError, StoredSession,
)


GREETING = "Hello, Quang! I'm Luna. It's lovely to see you today!"


def _summary(stored: StoredSession) -> SummaryView:
    demonstrated, supported, review = [], [], []
    review_ids = {item.objective_id for item in stored.state.review_queue}
    for item in stored.state.objective_progress:
        if item.objective_id in review_ids or item.needs_review:
            review.append(item.objective_id)
        elif item.independent_uses:
            demonstrated.append(item.objective_id)
        elif item.supported_uses or item.attempted:
            supported.append(item.objective_id)
    observed = set(demonstrated + supported + review)
    return SummaryView(demonstrated=demonstrated, supported=supported,
                       needs_review=review,
                       not_yet_observed=[] if observed else ['No learning evidence recorded yet'])


def session_view(stored: StoredSession) -> SessionView:
    messages = [MessageView(role='teacher', text=GREETING)]
    for completed in stored.turns:
        messages.extend([
            MessageView(role='learner', text=completed.plan.learner_text,
                        turn_id=completed.plan.turn_id),
            MessageView(role='teacher', text=completed.teacher_utterance.spoken_text,
                        turn_id=completed.plan.turn_id,
                        delivery_intent=completed.teacher_utterance.delivery_intent),
        ])
    last = stored.turns[-1] if stored.turns else None
    state = stored.state
    return SessionView(
        session_id=state.session_id, unit_id=state.unit_id,
        state_version=state.state_version, stage_id=state.stage_id,
        activity_id=state.activity_id, objective_id=state.objective_id,
        status=state.status, messages=messages,
        review_queue=list(state.review_queue),
        objective_progress=list(state.objective_progress),
        last_evidence=last.plan.evidence if last else None,
        last_decision=last.plan.decision if last else None,
        summary=_summary(stored) if state.status == 'completed' else None,
    )


def _error(status: int, code: str, message: str, retryable: bool = False):
    raise HTTPException(status_code=status, detail={
        'code': code, 'message': message, 'retryable': retryable})


def build_router(repository, turn_service) -> APIRouter:
    router = APIRouter(prefix='/api')

    @router.post('/sessions', response_model=SessionView)
    async def create_session(_: CreateSessionRequest | None = Body(default=None)):
        session_id = str(uuid4())
        state = LessonState(
            session_id=session_id, unit_id='grade05.unit01', stage_id='warm-up',
            activity_id='warm-up.hello', last_teacher_turn=GREETING)
        return session_view(repository.create_session(state))

    @router.get('/sessions', response_model=list[SessionView])
    async def list_sessions():
        return [session_view(item) for item in repository.list_sessions()]

    @router.get('/sessions/{session_id}', response_model=SessionView)
    async def get_session(session_id: str):
        try:
            return session_view(repository.get_session(session_id))
        except SessionNotFoundError:
            _error(404, 'SESSION_NOT_FOUND', 'Session was not found.')

    @router.post('/sessions/{session_id}/turns', response_model=TurnResponse)
    async def submit_turn(session_id: str, request: TurnRequest):
        existing = repository.get_turn(session_id, request.turn_id)
        if existing is not None:
            return TurnResponse(turn_id=request.turn_id,
                                session=session_view(repository.get_session(session_id)))
        try:
            stored = repository.get_session(session_id)
            if stored.state.status != 'active':
                _error(409, 'SESSION_NOT_ACTIVE', 'Session is not active.')
            if stored.state.state_version != request.expected_state_version:
                _error(409, 'STATE_CONFLICT', 'Session state has changed.')
            completed = await turn_service.process(
                stored.state, request.learner_text, request.turn_id)
            repository.commit_turn(session_id, request.expected_state_version, completed)
            return TurnResponse(turn_id=request.turn_id,
                                session=session_view(repository.get_session(session_id)))
        except SessionNotFoundError:
            _error(404, 'SESSION_NOT_FOUND', 'Session was not found.')
        except StateConflictError:
            _error(409, 'STATE_CONFLICT', 'Session state has changed.')
        except InvalidModelOutputError:
            _error(503, 'INVALID_EVALUATION', 'The tutor could not assess that turn.', True)
        except ProviderError:
            _error(503, 'PROVIDER_UNAVAILABLE', 'The tutor service is temporarily unavailable.', True)

    @router.post('/sessions/{session_id}/abandon', response_model=SessionView)
    async def abandon(session_id: str):
        try:
            return session_view(repository.abandon_session(session_id))
        except SessionNotFoundError:
            _error(404, 'SESSION_NOT_FOUND', 'Session was not found.')

    @router.post('/sessions/{session_id}/finish', response_model=SessionView)
    async def finish(session_id: str, request: VersionRequest):
        try:
            return session_view(repository.finish_free_talk(
                session_id, request.expected_state_version))
        except SessionNotFoundError:
            _error(404, 'SESSION_NOT_FOUND', 'Session was not found.')
        except StateConflictError as error:
            code = 'NOT_IN_FREE_TALK' if 'free talk' in str(error) else 'STATE_CONFLICT'
            _error(409, code, str(error))

    return router
