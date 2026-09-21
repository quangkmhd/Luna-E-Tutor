from pathlib import Path

from luna_tutor.curriculum.excel_importer import import_workbook
from luna_tutor.curriculum.loader import load_unit
from luna_tutor.curriculum.registry import CurriculumRegistry
from luna_tutor.evals.loader import load_coverage, load_scenarios, validate_coverage


ROOT = Path(__file__).resolve().parents[4]


def test_grade3_hello_source_and_curriculum():
    imported = import_workbook(ROOT / 'docs/Global_Success_Khung_Nghe_Noi_3_Level_v3.xlsx', 3, 1)
    curriculum = load_unit(ROOT / 'curriculum/grade-03/unit-01')
    assert curriculum.id == 'grade03.unit01'
    assert curriculum.title == 'Hello'
    assert {item.id: item.text for item in curriculum.vocabulary} == {item.id: item.text for item in imported.vocabulary}
    assert {item.id: item.text for item in curriculum.patterns} == {item.id: item.text for item in imported.patterns}
    assert [stage.id for stage in curriculum.stages] == [
        'warm-up', 'lesson-01', 'lesson-02', 'lesson-03',
        'level-02', 'level-03', 'free-talk', 'summary',
    ]
    assert not any('Ôn tập' in objective.description for objective in curriculum.objectives)


def test_grade3_and_grade5_have_distinct_unit_one_curricula():
    registry = CurriculumRegistry(ROOT / 'curriculum', ('grade03.unit01', 'grade05.unit01'))
    assert [(unit.id, unit.title) for unit in registry.list_units()] == [
        ('grade03.unit01', 'Hello'), ('grade05.unit01', 'All about me!')]
    assert registry.get('grade03.unit01').grade == 3


def test_grade3_eval_covers_each_learning_stage_and_free_talk():
    root = ROOT / 'evals/grade-03-unit-01'
    coverage = load_coverage(root / 'coverage.yaml')
    scenarios = load_scenarios(root)
    result = validate_coverage(coverage, scenarios, set())
    assert len(scenarios) == 6
    assert not result.missing_source_refs
    assert not result.missing_branch_ids
    assert not result.missing_objective_ids
