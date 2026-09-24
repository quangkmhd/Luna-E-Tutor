"""Production composition for Grade 3 in-memory teaching sessions."""

import os
from collections.abc import Mapping
from contextlib import asynccontextmanager
from pathlib import Path

from luna_tutor.api.lesson_api import create_lesson_api
from luna_tutor.config import Settings
from luna_tutor.curriculum.lesson_catalog import ScriptedCatalog
from luna_tutor.llm.openrouter import OpenRouterClient
from luna_tutor.llm.jev_turn_evaluator import JevTurnEvaluator, TurnEvaluation
from luna_tutor.teaching.lesson_sessions import ScriptedSessionStore
from luna_tutor.teaching.teacher_context import (
    ScriptedTeacherContext,
    build_teacher_service,
)


class _FixtureEvaluator:
    async def evaluate_turn(self, **_kwargs) -> TurnEvaluation:
        return TurnEvaluation.PASSED


class _FixtureLLM:
    async def run_inference(self, _context):
        return 'Try again.'


def build_lesson_runtime_app(environment: Mapping[str, str] | None = None):
    environment = os.environ if environment is None else environment
    root = Path(__file__).resolve().parents[4]
    catalog = ScriptedCatalog(Path(environment.get('TUTOR_CURRICULUM_ROOT', root / 'curriculum')))
    mode = environment.get('TUTOR_LLM_MODE', 'live')
    if mode == 'fixture':
        if environment.get('ENV') != 'test':
            raise RuntimeError('TUTOR_LLM_MODE=fixture requires ENV=test')
        store = ScriptedSessionStore(
            catalog, _FixtureEvaluator,
            lambda: ScriptedTeacherContext(_FixtureLLM()),
        )
        lifespan = None
    else:
        key = environment.get('OPENROUTER_API_KEY', '').strip()
        if not key:
            raise ValueError('Missing required runtime configuration: OPENROUTER_API_KEY')
        client = OpenRouterClient(Settings(openrouter_api_key=key))
        teacher_service = build_teacher_service(key)
        store = ScriptedSessionStore(
            catalog, lambda: JevTurnEvaluator(client),
            lambda: ScriptedTeacherContext(teacher_service),
        )

        @asynccontextmanager
        async def lifespan(_app):
            yield
            await client.aclose()
            await teacher_service.cleanup()

    origins = ['http://localhost:3000']
    for item in (environment.get('ALLOWED_ORIGINS') or environment.get('CORS_ORIGINS') or '').split(','):
        cleaned = item.strip()
        if cleaned and cleaned not in origins:
            origins.append(cleaned)
    return create_lesson_api(catalog, store, allowed_origins=origins, lifespan=lifespan)
