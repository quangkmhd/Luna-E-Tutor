from pathlib import Path

import yaml


def test_speaking_scenarios_cover_support_freedom_and_early_finish():
    path = Path(__file__).parents[3] / 'evals/speaking-grade5/scenarios.yaml'
    scenarios = yaml.safe_load(path.read_text())
    names = {item['name'] for item in scenarios}
    assert {'beginner_help', 'independent_answer', 'child_question',
            'unclear_audio', 'finish_without_all_words'} <= names
    finish = next(item for item in scenarios if item['name'] == 'finish_without_all_words')
    assert finish['expect']['unseen'] == ['carrot', 'feed']
