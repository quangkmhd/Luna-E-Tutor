from luna_tutor.evals.metrics import EvalRecord, calculate_metrics


def record(**changes):
    values = dict(scenario_id='s1', turn_index=1, repetition=1,
                  expected={'response_kind': 'answer'}, actual={'response_kind': 'answer'},
                  schema_valid=True, provider_failure=False, latency_ms=100.0,
                  hard_rule_failures=[])
    values.update(changes)
    return EvalRecord(**values)


def test_hard_rule_failure_is_independent_from_high_accuracy():
    metrics = calculate_metrics([
        record(), record(scenario_id='s2', hard_rule_failures=['R14']),
    ])
    assert metrics.field_accuracy == 1.0
    assert metrics.hard_rule_failures == {'R14': 1}
    assert not metrics.accepted


def test_provider_failures_remain_in_denominator():
    metrics = calculate_metrics([record(), record(
        scenario_id='s2', actual=None, schema_valid=False, provider_failure=True)])
    assert metrics.total == 2
    assert metrics.provider_failures == 1
    assert metrics.schema_validity == 0.5
    assert metrics.field_accuracy == 0.5


def test_repeated_different_outputs_are_unstable():
    metrics = calculate_metrics([
        record(repetition=1),
        record(repetition=2, actual={'response_kind': 'off_topic'}),
    ])
    assert metrics.unstable_scenarios == ['s1:1']
