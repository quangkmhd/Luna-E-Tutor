import json
from pathlib import Path

import httpx
import pytest
from luna_tutor.api import runtime
from luna_tutor.domain.state import ActivityProgress, LessonState
from luna_tutor.storage.session_repository import SessionRepository
from luna_tutor.teaching.unit_router import UnitTurnRouter


def test_database_path_is_root_relative_independent_of_service_cwd(tmp_path, monkeypatch):
    root = tmp_path / 'project'
    backend_cwd = root / 'backend'
    voice_cwd = root / 'voice' / 'server'
    backend_cwd.mkdir(parents=True)
    voice_cwd.mkdir(parents=True)
    expected = root / 'backend' / 'data' / 'luna-tutor.sqlite3'

    for cwd in (backend_cwd, voice_cwd):
        monkeypatch.chdir(cwd)
        assert runtime._resolve_database_path(
            'backend/data/luna-tutor.sqlite3', root,
        ) == expected


def test_database_path_preserves_absolute_override(tmp_path):
    absolute_path = tmp_path / 'custom.sqlite3'
    assert runtime._resolve_database_path(str(absolute_path), Path('/unrelated')) == absolute_path


def test_fixture_components_are_deterministic_and_have_repository(tmp_path):
    components = runtime.build_runtime_components(
        {
            "ENV": "test",
            "TUTOR_LLM_MODE": "fixture",
            "TUTOR_DATABASE_PATH": str(tmp_path / "voice.sqlite3"),
        }
    )

    assert isinstance(components.repository, SessionRepository)
    assert isinstance(components.turn_service, UnitTurnRouter)
    assert [
        item.id for item in components.curriculum_registry.list_units()
    ] == [
        'grade03.unit01',
        'grade05.unit01', 'grade05.unit02',
        'grade05.unit03', 'grade05.unit04', 'grade05.unit05',
    ]
    assert components.client is None


def test_live_components_require_openrouter_configuration(tmp_path):
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        runtime.build_runtime_components(
            {"TUTOR_DATABASE_PATH": str(tmp_path / "voice.sqlite3")}
        )


@pytest.mark.asyncio
async def test_live_runtime_binds_teacher_and_evaluator_prompts_to_grade(tmp_path):
    components = runtime.build_runtime_components({
        'OPENROUTER_API_KEY': 'test-key',
        'TUTOR_DATABASE_PATH': str(tmp_path / 'prompts.sqlite3'),
    })
    try:
        grade3 = components.turn_service._service('grade03.unit01')._service(1)
        grade5 = components.turn_service._service('grade05.unit01')
        assert 'Grade 3' in grade3._teacher._prompt
        assert 'Grade 3' in grade3._evaluator._prompt
        assert 'Grade 5' in grade5._teacher._prompt
        assert 'Grade 5' in grade5._planner._evaluator._prompt
        assert grade3._teacher is not grade5._teacher
    finally:
        await components.client.aclose()


def warmup_state():
    return LessonState(
        session_id='session-1', unit_id='grade05.unit01', stage_id='warm-up',
        activity_id='warm-up.feelings', last_teacher_turn='How are you today?',
        activity_progress=(
            ActivityProgress(activity_id='warm-up.hello', status='completed'),
            ActivityProgress(activity_id='warm-up.feelings', status='in_progress',
                             response_opportunity_given=True),
        ),
    )


@pytest.mark.asyncio
async def test_live_runtime_uses_jev_decisions_endpoint_when_selected(tmp_path, respx_mock):
    decision_route = respx_mock.post('https://openrouter.ai/api/alpha/decisions').mock(
        return_value=httpx.Response(200, json={
            'model': 'typesafe/jev-1.13-20260917',
            'answers': {
                'response_kind': {'type': 'choice', 'choice': 'answer'},
                'emotional_signal': {'type': 'noul', 'noul': 0.01},
                'needs_clarification': {'type': 'noul', 'noul': 0.01},
            },
        }))
    components = runtime.build_runtime_components({
        'OPENROUTER_API_KEY': 'test-key',
        'TUTOR_EVALUATOR_MODEL': '~typesafe/jev-latest',
        'TUTOR_DATABASE_PATH': str(tmp_path / 'jev.sqlite3'),
    })

    try:
        plan = await components.turn_service.plan(
            warmup_state(), 'I feel happy today.', 'turn-jev')
    finally:
        await components.client.aclose()

    assert decision_route.call_count == 1
    assert plan.evidence.response_kind == 'answer'


@pytest.mark.asyncio
async def test_live_runtime_uses_gemini_chat_endpoint_when_selected(tmp_path, respx_mock):
    result = {
        'turn_id': 'turn-gemini', 'state_version': 0, 'response_kind': 'answer',
        'emotional_signals': [], 'objective_evidence': [],
        'needs_clarification': False, 'ambiguity_reason': None,
    }
    chat_route = respx_mock.post('https://openrouter.ai/api/v1/chat/completions').mock(
        return_value=httpx.Response(200, json={
            'choices': [{'finish_reason': 'stop', 'message': {
                'content': json.dumps(result),
            }}],
        }))
    components = runtime.build_runtime_components({
        'OPENROUTER_API_KEY': 'test-key',
        'TUTOR_EVALUATOR_MODEL': 'google/gemini-3.5-flash-lite',
        'TUTOR_DATABASE_PATH': str(tmp_path / 'gemini.sqlite3'),
    })

    try:
        plan = await components.turn_service.plan(
            warmup_state(), 'I feel happy today.', 'turn-gemini')
    finally:
        await components.client.aclose()

    assert chat_route.call_count == 1
    assert plan.evidence.response_kind == 'answer'


def test_live_runtime_rejects_unknown_evaluator_model(tmp_path):
    with pytest.raises(ValueError, match='TUTOR_EVALUATOR_MODEL'):
        runtime.build_runtime_components({
            'OPENROUTER_API_KEY': 'test-key',
            'TUTOR_EVALUATOR_MODEL': 'custom/unknown-model',
            'TUTOR_DATABASE_PATH': str(tmp_path / 'invalid.sqlite3'),
        })


@pytest.mark.asyncio
async def test_review_keeps_distinct_gemini_and_jev_branches_when_live_runtime_uses_jev(
        tmp_path, respx_mock):
    decision_route = respx_mock.post('https://openrouter.ai/api/alpha/decisions').mock(
        return_value=httpx.Response(200, json={
            'model': 'typesafe/jev-1.13-20260917',
            'answers': {
                'response_kind': {'type': 'choice', 'choice': 'answer'},
                'emotional_signal': {'type': 'noul', 'noul': 0.01},
                'needs_clarification': {'type': 'noul', 'noul': 0.01},
            },
        }))

    def chat_response(request):
        payload = json.loads(request.content)
        if 'response_format' in payload:
            content = json.dumps({
                'turn_id': 'review-gemini', 'state_version': 0,
                'response_kind': 'answer', 'emotional_signals': [],
                'objective_evidence': [], 'needs_clarification': False,
                'ambiguity_reason': None,
            })
        else:
            content = 'Teacher output.'
        return httpx.Response(200, json={
            'choices': [{'finish_reason': 'stop', 'message': {'content': content}}],
        })

    chat_route = respx_mock.post(
        'https://openrouter.ai/api/v1/chat/completions').mock(side_effect=chat_response)
    components = runtime.build_runtime_components({
        'OPENROUTER_API_KEY': 'test-key',
        'TUTOR_EVALUATOR_MODEL': '~typesafe/jev-latest',
        'TUTOR_DATABASE_PATH': str(tmp_path / 'compare.sqlite3'),
    })

    try:
        result = await components.comparison_service.compare(
            warmup_state(), 'I feel happy today.', 'review')
    finally:
        await components.client.aclose()

    structured_calls = [call for call in chat_route.calls
                        if 'response_format' in json.loads(call.request.content)]
    assert decision_route.call_count == 1
    assert len(structured_calls) == 1
    assert result.gemini.evidence.turn_id == 'review-gemini'
    assert result.jev.evidence.turn_id == 'review-jev'
