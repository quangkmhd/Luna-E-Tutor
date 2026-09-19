from pathlib import Path

import pytest

from luna_tutor.evals.loader import load_scenarios
from luna_tutor.evals.runner import EvalRunner
from luna_tutor.evals.metrics import EvalRecord
from luna_tutor.llm.evaluator import InvalidEvaluatorResultError


ROOT = Path(__file__).resolve().parents[3]


class FakeEvaluator:
    def __init__(self):
        self.requests = []

    async def evaluate(self, request):
        from luna_tutor.domain.evidence import EvaluatorResult
        self.requests.append(request)
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
    payload = __import__('json').loads(text)
    assert 'meaning_status' not in payload['records'][0]['expected']
    assert 'target_form_status' not in payload['records'][0]['expected']
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


@pytest.mark.asyncio
async def test_runner_redacts_scenario_contact_before_request(tmp_path):
    scenario = next(item for item in load_scenarios(ROOT / 'evals/unit-01')
                    if item.id == 'station2-08')
    evaluator = FakeEvaluator()
    report = await EvalRunner(ROOT, evaluator).run([scenario], repetitions=1, output_dir=tmp_path)
    assert evaluator.requests == []
    payload = __import__('json').loads(report.json_path.read_text())
    assert payload['records'][0]['schema_valid']
    assert payload['records'][0]['hard_rule_failures'] == []


@pytest.mark.asyncio
async def test_invalid_model_output_is_not_counted_as_provider_failure(tmp_path):
    class InvalidEvaluator:
        async def evaluate(self, request):
            raise InvalidEvaluatorResultError(
                status_code=200, request_id=request.turn_id, reason='invalid')

    scenario = load_scenarios(ROOT / 'evals/unit-01')[0]
    report = await EvalRunner(ROOT, InvalidEvaluator()).run(
        [scenario], repetitions=1, output_dir=tmp_path)
    payload = __import__('json').loads(report.json_path.read_text())
    assert payload['metrics']['provider_failures'] == 0
    assert payload['metrics']['invalid_responses'] == 1


@pytest.mark.asyncio
async def test_runner_passes_scenario_transcript_status_to_evaluator(tmp_path):
    scenario = next(item for item in load_scenarios(ROOT / 'evals/unit-01')
                    if item.id == 'station1-06')
    evaluator = FakeEvaluator()
    await EvalRunner(ROOT, evaluator).run([scenario], 1, tmp_path)
    assert evaluator.requests[0].transcript_status == 'uncertain'


@pytest.mark.asyncio
async def test_runner_passes_scenario_teacher_turn_to_evaluator(tmp_path):
    scenario = next(item for item in load_scenarios(ROOT / 'evals/unit-01')
                    if item.id == 'station1-08')
    evaluator = FakeEvaluator()
    await EvalRunner(ROOT, evaluator).run([scenario], 1, tmp_path)
    assert evaluator.requests[0].teacher_turn == 'Where do you live?'


@pytest.mark.asyncio
async def test_runner_scores_current_objective_not_first_model_evidence(tmp_path):
    from luna_tutor.domain.evidence import EvaluatorResult, ObjectiveEvidence

    scenario = next(item for item in load_scenarios(ROOT / 'evals/unit-01')
                    if item.id == 'station2-01')

    class MultiEvaluator:
        async def evaluate(self, request):
            evidence = [ObjectiveEvidence(
                objective_id=item.objective_id, meaning_status='not_demonstrated',
                target_form_status='not_used', evidence_quote=None,
                recast_needed=False, corrected_form=None) for item in request.active_objectives]
            current = next(item for item in evidence
                           if item.objective_id == scenario.initial_state.objective_id)
            evidence[evidence.index(current)] = current.model_copy(update={
                'meaning_status': 'satisfied',
                'target_form_status': scenario.turns[0].evaluator_gold.target_form_status,
                'evidence_quote': scenario.turns[0].learner_text,
            })
            return EvaluatorResult(
                turn_id=request.turn_id, state_version=0, response_kind='asks_teacher',
                emotional_signals=[], objective_evidence=evidence,
                needs_clarification=False, ambiguity_reason=None)

    report = await EvalRunner(ROOT, MultiEvaluator()).run([scenario], 1, tmp_path)
    payload = __import__('json').loads(report.json_path.read_text())
    assert payload['records'][0]['differences'] == {}
