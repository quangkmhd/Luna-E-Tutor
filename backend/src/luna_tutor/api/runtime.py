"""Runnable FastAPI composition root for local development and browser tests."""

from contextlib import asynccontextmanager
import os
from pathlib import Path
from typing import Mapping

from luna_tutor.api.app import create_app
from luna_tutor.config import Settings
from luna_tutor.curriculum.loader import load_unit
from luna_tutor.domain.decisions import (
    CompletedTurn, PlannedTurn, TeacherTurnRequest, TeacherUtterance,
    TeachingDecision,
)
from luna_tutor.domain.evidence import EvaluatorResult, ObjectiveEvidence
from luna_tutor.llm.evaluator import GeminiEvaluator
from luna_tutor.llm.openrouter import OpenRouterClient, ProviderError
from luna_tutor.llm.teacher import GeminiTeacher
from luna_tutor.storage.session_repository import SessionRepository
from luna_tutor.teaching.engine import TeachingEngine
from luna_tutor.teaching.planner import TurnPlanner
from luna_tutor.teaching.turn_service import TurnService
from luna_tutor.speaking.fixtures import FixtureSpeakingModels
from luna_tutor.speaking.llm import SpeakingModels
from luna_tutor.speaking.repository import SpeakingRepository
from luna_tutor.speaking.service import SpeakingService


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


def build_runtime_app(environment: Mapping[str, str] | None = None, *,
                      turn_service_adapter=None):
    environment = os.environ if environment is None else environment
    root = Path(__file__).resolve().parents[4]
    database_path = Path(environment.get(
        'TUTOR_DATABASE_PATH', str(root / 'backend/data/luna-tutor.sqlite3')))
    repository = SessionRepository(database_path)
    speaking_repository = SpeakingRepository(database_path)
    mode = environment.get('TUTOR_LLM_MODE', 'live')
    client = None
    if mode == 'fixture':
        if environment.get('ENV') != 'test':
            raise RuntimeError('TUTOR_LLM_MODE=fixture requires ENV=test')
        turn_service = FixtureTurnService()
        speaking_models = FixtureSpeakingModels()
    else:
        key = environment.get('OPENROUTER_API_KEY', '').strip()
        settings = Settings(openrouter_api_key=key)
        client = OpenRouterClient(settings)
        curriculum = load_unit(root / 'curriculum/grade-05/unit-01')
        planner = TurnPlanner(GeminiEvaluator(client), TeachingEngine(), curriculum)
        turn_service = TurnService(planner, GeminiTeacher(client))
        speaking_models = SpeakingModels(client)

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
    return create_app(repository=repository, turn_service=turn_service,
                      speaking_service=SpeakingService(speaking_repository, speaking_models),
                      speaking_repository=speaking_repository,
                      lifespan=lifespan, allowed_origins=origins)
