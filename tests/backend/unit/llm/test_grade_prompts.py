import pytest

from luna_tutor.prompts.loader import load_grade_system_prompt


def test_grade_prompts_are_distinct_and_keep_shared_rules():
    teacher3 = load_grade_system_prompt(3, 'teacher')
    teacher5 = load_grade_system_prompt(5, 'teacher')
    evaluator3 = load_grade_system_prompt(3, 'evaluator')
    evaluator5 = load_grade_system_prompt(5, 'evaluator')
    assert 'Grade 3' in teacher3 and 'Grade 5' not in teacher3
    assert 'Grade 5' in teacher5
    assert 'Grade 3' in evaluator3 and 'Grade 5' not in evaluator3
    assert 'Grade 5' in evaluator5
    assert 'deterministic teaching code' in teacher3
    assert 'Return exactly one JSON object' in evaluator3
    for grade5_example in ('countryside', 'birthday', 'however', 'moreover', 'Class. Class.', 'hobby'):
        assert grade5_example not in teacher3
        assert grade5_example not in evaluator3


def test_missing_grade_fails_without_fallback():
    with pytest.raises(ValueError, match='grade-04.*teacher'):
        load_grade_system_prompt(4, 'teacher')
