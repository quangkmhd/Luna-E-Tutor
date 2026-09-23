from uuid import uuid4

from fastapi import APIRouter, HTTPException

from luna_tutor.api.schemas import (
    CreateSessionRequest,
    LearningStageFocusView,
    LessonView,
    MessageView,
    ReviewRequest,
    SessionView,
    SummaryView,
    TurnRequest,
    TurnResponse,
    UnitView,
    VocabularyCardView,
    VersionRequest,
)
from luna_tutor.curriculum.registry import UnknownUnitError
from luna_tutor.teaching.scripted_lesson import ScriptedLessonService
from luna_tutor.domain.state import ActivityProgress, LessonState
from luna_tutor.llm.openrouter import InvalidModelOutputError, ProviderError
from luna_tutor.llm.teacher import InvalidTeacherResultError
from luna_tutor.review.comparison import ComparisonResult
from luna_tutor.storage.session_repository import (
    SessionNotFoundError,
    StateConflictError,
    StoredSession,
)
from luna_tutor.speech.language_segments import plain_speech_text

LEGACY_GREETING = "Hello, Quang! I'm Luna. It's lovely to see you today!"


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
    review.extend(item.objective_id for item in stored.state.review_queue
                  if item.objective_id not in review)
    observed = set(demonstrated + supported + review)
    return SummaryView(demonstrated=demonstrated, supported=supported,
                       needs_review=review,
                       not_yet_observed=[] if observed else ['No learning evidence recorded yet'])


def _learning_focus(curriculum, current_stage_id: str) -> list[LearningStageFocusView]:
    stage_positions = {stage.id: index for index, stage in enumerate(curriculum.stages)}
    current_position = stage_positions[current_stage_id]
    candidates = []
    for stage in curriculum.stages:
        if stage.id in {'warm-up', 'free-talk', 'summary'}:
            continue
        objective_ids = {
            objective_id
            for activity in curriculum.activities
            if activity.stage_id == stage.id
            for objective_id in activity.objective_ids
        }
        objectives = [item for item in curriculum.objectives if item.id in objective_ids]
        vocabulary_ids = {
            vocabulary_id for objective in objectives
            for vocabulary_id in objective.vocabulary_ids
        }
        pattern_ids = {
            pattern_id for objective in objectives
            for pattern_id in objective.pattern_ids
        }
        target_words = [
            item.text for item in curriculum.vocabulary if item.id in vocabulary_ids
        ]
        target_patterns = [
            item.text for item in curriculum.patterns if item.id in pattern_ids
        ]
        if target_words or target_patterns:
            candidates.append((stage, target_words, target_patterns))

    highlighted_stage_id = current_stage_id if any(
        stage.id == current_stage_id for stage, _, _ in candidates
    ) else next((
        stage.id for stage, _, _ in candidates
        if stage_positions[stage.id] > current_position
    ), None)

    return [
        LearningStageFocusView(
            stage_id=stage.id,
            stage_title=stage.title,
            target_words=target_words,
            target_patterns=target_patterns,
            highlighted=stage.id == highlighted_stage_id,
        )
        for stage, target_words, target_patterns in candidates
    ]


def session_view(stored: StoredSession, curriculum_registry) -> SessionView:
    state = stored.state
    curriculum = curriculum_registry.get(state.unit_id)
    script = curriculum_registry.get_lesson_script(state.unit_id, state.lesson_id) if state.lesson_id is not None else None
    opening_image = script.image_for_activity(state.activity_id) if script else None
    messages = [MessageView(role='teacher', text=plain_speech_text(state.opening_message or LEGACY_GREETING),
                            image_url=opening_image)]
    if stored.state.opening_script:
        messages.append(MessageView(role='teacher', text=plain_speech_text(stored.state.opening_script),
                                    image_url=opening_image))
    for completed in stored.turns:
        next_activity_id = completed.plan.proposed_next_state.activity_id
        if script:
            image_url = script.image_for_activity(next_activity_id)
        else:
            next_activity = next((item for item in curriculum.activities
                                  if item.id == next_activity_id), None)
            image_url = next_activity.image_url if next_activity else None
        messages.extend([
            MessageView(role='learner', text=completed.plan.learner_text,
                        turn_id=completed.plan.turn_id),
            MessageView(role='teacher', text=plain_speech_text(completed.teacher_utterance.spoken_text),
                        turn_id=completed.plan.turn_id,
                        delivery_intent=completed.teacher_utterance.delivery_intent,
                        image_url=image_url),
        ])
    last = stored.turns[-1] if stored.turns else None
    if state.closing_message:
        messages.append(MessageView(role='teacher', text=plain_speech_text(state.closing_message),
                                    delivery_intent='warm'))
    if state.lesson_id is None:
        focus = _learning_focus(curriculum, state.stage_id)
    else:
        focus = [LearningStageFocusView(
            stage_id=station.id,
            stage_title={'vocabulary': 'Trạm 1 · Từ vựng',
                         'patterns': 'Trạm 2 · Mẫu câu',
                         'conversation': 'Trạm 3 · Hội thoại'}[station.id],
            target_words=list(dict.fromkeys(
                target for step in station.steps
                for target in ([step.target] if isinstance(step.target, str) else step.target or [])
                if target in script.words)),
            target_patterns=list(dict.fromkeys(
                script.patterns[target] for step in station.steps
                for target in ([step.target] if isinstance(step.target, str) else step.target or [])
                if target in script.patterns)),
            highlighted=station.id == state.stage_id or (
                state.stage_id == 'greeting' and station.id == 'vocabulary'),
        ) for station in script.stations]
    active_words = list(dict.fromkeys(
        word for item in focus if item.highlighted for word in item.target_words
    ))
    card_by_word = {item.text: item for item in curriculum.vocabulary}
    if script:
        card_by_word.update({card.word: card for card in script.cards})
        active_words = [word for word in active_words if word in card_by_word]
    else:
        active_words = [word for word in active_words if word in card_by_word and (
            card_by_word[word].image_url or card_by_word[word].meaning_vi
            or card_by_word[word].pronunciation
        )]
    vocabulary_text_by_id = {item.id: item.text for item in curriculum.vocabulary}
    objectives_by_word = {
        vocabulary_text_by_id[word]: objective.id
        for objective in curriculum.objectives
        for word in objective.vocabulary_ids if word in vocabulary_text_by_id
    }
    if script:
        for step in script.steps():
            target_exchanges = (step, *step.more)
            for exchange_index, exchange in enumerate(target_exchanges, start=1):
                selected = ([step.target] if isinstance(step.target, str) else step.target or [])
                for word in selected:
                    if word in script.words:
                        objectives_by_word[word] = (
                            f'lesson-{step.order:02d}.objective-{exchange_index:02d}'
                        )
    progress_by_id = {item.objective_id: item for item in state.objective_progress}
    flashcards = []
    for word in active_words:
        card = card_by_word.get(word)
        objective = progress_by_id.get(objectives_by_word.get(word, ''))
        status = ('learned' if objective and objective.independent_uses else
                  'learning' if objective and (objective.supported_uses or objective.attempted) else 'new')
        flashcards.append(VocabularyCardView(
            word=word,
            pronunciation=card.pronunciation if card else None,
            meaning_vi=card.meaning_vi if card else None,
            image_url=card.image_url if card else None,
            status=status,
        ))
    return SessionView(
        session_id=state.session_id, unit_id=state.unit_id, lesson_id=state.lesson_id,
        unit=UnitView(
            id=curriculum.id, grade=curriculum.grade,
            unit=curriculum.unit, title=curriculum.title,
        ),
        state_version=state.state_version, stage_id=state.stage_id,
        activity_id=state.activity_id, objective_id=state.objective_id,
        learning_focus=focus,
        flashcards=flashcards,
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


def _fresh_state(curriculum) -> LessonState:
    feelings = next(
        activity for activity in curriculum.activities
        if activity.stage_id == 'warm-up' and activity.kind == 'emotion_check'
    )
    greeting = next(
        activity for activity in curriculum.activities
        if activity.stage_id == 'warm-up' and activity.kind == 'greeting'
    )
    return LessonState(
        session_id=str(uuid4()), unit_id=curriculum.id, stage_id='warm-up',
        activity_id=feelings.id, last_teacher_turn=curriculum.greeting,
        opening_message=curriculum.greeting,
        activity_progress=(ActivityProgress(
            activity_id=greeting.id, status='completed'),
            ActivityProgress(activity_id=feelings.id, status='in_progress',
                             response_opportunity_given=True)))


def build_router(
        repository, turn_service, curriculum_registry,
        comparison_service=None) -> APIRouter:
    router = APIRouter(prefix='/api')

    def view(stored):
        try:
            return session_view(stored, curriculum_registry)
        except UnknownUnitError:
            _error(
                500, 'UNKNOWN_STORED_UNIT',
                f'Session references unavailable curriculum {stored.state.unit_id}.',
            )

    @router.get('/units', response_model=list[UnitView])
    async def list_units():
        return [
            UnitView(id=item.id, grade=item.grade, unit=item.unit, title=item.title)
            for item in curriculum_registry.list_units()
        ]

    @router.get('/units/{unit_id}/lessons', response_model=list[LessonView])
    async def list_lessons(unit_id: str):
        try:
            curriculum_registry.get(unit_id)
        except UnknownUnitError:
            _error(404, 'UNKNOWN_UNIT', f'Unknown curriculum unit {unit_id}.')
        return [LessonView(lesson=script.lesson, title=script.title)
                for script in curriculum_registry.list_lesson_scripts(unit_id)]

    @router.post('/sessions', response_model=SessionView)
    async def create_session(request: CreateSessionRequest):
        try:
            curriculum = curriculum_registry.get(request.unit_id)
        except UnknownUnitError:
            _error(400, 'UNKNOWN_UNIT', f'Unknown curriculum unit {request.unit_id}.')
        if request.unit_id == 'grade03.unit01':
            try:
                script = curriculum_registry.get_lesson_script(
                    request.unit_id, request.lesson_id or 1)
            except UnknownUnitError:
                _error(400, 'UNKNOWN_LESSON', 'Unknown lesson for this unit.')
            state = ScriptedLessonService(script, None, None).fresh_state(str(uuid4()))
        else:
            if request.lesson_id is not None:
                _error(400, 'UNKNOWN_LESSON', 'This unit does not use lesson selection.')
            state = _fresh_state(curriculum)
        return view(repository.create_session(state))

    @router.post('/sessions/reset', response_model=SessionView)
    async def reset_session(request: CreateSessionRequest):
        try:
            curriculum = curriculum_registry.get(request.unit_id)
        except UnknownUnitError:
            _error(400, 'UNKNOWN_UNIT', f'Unknown curriculum unit {request.unit_id}.')
        if request.unit_id == 'grade03.unit01':
            try:
                script = curriculum_registry.get_lesson_script(
                    request.unit_id, request.lesson_id or 1)
            except UnknownUnitError:
                _error(400, 'UNKNOWN_LESSON', 'Unknown lesson for this unit.')
            state = ScriptedLessonService(script, None, None).fresh_state(str(uuid4()))
        else:
            if request.lesson_id is not None:
                _error(400, 'UNKNOWN_LESSON', 'This unit does not use lesson selection.')
            state = _fresh_state(curriculum)
        return view(repository.replace_with_session(state))

    @router.get('/sessions', response_model=list[SessionView])
    async def list_sessions():
        return [view(item) for item in repository.list_sessions()]

    @router.get('/sessions/{session_id}', response_model=SessionView)
    async def get_session(session_id: str):
        try:
            return view(repository.get_session(session_id))
        except SessionNotFoundError:
            _error(404, 'SESSION_NOT_FOUND', 'Session was not found.')

    @router.post('/sessions/{session_id}/turns', response_model=TurnResponse)
    async def submit_turn(session_id: str, request: TurnRequest):
        existing = repository.get_turn(session_id, request.turn_id)
        if existing is not None:
            return TurnResponse(turn_id=request.turn_id,
                                session=view(repository.get_session(session_id)))
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
                                session=view(repository.get_session(session_id)))
        except SessionNotFoundError:
            _error(404, 'SESSION_NOT_FOUND', 'Session was not found.')
        except StateConflictError:
            _error(409, 'STATE_CONFLICT', 'Session state has changed.')
        except InvalidTeacherResultError:
            _error(503, 'INVALID_TEACHER_OUTPUT', 'The tutor could not prepare a reply. Please retry.', True)
        except InvalidModelOutputError:
            _error(503, 'INVALID_EVALUATION', 'The tutor could not assess that turn.', True)
        except ProviderError:
            _error(503, 'PROVIDER_UNAVAILABLE', 'The tutor service is temporarily unavailable.', True)
        except UnknownUnitError:
            _error(
                500, 'UNKNOWN_STORED_UNIT',
                f'Session references unavailable curriculum {stored.state.unit_id}.',
            )

    @router.post('/sessions/{session_id}/abandon', response_model=SessionView)
    async def abandon(session_id: str):
        try:
            return view(repository.abandon_session(session_id))
        except SessionNotFoundError:
            _error(404, 'SESSION_NOT_FOUND', 'Session was not found.')

    @router.post('/sessions/{session_id}/finish', response_model=SessionView)
    async def finish(session_id: str, request: VersionRequest):
        try:
            return view(repository.finish_free_talk(
                session_id, request.expected_state_version))
        except SessionNotFoundError:
            _error(404, 'SESSION_NOT_FOUND', 'Session was not found.')
        except StateConflictError as error:
            code = 'NOT_IN_FREE_TALK' if 'free talk' in str(error) else 'STATE_CONFLICT'
            _error(409, code, str(error))

    if comparison_service is not None:
        @router.post('/review/{session_id}', response_model=ComparisonResult)
        async def compare_evaluators(session_id: str, request: ReviewRequest):
            try:
                stored = repository.get_session(session_id)
                return await comparison_service.compare(
                    stored.state, request.learner_text, str(uuid4()))
            except SessionNotFoundError:
                _error(404, 'SESSION_NOT_FOUND', 'Session was not found.')
            except InvalidTeacherResultError:
                _error(503, 'INVALID_TEACHER_OUTPUT',
                       'The tutor could not prepare a comparison reply. Please retry.', True)
            except InvalidModelOutputError:
                _error(503, 'INVALID_EVALUATION',
                       'One evaluator could not assess that turn.', True)
            except ProviderError:
                _error(503, 'PROVIDER_UNAVAILABLE',
                       'The tutor service is temporarily unavailable.', True)
            except UnknownUnitError:
                _error(
                    500, 'UNKNOWN_STORED_UNIT',
                    f'Session references unavailable curriculum {stored.state.unit_id}.',
                )

    return router
