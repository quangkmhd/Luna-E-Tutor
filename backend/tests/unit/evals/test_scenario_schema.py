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


def test_numbered_behavior_cases_have_unambiguous_activity_and_prior_teacher_turn():
    from luna_tutor.curriculum.loader import load_unit
    unit = load_unit(ROOT / 'curriculum/grade-05/unit-01')
    activities = {a.id: a for a in unit.activities}
    numbered = [s for s in load_scenarios(ROOT / 'evals/unit-01') if s.source.numbered]
    assert len(numbered) == 40
    for scenario in numbered:
        assert scenario.initial_state.activity_id in activities, scenario.id
        activity = activities[scenario.initial_state.activity_id]
        assert activity.stage_id == scenario.initial_state.stage_id
        if scenario.initial_state.objective_id:
            assert scenario.initial_state.objective_id in activity.objective_ids, scenario.id
        # Only the initial prompt is seeded; later turns use the actual Teacher output.
        assert scenario.turns[0].teacher_turn.strip(), scenario.id
        for turn in scenario.turns:
            assert 'attempt_delta' not in turn.expected_state_effects, scenario.id
