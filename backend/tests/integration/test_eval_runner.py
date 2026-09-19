from pathlib import Path

import pytest

from luna_tutor.evals.loader import load_scenarios
from luna_tutor.evals.runner import EvalRunner
from luna_tutor.evals.metrics import EvalRecord


ROOT = Path(__file__).resolve().parents[3]


class FakeEvaluator:
    async def evaluate(self, request):
        from luna_tutor.domain.evidence import EvaluatorResult
        return EvaluatorResult(
            turn_id=request.turn_id, state_version=request.state_version,
            response_kind='answer', emotional_signals=[], objective_evidence=[],
            needs_clarification=False, ambiguity_reason=None)


@pytest.mark.asyncio
async def test_runner_writes_versioned_json_and_markdown_without_raw_transcript(tmp_path):
    scenarios = load_scenarios(ROOT / 'evals/unit-01')[:1]
    runner = EvalRunner(ROOT, FakeEvaluator())
    report = await runner.run(scenarios, repetitions=2, output_dir=tmp_path)
    assert report.json_path.exists()
    assert report.markdown_path.exists()
    assert report.prompt_sha256
    assert report.curriculum_sha256
    text = report.json_path.read_text()
    assert scenarios[0].turns[0].learner_text not in text
    assert len(list(tmp_path.glob('*.json'))) == 1


def test_offline_rescore_writes_new_artifacts_without_evaluator(tmp_path):
    runner = EvalRunner(ROOT, evaluator=None)
    records = [EvalRecord(
        scenario_id='offline-one', turn_index=1, repetition=1,
        expected={'response_kind': 'answer'}, actual={'response_kind': 'answer'},
        schema_valid=True, provider_failure=False, latency_ms=4,
    )]
    recorded = tmp_path / 'recorded.json'
    recorded.write_text(__import__('json').dumps({
        'records': [item.model_dump(mode='json') for item in records]}))
    first = runner.rescore(recorded, tmp_path)
    second = runner.rescore(recorded, tmp_path)
    assert first.json_path != second.json_path
    assert first.json_path.exists() and second.json_path.exists()
