from collections import Counter, defaultdict
import json

from pydantic import Field

from luna_tutor.domain.contracts import Contract, Identifier


class EvalRecord(Contract):
    scenario_id: Identifier
    turn_index: int = Field(ge=1)
    repetition: int = Field(ge=1)
    expected: dict
    actual: dict | None
    schema_valid: bool
    provider_failure: bool
    latency_ms: float = Field(ge=0)
    hard_rule_failures: list[str] = Field(default_factory=list)
    differences: dict = Field(default_factory=dict)


class EvalMetrics(Contract):
    total: int
    field_accuracy: float
    schema_validity: float
    provider_failures: int
    invalid_responses: int
    hard_rule_failures: dict[str, int]
    unstable_scenarios: list[str]
    latency_p50_ms: float
    latency_p95_ms: float
    accepted: bool


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def calculate_metrics(records: list[EvalRecord]) -> EvalMetrics:
    total = len(records)
    correct = 0
    signatures: dict[str, set[str]] = defaultdict(set)
    hard = Counter()
    for record in records:
        if record.actual is not None and all(
                record.actual.get(key) == value for key, value in record.expected.items()):
            correct += 1
        if record.actual is not None:
            signatures[f'{record.scenario_id}:{record.turn_index}'].add(
                json.dumps(record.actual, sort_keys=True, ensure_ascii=False))
        hard.update(record.hard_rule_failures)
    valid = sum(record.schema_valid for record in records)
    provider_failures = sum(record.provider_failure for record in records)
    unstable = sorted(key for key, values in signatures.items() if len(values) > 1)
    accepted = bool(total) and valid == total and not provider_failures and not hard
    return EvalMetrics(
        total=total,
        field_accuracy=correct / total if total else 0.0,
        schema_validity=valid / total if total else 0.0,
        provider_failures=provider_failures,
        invalid_responses=total - valid - provider_failures,
        hard_rule_failures=dict(sorted(hard.items())),
        unstable_scenarios=unstable,
        latency_p50_ms=_percentile([r.latency_ms for r in records], .5),
        latency_p95_ms=_percentile([r.latency_ms for r in records], .95),
        accepted=accepted,
    )
