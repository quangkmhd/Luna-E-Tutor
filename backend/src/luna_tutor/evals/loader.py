from pathlib import Path

import yaml

from luna_tutor.evals.models import CoverageManifest, CoverageResult, Scenario


def _read(path: Path):
    with path.open(encoding='utf-8') as stream:
        return yaml.safe_load(stream)


def load_coverage(path: Path) -> CoverageManifest:
    return CoverageManifest.model_validate(_read(path))


def load_scenarios(path: Path) -> list[Scenario]:
    scenarios: list[Scenario] = []
    for file in sorted(path.glob('*/*.yaml')):
        document = _read(file)
        if not document:
            continue
        scenario_set = file.parent.name
        defaults = document.get('defaults', {})
        source_file = document.get('source_file')
        for raw in document.get('scenarios', []):
            source = {'file': source_file, **raw.pop('source')}
            turn_defaults = defaults.get('turn', {})
            turns = []
            for turn in raw.pop('turns'):
                gold = {**turn_defaults.get('evaluator_gold', {}),
                        **turn.pop('evaluator_gold', {})}
                turns.append({**turn_defaults, **turn, 'evaluator_gold': gold})
            initial = {**defaults.get('initial_state', {}), **raw.pop('initial_state', {})}
            scenarios.append(Scenario.model_validate({
                **defaults.get('scenario', {}), **raw, 'set': scenario_set,
                'source': source, 'initial_state': initial, 'turns': turns,
            }))
    ids = [scenario.id for scenario in scenarios]
    if len(ids) != len(set(ids)):
        raise ValueError('Scenario IDs must be unique')
    return scenarios


def validate_coverage(manifest: CoverageManifest, scenarios: list[Scenario],
                      rules: set[str]) -> CoverageResult:
    by_id = {scenario.id: scenario for scenario in scenarios}
    missing_source = [scenario_id for scenario_id in manifest.numbered_scenario_ids
                      if scenario_id not in by_id or not by_id[scenario_id].source.numbered]
    covered_rules = {rule for rule, scenario_ids in manifest.rule_scenarios.items()
                     if rule in rules and any(item in by_id for item in scenario_ids)}
    missing_branches = [branch for branch in manifest.required_branch_ids
                        if not any(item in by_id for item in manifest.branch_scenarios.get(branch, []))]
    covered_objectives = {objective for scenario in scenarios for objective in scenario.objective_ids}
    return CoverageResult(
        numbered_scenarios=len(manifest.numbered_scenario_ids),
        missing_source_refs=missing_source,
        covered_rule_ids=covered_rules,
        missing_branch_ids=missing_branches,
        missing_objective_ids=[item for item in manifest.required_objective_ids
                               if item not in covered_objectives],
    )
