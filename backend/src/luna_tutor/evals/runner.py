from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

from luna_tutor.curriculum.loader import load_unit
from luna_tutor.domain.evidence import ActiveObjective, EvaluatorRequest
from luna_tutor.evals.metrics import EvalRecord, calculate_metrics
from luna_tutor.evals.models import Scenario
from luna_tutor.llm.openrouter import OpenRouterError


@dataclass(frozen=True)
class ReportArtifacts:
    json_path: Path
    markdown_path: Path
    prompt_sha256: str
    curriculum_sha256: str
    accepted: bool


def _sha(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.relative_to(path.parents[2]).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _differences(expected: dict, actual: dict | None) -> dict:
    if actual is None:
        return {key: {'expected': value, 'actual': None} for key, value in expected.items()}
    return {key: {'expected': value, 'actual': actual.get(key)}
            for key, value in expected.items() if actual.get(key) != value}


class EvalRunner:
    def __init__(self, repository_root: Path, evaluator):
        self.root = repository_root
        self.evaluator = evaluator
        self.curriculum = load_unit(repository_root / 'curriculum/grade-05/unit-01')

    def _objective(self, objective_id: str) -> ActiveObjective:
        objective = next(item for item in self.curriculum.objectives if item.id == objective_id)
        patterns = {item.id: item for item in self.curriculum.patterns}
        return ActiveObjective(
            objective_id=objective.id, communicative_goal=objective.description,
            target_patterns=[patterns[item].text for item in objective.pattern_ids],
            acceptable_alternatives=[alternative for item in objective.pattern_ids
                                     for alternative in patterns[item].acceptable_alternatives],
            evidence_criteria=objective.evidence_criteria,
        )

    async def run(self, scenarios: list[Scenario], repetitions: int,
                  output_dir: Path) -> ReportArtifacts:
        records: list[EvalRecord] = []
        for repetition in range(1, repetitions + 1):
            for scenario in scenarios:
                for index, turn in enumerate(scenario.turns, 1):
                    request = EvaluatorRequest(
                        turn_id=f'{scenario.id}-{index}-{repetition}', state_version=0,
                        teacher_turn='', activity_type=scenario.initial_state.stage_id,
                        active_objectives=[self._objective(item) for item in scenario.objective_ids],
                        support_given={}, transcript_status='final',
                        learner_transcript=turn.learner_text, recent_context=[],
                        attempt_count=scenario.initial_state.attempt_count,
                    )
                    started = time.perf_counter()
                    actual = None
                    provider_failure = False
                    schema_valid = False
                    try:
                        result = await self.evaluator.evaluate(request)
                        schema_valid = True
                        first = result.objective_evidence[0] if result.objective_evidence else None
                        actual = {
                            'response_kind': result.response_kind,
                            'meaning_status': first.meaning_status if first else 'not_demonstrated',
                            'target_form_status': first.target_form_status if first else 'not_used',
                            'recast_needed': first.recast_needed if first else False,
                            'emotional_signals': result.emotional_signals,
                            'needs_clarification': result.needs_clarification,
                        }
                    except OpenRouterError:
                        provider_failure = True
                    except (ValueError, TypeError, KeyError):
                        pass
                    expected = turn.evaluator_gold.model_dump()
                    records.append(EvalRecord(
                        scenario_id=scenario.id, turn_index=index, repetition=repetition,
                        expected=expected, actual=actual, schema_valid=schema_valid,
                        provider_failure=provider_failure,
                        latency_ms=(time.perf_counter() - started) * 1000,
                        hard_rule_failures=[], differences=_differences(expected, actual),
                    ))
        return self.write_report(records, output_dir)

    def rescore(self, recorded_path: Path, output_dir: Path) -> ReportArtifacts:
        payload = json.loads(recorded_path.read_text(encoding='utf-8'))
        records = [EvalRecord.model_validate(item) for item in payload['records']]
        return self.write_report(records, output_dir)

    def write_report(self, records: list[EvalRecord], output_dir: Path) -> ReportArtifacts:
        output_dir.mkdir(parents=True, exist_ok=True)
        prompt = self.root / 'backend/src/luna_tutor/prompts/evaluator.md'
        prompt_hash = hashlib.sha256(prompt.read_bytes()).hexdigest()
        curriculum_paths = list((self.root / 'curriculum/grade-05/unit-01').rglob('*.yaml'))
        curriculum_hash = _sha(curriculum_paths)
        metrics = calculate_metrics(records)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        base = output_dir / f'unit-01-{stamp}'
        counter = 1
        while Path(f'{base}.json').exists() or Path(f'{base}.md').exists():
            base = output_dir / f'unit-01-{stamp}-{counter}'
            counter += 1
        json_path = Path(f'{base}.json')
        markdown_path = Path(f'{base}.md')
        payload = {
            'prompt_sha256': prompt_hash, 'curriculum_sha256': curriculum_hash,
            'metrics': metrics.model_dump(mode='json'),
            'records': [record.model_dump(mode='json') for record in records],
        }
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        markdown_path.write_text(
            '# Unit 1 evaluation\n\n'
            f'- Prompt SHA-256: `{prompt_hash}`\n'
            f'- Curriculum SHA-256: `{curriculum_hash}`\n'
            f'- Records: {metrics.total}\n'
            f'- Field accuracy: {metrics.field_accuracy:.3f}\n'
            f'- Schema validity: {metrics.schema_validity:.3f}\n'
            f'- Provider failures: {metrics.provider_failures}\n'
            f'- Invalid responses: {metrics.invalid_responses}\n'
            f'- Hard-rule failures: {json.dumps(metrics.hard_rule_failures)}\n'
            f'- Unstable: {", ".join(metrics.unstable_scenarios) or "none"}\n'
            f'- Latency p50/p95: {metrics.latency_p50_ms:.1f}/{metrics.latency_p95_ms:.1f} ms\n'
            f'- Accepted: {metrics.accepted}\n', encoding='utf-8')
        return ReportArtifacts(json_path, markdown_path, prompt_hash, curriculum_hash,
                               metrics.accepted)
