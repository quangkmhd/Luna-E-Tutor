from pathlib import Path

from luna_tutor.evals.loader import load_coverage, load_scenarios, validate_coverage


ROOT = Path(__file__).resolve().parents[4]


def test_manifest_covers_all_numbered_dialogue_scenarios():
    manifest = load_coverage(ROOT / 'evals/unit-01/coverage.yaml')
    scenarios = load_scenarios(ROOT / 'evals/unit-01')
    result = validate_coverage(manifest, scenarios, {f'R{i:02d}' for i in range(1, 21)})
    assert result.numbered_scenarios == 40
    assert result.missing_source_refs == []


def test_manifest_covers_every_rule_branch_and_curriculum_objective():
    manifest = load_coverage(ROOT / 'evals/unit-01/coverage.yaml')
    scenarios = load_scenarios(ROOT / 'evals/unit-01')
    result = validate_coverage(manifest, scenarios, {f'R{i:02d}' for i in range(1, 21)})
    assert result.covered_rule_ids == {f'R{i:02d}' for i in range(1, 21)}
    assert result.missing_branch_ids == []
    assert result.missing_objective_ids == []
