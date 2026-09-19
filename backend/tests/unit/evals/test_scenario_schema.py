from pathlib import Path

from luna_tutor.evals.loader import load_scenarios


ROOT = Path(__file__).resolve().parents[4]


def test_every_scenario_has_source_gold_behavior_and_teacher_criteria():
    scenarios = load_scenarios(ROOT / 'evals/unit-01')
    assert scenarios
    for scenario in scenarios:
        assert scenario.source.heading
        assert scenario.initial_state.stage_id
        assert scenario.turns
        for turn in scenario.turns:
            assert turn.evaluator_gold.response_kind
            assert turn.allowed_feedback_actions
            assert turn.forbidden_behaviors
            assert turn.teacher_criteria


def test_holdout_uses_distinct_learner_wording():
    scenarios = load_scenarios(ROOT / 'evals/unit-01')
    development = {turn.learner_text.casefold() for s in scenarios if s.set == 'development'
                   for turn in s.turns}
    holdout = {turn.learner_text.casefold() for s in scenarios if s.set == 'holdout'
               for turn in s.turns}
    assert development.isdisjoint(holdout)
