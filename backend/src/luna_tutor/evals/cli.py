import argparse
import asyncio
import json
from pathlib import Path

from luna_tutor.config import Settings
from luna_tutor.evals.loader import load_coverage, load_scenarios, validate_coverage
from luna_tutor.evals.runner import EvalRunner
from luna_tutor.llm.evaluator import GeminiEvaluator
from luna_tutor.llm.openrouter import OpenRouterClient


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='luna-eval')
    sub = parser.add_subparsers(dest='command', required=True)
    run = sub.add_parser('run')
    run.add_argument('--set', choices=['development', 'holdout'], required=True)
    run.add_argument('--repetitions', type=int, default=1)
    run.add_argument('--out', type=Path, required=True)
    run.add_argument('--recorded', type=Path)
    run.add_argument('--baseline', type=Path)
    verify = sub.add_parser('verify-baseline')
    verify.add_argument('baseline', type=Path)
    return parser


async def _run(args) -> int:
    root = Path(__file__).resolve().parents[4]
    all_scenarios = load_scenarios(root / 'evals/unit-01')
    manifest = load_coverage(root / 'evals/unit-01/coverage.yaml')
    coverage = validate_coverage(manifest, all_scenarios,
                                 {f'R{i:02d}' for i in range(1, 21)})
    if (coverage.missing_source_refs or coverage.missing_branch_ids
            or coverage.missing_objective_ids
            or coverage.covered_rule_ids != {f'R{i:02d}' for i in range(1, 21)}):
        print('FAIL: incomplete coverage')
        return 2
    scenarios = [item for item in all_scenarios
                 if item.set == args.set]
    if args.recorded:
        report = EvalRunner(root, evaluator=None).rescore(args.recorded, args.out)
    else:
        async with OpenRouterClient(Settings.from_env()) as client:
            report = await EvalRunner(root, GeminiEvaluator(client)).run(
                scenarios, args.repetitions, args.out)
    accepted = report.accepted
    if args.set == 'holdout' and args.baseline and args.baseline.exists():
        baseline = json.loads(args.baseline.read_text(encoding='utf-8'))
        current = json.loads(report.json_path.read_text(encoding='utf-8'))
        accepted = accepted and (
            current['metrics']['field_accuracy'] >= baseline['metrics']['field_accuracy'])
    print(report.json_path)
    return 0 if accepted else 1


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    if args.command == 'run':
        return asyncio.run(_run(args))
    payload = json.loads(args.baseline.read_text(encoding='utf-8'))
    metrics = payload.get('metrics', payload)
    accepted = (metrics.get('schema_validity') == 1.0
                and not metrics.get('hard_rule_failures')
                and not metrics.get('provider_failures'))
    print('PASS' if accepted else 'FAIL')
    return 0 if accepted else 1


if __name__ == '__main__':
    raise SystemExit(main())
