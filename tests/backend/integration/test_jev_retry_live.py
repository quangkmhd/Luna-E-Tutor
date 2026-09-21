"""Opt-in checks against the evaluator model used by the local backend."""

import os
from pathlib import Path

import pytest

from luna_tutor.config import Settings
from luna_tutor.curriculum.loader import load_unit
from luna_tutor.domain.evidence import ActiveObjective, EvaluatorRequest
from luna_tutor.domain.state import ActivityProgress, LessonState
from luna_tutor.llm.jev_evaluator import JevEvaluator
from luna_tutor.llm.openrouter import OpenRouterClient
from luna_tutor.llm.teacher import GeminiTeacher
from luna_tutor.teaching.engine import TeachingEngine
from luna_tutor.teaching.planner import TurnPlanner


pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(
    os.getenv('RUN_LIVE_LLM') != '1', reason='Set RUN_LIVE_LLM=1 for live Jev checks')]


def _active_objective(curriculum, objective_id):
    objective = next(item for item in curriculum.objectives if item.id == objective_id)
    patterns = {item.id: item for item in curriculum.patterns}
    words = {item.id: item for item in curriculum.vocabulary}
    return ActiveObjective(
        objective_id=objective.id, communicative_goal=objective.description,
        evidence_criteria=objective.evidence_criteria,
        target_patterns=[patterns[item].text for item in objective.pattern_ids],
        acceptable_alternatives=[alternative for item in objective.pattern_ids
                                 for alternative in patterns[item].acceptable_alternatives],
        target_words=[words[item].text for item in objective.vocabulary_ids],
    )


@pytest.mark.parametrize(('objective_id', 'activity_type', 'teacher_turn',
                          'learner_text', 'meaning', 'form'), [
    ('unit01.lesson01.vocabulary.city', 'vocabulary_introduction',
     'Can you say “city”?', 'cidy', 'not_demonstrated', 'error_in_target_form'),
    ('unit01.lesson01.pattern.live_in', 'guided_response',
     'Where do you live?', 'I live countryside.', 'satisfied', 'error_in_target_form'),
    ('unit01.lesson02.pattern.favourite', 'guided_response',
     'What is your favourite animal?', 'My favourite animal is pink.',
     'wrong_semantic_category', 'error_in_target_form'),
    ('unit01.lesson01.vocabulary.city', 'comprehension',
     'Which place has tall buildings: city or countryside?', 'Countryside.',
     'wrong_semantic_category', 'not_used'),
], ids=['wrong-vocabulary', 'wrong-grammar', 'wrong-word-in-sentence',
        'wrong-sentence-meaning'])
async def test_live_jev_distinguishes_four_failed_attempts(
        objective_id, activity_type, teacher_turn, learner_text, meaning, form):
    curriculum = load_unit(Path(__file__).resolve().parents[3]
                           / 'curriculum/grade-05/unit-01')
    request = EvaluatorRequest(
        turn_id='live-' + objective_id, unit_id=curriculum.id, state_version=0,
        teacher_turn=teacher_turn, activity_type=activity_type,
        active_objectives=[_active_objective(curriculum, objective_id)],
        support_given={}, transcript_status='final', learner_transcript=learner_text,
    )
    async with OpenRouterClient(Settings.from_env()) as client:
        result = await JevEvaluator(client).evaluate(request)
    item = result.objective_evidence[0]
    assert result.response_kind == 'answer'
    assert item.meaning_status == meaning
    assert item.target_form_status == form


async def test_live_teacher_asks_to_repeat_mispronounced_city():
    curriculum = load_unit(Path(__file__).resolve().parents[3]
                           / 'curriculum/grade-05/unit-01')
    activity_id = 'lesson-01.introduce-city'
    objective_id = 'unit01.lesson01.vocabulary.city'
    state = LessonState(
        session_id='live-retry', unit_id=curriculum.id, stage_id='lesson-01',
        activity_id=activity_id, objective_id=objective_id,
        last_teacher_turn='Can you say “city”?',
        activity_progress=(ActivityProgress(
            activity_id=activity_id, status='in_progress',
            model_repetitions_delivered=2, response_opportunity_given=True),),
    )
    async with OpenRouterClient(Settings.from_env()) as client:
        plan = await TurnPlanner(JevEvaluator(client), TeachingEngine(), curriculum).plan(
            state, 'cidy', 'live-retry-city')
        assert plan.teacher_request.constraints.require_repetition
        utterance = await GeminiTeacher(client).respond(plan.teacher_request)
    text = utterance.spoken_text.lower()
    assert 'city' in text
    assert any(phrase in text for phrase in ('try again', 'say', 'one more time'))
    assert 'yes, city' not in text
    assert 'noisy or quiet' not in text


@pytest.mark.parametrize(('word', 'activity_id', 'objective_id'), [
    ('city', 'lesson-01.introduce-city', 'unit01.lesson01.vocabulary.city'),
    ('class', 'lesson-01.introduce-class', 'unit01.lesson01.vocabulary.class'),
])
async def test_live_exact_word_imitation_moves_on_without_failure_language(
        word, activity_id, objective_id):
    curriculum = load_unit(Path(__file__).resolve().parents[3]
                           / 'curriculum/grade-05/unit-01')
    prior = tuple(ActivityProgress(activity_id=item.id, status='completed')
                  for item in curriculum.activities if item.stage_id == 'lesson-01'
                  and item.id == 'lesson-01.introduce-city' and item.id != activity_id)
    state = LessonState(
        session_id='live-word', unit_id=curriculum.id, stage_id='lesson-01',
        activity_id=activity_id, objective_id=objective_id,
        last_teacher_turn=f'Can you say “{word}”?',
        activity_progress=prior + (ActivityProgress(
            activity_id=activity_id, status='in_progress',
            model_repetitions_delivered=2, response_opportunity_given=True),),
    )
    async with OpenRouterClient(Settings.from_env()) as client:
        plan = await TurnPlanner(JevEvaluator(client), TeachingEngine(), curriculum).plan(
            state, word, f'live-exact-{word}')
        assert plan.decision.feedback_action == 'acknowledge_and_continue'
        assert not plan.decision.support_limit_exit
        utterance = await GeminiTeacher(client).respond(plan.teacher_request)
    spoken = utterance.spoken_text.lower()
    assert 'try again' not in spoken
    assert 'no worries' not in spoken
    assert 'that is alright' not in spoken
