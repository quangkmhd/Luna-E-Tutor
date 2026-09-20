"""Runnable FastAPI composition root for local development and browser tests."""

import os
from collections.abc import Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from luna_tutor.api.app import create_app
from luna_tutor.config import Settings
from luna_tutor.curriculum.loader import load_unit
from luna_tutor.domain.decisions import (
    CompletedTurn,
    PlannedTurn,
    TeacherTurnRequest,
    TeacherUtterance,
    TeachingDecision,
)
from luna_tutor.domain.evidence import EvaluatorResult, ObjectiveEvidence
from luna_tutor.llm.evaluator import GeminiEvaluator
from luna_tutor.llm.jev_evaluator import JevEvaluator
from luna_tutor.llm.openrouter import OpenRouterClient, ProviderError
from luna_tutor.llm.teacher import GeminiTeacher
from luna_tutor.review.comparison import ComparisonService
from luna_tutor.storage.session_repository import SessionRepository
from luna_tutor.teaching.engine import TeachingEngine
from luna_tutor.teaching.planner import TurnPlanner
from luna_tutor.teaching.turn_service import TurnService


GEMINI_EVALUATOR_MODEL = 'google/gemini-3.5-flash-lite'
JEV_EVALUATOR_MODEL = '~typesafe/jev-latest'


def build_evaluator(model: str, client: OpenRouterClient):
    if model == GEMINI_EVALUATOR_MODEL:
        return GeminiEvaluator(client)
    if model == JEV_EVALUATOR_MODEL:
        return JevEvaluator(client)
    raise ValueError(
        'TUTOR_EVALUATOR_MODEL must be '
        f'{GEMINI_EVALUATOR_MODEL} or {JEV_EVALUATOR_MODEL}')


class FixtureTurnService:
    """Deterministic browser-test double, available only under ``ENV=test``."""

    async def process(self, state, learner_text: str, turn_id: str) -> CompletedTurn:
        if learner_text == 'fixture: provider failure':
            raise ProviderError(status_code=503, request_id=turn_id, reason='fixture failure')
        recast = learner_text.strip().lower() == 'i live countryside.'
        go_free = learner_text.strip().lower() == 'fixture: go to free talk'
        objective = state.objective_id
        evidence_items = []
        if objective:
            evidence_items.append(ObjectiveEvidence(
                objective_id=objective,
                meaning_status='satisfied',
                target_form_status='error_in_target_form' if recast else 'valid_alternative',
                evidence_quote=learner_text,
                recast_needed=recast,
                corrected_form='I live in the countryside.' if recast else None,
            ))
        evidence = EvaluatorResult(
            turn_id=turn_id, state_version=state.state_version,
            response_kind='answer', emotional_signals=[],
            objective_evidence=evidence_items, needs_clarification=False,
            ambiguity_reason=None)
        decision = TeachingDecision(
            feedback_action='recast' if recast else 'acknowledge_and_continue',
            progression_action='move_to_next_stage' if go_free else 'stay',
            corrected_form='I live in the countryside.' if recast else None,
            next_stage_id='free-talk' if go_free else None,
            next_activity_id='free-talk.conversation' if go_free else None,
        )
        request = TeacherTurnRequest(
            turn_id=turn_id, feedback_action=decision.feedback_action,
            corrected_form=decision.corrected_form, learner_meaning=learner_text,
            next_teaching_move=('Start Free Talk.' if go_free else 'Ask one short follow-up.'))
        proposed = state.model_copy(update={
            'state_version': state.state_version + 1,
            'stage_id': 'free-talk' if go_free else state.stage_id,
            'activity_id': 'free-talk.conversation' if go_free else state.activity_id,
            'objective_id': None if go_free else state.objective_id,
            'applied_turn_ids': (*state.applied_turn_ids, turn_id),
        })
        spoken = ('I live in the countryside. What do you like about it?'
                  if recast else
                  'Great, Quang! Let us have a free conversation.' if go_free
                  else 'Thank you, Quang. Tell me a little more?')
        utterance = TeacherUtterance(spoken_text=spoken, delivery_intent='encouraging')
        return CompletedTurn(
            plan=PlannedTurn(
                turn_id=turn_id, state_version=state.state_version,
                learner_text=learner_text, privacy_event=False, evidence=evidence,
                decision=decision, teacher_request=request,
                proposed_next_state=proposed),
            teacher_utterance=utterance,
            next_state=proposed.model_copy(update={'last_teacher_turn': spoken}),
        )


@dataclass(frozen=True)
class RuntimeComponents:
    repository: SessionRepository
    turn_service: object
    client: OpenRouterClient | None
    comparison_service: object | None = None


def build_runtime_components(environment: Mapping[str, str]) -> RuntimeComponents:
    root = Path(__file__).resolve().parents[4]
    database_path = Path(environment.get(
        'TUTOR_DATABASE_PATH', str(root / 'backend/data/luna-tutor.sqlite3')))
    repository = SessionRepository(database_path)
    mode = environment.get('TUTOR_LLM_MODE', 'live')
    if mode == 'fixture':
        if environment.get('ENV') != 'test':
            raise RuntimeError('TUTOR_LLM_MODE=fixture requires ENV=test')
        return RuntimeComponents(repository, FixtureTurnService(), None, None)

    key = environment.get('OPENROUTER_API_KEY', '').strip()
    if not key:
        raise ValueError('Missing required runtime configuration: OPENROUTER_API_KEY')
    evaluator_model = environment.get(
        'TUTOR_EVALUATOR_MODEL', GEMINI_EVALUATOR_MODEL).strip()
    if evaluator_model not in {GEMINI_EVALUATOR_MODEL, JEV_EVALUATOR_MODEL}:
        raise ValueError(
            'TUTOR_EVALUATOR_MODEL must be '
            f'{GEMINI_EVALUATOR_MODEL} or {JEV_EVALUATOR_MODEL}')
    settings = Settings(openrouter_api_key=key)
    client = OpenRouterClient(settings)
    evaluator = build_evaluator(evaluator_model, client)
    curriculum = load_unit(root / 'curriculum/grade-05/unit-01')
    teacher = GeminiTeacher(client)
    planner = TurnPlanner(evaluator, TeachingEngine(), curriculum)
    turn_service = TurnService(planner, teacher)
    gemini_turn_service = (turn_service if evaluator_model == GEMINI_EVALUATOR_MODEL else
                           TurnService(TurnPlanner(
                               GeminiEvaluator(client), TeachingEngine(), curriculum), teacher))
    jev_turn_service = (turn_service if evaluator_model == JEV_EVALUATOR_MODEL else
                        TurnService(TurnPlanner(
                            JevEvaluator(client), TeachingEngine(), curriculum), teacher))
    comparison_service = ComparisonService(gemini_turn_service, jev_turn_service)
    return RuntimeComponents(repository, turn_service, client, comparison_service)


def build_runtime_app(environment: Mapping[str, str] | None = None, *,
                      turn_service_adapter=None):
    environment = os.environ if environment is None else environment
    components = build_runtime_components(environment)
    repository = components.repository
    turn_service = components.turn_service
    client = components.client
    comparison_service = components.comparison_service

    if turn_service_adapter is not None:
        turn_service = turn_service_adapter(turn_service)

    @asynccontextmanager
    async def lifespan(_app):
        yield
        if client is not None:
            await client.aclose()

    origins = ['http://localhost:3000']
    if environment.get('ENV') == 'test':
        origins.append('http://localhost:3090')
        if e2e_web_origin := environment.get('E2E_WEB_ORIGIN', '').strip():
            origins.append(e2e_web_origin)
    return create_app(repository=repository, turn_service=turn_service,
                      comparison_service=comparison_service,
                      lifespan=lifespan, allowed_origins=origins)
