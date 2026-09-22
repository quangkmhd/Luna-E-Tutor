from pathlib import Path
import shutil

import yaml

import pytest

from luna_tutor.curriculum.loader import load_unit
from luna_tutor.domain.evidence import EvaluatorResult, ObjectiveEvidence
from luna_tutor.domain.state import LessonState
from luna_tutor.domain.state import ActivityProgress
from luna_tutor.teaching.engine import TeachingEngine
from luna_tutor.teaching.planner import TurnPlanner
from luna_tutor.domain.decisions import TeachingDecision


ROOT = Path(__file__).resolve().parents[4]


def test_learner_repetitions_can_be_overridden_in_any_unit_yaml(tmp_path):
    root = tmp_path / 'unit-01'
    shutil.copytree(ROOT / 'curriculum/grade-03/unit-01', root)
    path = root / 'lesson-01/legacy.yaml'
    document = yaml.safe_load(path.read_text(encoding='utf-8'))
    hello = next(item for item in document['activities']
                 if item['id'] == 'lesson-01.introduce-hello')
    hello['completion_rule']['learner_repetitions'] = 2
    path.write_text(yaml.safe_dump(document, allow_unicode=True), encoding='utf-8')

    unit = load_unit(root)
    assert next(item for item in unit.activities
                if item.id == 'lesson-01.introduce-hello').required_learner_repetitions == 2
    assert next(item for item in unit.activities
                if item.id == 'lesson-01.introduce-hi').required_learner_repetitions == 3

    objective = 'unit01.lesson01.vocabulary.hello'
    evidence = EvaluatorResult(
        turn_id='configured', state_version=0, response_kind='answer',
        emotional_signals=[], objective_evidence=[ObjectiveEvidence(
            objective_id=objective, meaning_status='not_demonstrated',
            target_form_status='correct_target_form', evidence_quote='hello',
            recast_needed=False, corrected_form=None)],
        needs_clarification=False, ambiguity_reason=None,
    )
    state = LessonState(
        session_id='configured', unit_id=unit.id, stage_id='lesson-01',
        activity_id='lesson-01.introduce-hello', objective_id=objective,
        activity_progress=(ActivityProgress(
            activity_id='lesson-01.introduce-hello', status='in_progress',
            model_repetitions_delivered=2, response_opportunity_given=True,
            successful_learner_repetitions=1),),
    )
    assert TeachingEngine().decide(state, evidence, unit, learner_text='hello').next_activity_id == 'lesson-01.introduce-hi'


@pytest.mark.asyncio
async def test_vocabulary_requires_three_successful_learner_turns_by_default():
    unit = load_unit(ROOT / 'curriculum/grade-03/unit-01')
    objective = 'unit01.lesson01.vocabulary.hello'
    state = LessonState(
        session_id='three-hellos', unit_id=unit.id, stage_id='lesson-01',
        activity_id='lesson-01.introduce-hello', objective_id=objective,
        last_teacher_turn='Can you say Hello?',
        activity_progress=(ActivityProgress(
            activity_id='lesson-01.introduce-hello', status='in_progress',
            model_repetitions_delivered=2, response_opportunity_given=True),),
    )

    class Evaluator:
        async def evaluate(self, request):
            return EvaluatorResult(
                turn_id=request.turn_id, state_version=request.state_version,
                response_kind='answer', emotional_signals=[],
                objective_evidence=[ObjectiveEvidence(
                    objective_id=objective, meaning_status='not_demonstrated',
                    target_form_status='correct_target_form',
                    evidence_quote='hello', recast_needed=False,
                    corrected_form=None)],
                needs_clarification=False, ambiguity_reason=None,
            )

    planner = TurnPlanner(Evaluator(), TeachingEngine(), unit)
    for turn_number in (1, 2, 3):
        plan = await planner.plan(state, 'hello', f'hello-{turn_number}')
        assert plan.decision.count_successful_repetition
        progress = next(item for item in plan.proposed_next_state.activity_progress
                        if item.activity_id == state.activity_id)
        assert progress.successful_learner_repetitions == turn_number
        if turn_number < 3:
            assert plan.decision.progression_action == 'stay'
            assert not plan.decision.count_attempt
            assert 'invite another learner turn' in plan.teacher_request.next_teaching_move
            assert plan.teacher_request.constraints.require_repetition
        else:
            assert plan.decision.next_activity_id == 'lesson-01.introduce-hi'
        state = plan.proposed_next_state.model_copy(update={
            'last_teacher_turn': f'Please say hello again, turn {turn_number}.'})


@pytest.mark.asyncio
async def test_exact_final_word_resolves_conflicting_unclear_evaluator_result():
    unit = load_unit(ROOT / 'curriculum/grade-03/unit-01')
    objective = 'unit01.lesson01.vocabulary.hello'
    state = LessonState(
        session_id='exact-word', unit_id=unit.id, stage_id='lesson-01',
        activity_id='lesson-01.introduce-hello', objective_id=objective,
        last_teacher_turn='Say hello again.',
        activity_progress=(ActivityProgress(
            activity_id='lesson-01.introduce-hello', status='in_progress',
            model_repetitions_delivered=2, response_opportunity_given=True,
            successful_learner_repetitions=2),),
    )

    class ConflictingEvaluator:
        async def evaluate(self, request):
            return EvaluatorResult(
                turn_id=request.turn_id, state_version=request.state_version,
                response_kind='insufficient_data', emotional_signals=[],
                objective_evidence=[ObjectiveEvidence(
                    objective_id=objective, meaning_status='not_demonstrated',
                    target_form_status='correct_target_form', evidence_quote='hello',
                    recast_needed=False, corrected_form=None)],
                needs_clarification=True, ambiguity_reason='Unclear input.',
            )

    planner = TurnPlanner(ConflictingEvaluator(), TeachingEngine(), unit)
    final = await planner.plan(state, 'hello', 'exact-final')
    uncertain = await planner.plan(state, 'hello', 'uncertain-audio',
                                   transcript_status='uncertain')

    assert final.decision.next_activity_id == 'lesson-01.introduce-hi'
    assert final.decision.count_successful_repetition
    assert uncertain.decision.feedback_action == 'clarify'


def test_hello_lesson_script_reaches_teacher_move():
    unit = load_unit(ROOT / 'curriculum/grade-03/unit-01')
    planner = TurnPlanner(None, TeachingEngine(), unit)
    current = next(item for item in unit.activities if item.id == 'warm-up.feelings')
    move = planner._next_move_text(current, TeachingDecision(
        feedback_action='acknowledge_and_continue',
        progression_action='move_to_next_stage',
        next_activity_id='lesson-01.introduce-hello',
        next_stage_id='lesson-01',
        next_objective_id='unit01.lesson01.vocabulary.hello',
    ))

    assert 'Cô trò mình sang Trạm 1' in move
    assert 'Listen first! [long pause] HELLO.' in move
    assert 'Your turn now! Can you say: [long pause] Hello?' in move


def test_lesson_one_moves_from_pattern_practice_to_good_evening():
    unit = load_unit(ROOT / 'curriculum/grade-03/unit-01')
    assert not any(item.id == 'lesson-01.ask-luna' for item in unit.activities)
    assert not any(item.id == 'level-02.introduce-good-evening' for item in unit.activities)
    objective = 'unit01.lesson01.pattern.pattern_hello_hi_i_m_2'
    prior = tuple(ActivityProgress(activity_id=item.id, status='completed')
                  for item in unit.activities
                  if item.stage_id == 'lesson-01' and item.id not in {
                      'lesson-01.practice-02', 'lesson-01.introduce-good-evening'})
    state = LessonState(
        session_id='to-good-evening', unit_id=unit.id, stage_id='lesson-01',
        activity_id='lesson-01.practice-02', objective_id=objective,
        last_teacher_turn="Can you say Hi, Quang. I'm Luna?",
        activity_progress=prior + (ActivityProgress(
            activity_id='lesson-01.practice-02', status='in_progress',
            response_opportunity_given=True),),
    )
    evidence = EvaluatorResult(
        turn_id='practice-done', state_version=0, response_kind='answer',
        emotional_signals=[], objective_evidence=[ObjectiveEvidence(
            objective_id=objective, meaning_status='satisfied',
            target_form_status='correct_target_form', evidence_quote="Hi, Luna. I'm Quang.",
            recast_needed=False, corrected_form=None)],
        needs_clarification=False, ambiguity_reason=None,
    )
    decision = TeachingEngine().decide(state, evidence, unit, learner_text="Hi, Luna. I'm Quang.")
    assert decision.next_activity_id == 'lesson-01.introduce-good-evening'
    target = next(item for item in unit.activities if item.id == decision.next_activity_id)
    assert 'Good evening là chào buổi tối' in target.instruction
    assert 'Listen first! [long pause] GOOD EVENING.' in target.instruction
    assert 'Your turn now! Good evening!' in target.instruction
    current = next(item for item in unit.activities if item.id == state.activity_id)
    move = TurnPlanner(None, TeachingEngine(), unit)._next_move_text(current, decision)
    assert 'Good evening là chào buổi tối' in move
    assert 'Do not ask Quang to ask Luna a question here.' in move


def test_good_evening_moves_to_nice_to_meet_you():
    unit = load_unit(ROOT / 'curriculum/grade-03/unit-01')
    assert not any(item.id == 'level-02.introduce-nice-to-meet-you'
                   for item in unit.activities)
    objective = 'unit01.level02.vocabulary.good_evening'
    prior = tuple(ActivityProgress(activity_id=item.id, status='completed')
                  for item in unit.activities if item.stage_id == 'lesson-01'
                  and item.id not in {'lesson-01.introduce-good-evening',
                                      'lesson-01.introduce-nice-to-meet-you'})
    state = LessonState(
        session_id='to-nice-to-meet-you', unit_id=unit.id, stage_id='lesson-01',
        activity_id='lesson-01.introduce-good-evening', objective_id=objective,
        last_teacher_turn='Your turn now! Good evening!',
        activity_progress=prior + (ActivityProgress(
            activity_id='lesson-01.introduce-good-evening', status='in_progress',
            model_repetitions_delivered=2, response_opportunity_given=True,
            successful_learner_repetitions=2),),
    )
    evidence = EvaluatorResult(
        turn_id='evening-done', state_version=0, response_kind='answer',
        emotional_signals=[], objective_evidence=[ObjectiveEvidence(
            objective_id=objective, meaning_status='not_demonstrated',
            target_form_status='correct_target_form', evidence_quote='good evening',
            recast_needed=False, corrected_form=None)],
        needs_clarification=False, ambiguity_reason=None,
    )
    decision = TeachingEngine().decide(state, evidence, unit, learner_text='good evening')
    assert decision.next_activity_id == 'lesson-01.introduce-nice-to-meet-you'
    current = next(item for item in unit.activities if item.id == state.activity_id)
    move = TurnPlanner(None, TeachingEngine(), unit)._next_move_text(current, decision)
    assert 'Khi gặp ai LẦN ĐẦU' in move
    assert 'Listen first! [long pause] NICE TO MEET YOU.' in move
    assert 'Your turn now! Nice to meet you!' in move


@pytest.mark.asyncio
async def test_correct_im_response_to_im_model_is_acknowledged_without_using_pattern_attempt():
    unit = load_unit(ROOT / 'curriculum/grade-03/unit-01')
    objective = 'unit01.lesson01.pattern.pattern_hello_hi_i_m'
    previous = next(item.instruction for item in unit.activities
                    if item.id == 'lesson-01.practice-01')
    state = LessonState(
        session_id='im-model', unit_id=unit.id, stage_id='lesson-01',
        activity_id='lesson-01.practice-01', objective_id=objective,
        last_teacher_turn=previous,
        activity_progress=(ActivityProgress(
            activity_id='lesson-01.practice-01', status='in_progress',
            response_opportunity_given=True),),
    )

    class Evaluator:
        async def evaluate(self, request):
            return EvaluatorResult(
                turn_id=request.turn_id, state_version=request.state_version,
                response_kind='answer', emotional_signals=[],
                objective_evidence=[ObjectiveEvidence(
                    objective_id=objective, meaning_status='not_demonstrated',
                    target_form_status='correct_target_form', evidence_quote="I'm",
                    recast_needed=False, corrected_form=None)],
                needs_clarification=False, ambiguity_reason=None,
            )

    plan = await TurnPlanner(Evaluator(), TeachingEngine(), unit).plan(
        state, "I'm", 'im-correct')
    assert plan.decision.feedback_action == 'acknowledge_and_continue'
    assert plan.decision.progression_action == 'stay'
    assert not plan.decision.count_attempt
    assert not plan.teacher_request.constraints.require_repetition
    assert 'target pattern in activity_context' in plan.teacher_request.next_teaching_move
    assert 'Hello./Hi. I\'m ___.' in plan.teacher_request.activity_context.target_patterns


@pytest.mark.asyncio
async def test_untracked_first_form_error_uses_correction_guidance():
    unit = load_unit(ROOT / 'curriculum/grade-03/unit-01')
    objective = 'unit01.lesson01.pattern.pattern_hello_hi_i_m_2'
    state = LessonState(
        session_id='grade3-form', unit_id=unit.id, stage_id='lesson-01',
        activity_id='lesson-01.practice-02', objective_id=objective,
        last_teacher_turn='You can say, hi, i am quang.',
    )
    evidence = EvaluatorResult(
        turn_id='t1', state_version=0, response_kind='answer',
        emotional_signals=[], objective_evidence=[ObjectiveEvidence(
            objective_id=objective, meaning_status='satisfied',
            target_form_status='error_in_target_form',
            evidence_quote='hi, i a quang', recast_needed=True,
            corrected_form=None,
        )], needs_clarification=False, ambiguity_reason=None,
    )

    class Evaluator:
        async def evaluate(self, request):
            return evidence.model_copy(update={'turn_id': request.turn_id})

    plan = await TurnPlanner(Evaluator(), TeachingEngine(), unit).plan(
        state, 'hi, i a quang', 't1')

    assert plan.decision.feedback_action == 'recast'
    assert not plan.decision.count_attempt
    assert 'target construction has an error' in plan.teacher_request.next_teaching_move
    assert 'two concrete' not in plan.teacher_request.next_teaching_move
    assert plan.teacher_request.constraints.require_repetition


def test_spoken_number_in_level3_range_can_count_as_independent_use():
    unit = load_unit(ROOT / 'curriculum/grade-03/unit-01')
    objective = 'unit01.level03.vocabulary.numbers_20100'
    state = LessonState(
        session_id='grade3-number', unit_id=unit.id, stage_id='level-03',
        activity_id='level-03.introduce-numbers-20100', objective_id=objective,
    )
    evidence = EvaluatorResult(
        turn_id='t1', state_version=state.state_version, response_kind='answer',
        emotional_signals=[],
        objective_evidence=[ObjectiveEvidence(
            objective_id=objective, meaning_status='satisfied',
            target_form_status='correct_target_form', evidence_quote='thirty-five',
            recast_needed=False, corrected_form=None,
        )], needs_clarification=False, ambiguity_reason=None,
    )

    decision = TeachingEngine().decide(state, evidence, unit, learner_text='thirty-five')

    progress = next(item for item in decision.mastery_updates if item.objective_id == objective)
    assert progress.independent_uses == 1
