from pathlib import Path

from luna_tutor.curriculum.loader import load_unit
from luna_tutor.domain.evidence import EvaluatorResult, ObjectiveEvidence
from luna_tutor.domain.state import LessonState
from luna_tutor.teaching.engine import TeachingEngine


ROOT = Path(__file__).resolve().parents[4]


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
