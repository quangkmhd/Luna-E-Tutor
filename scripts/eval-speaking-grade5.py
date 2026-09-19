import argparse
from pathlib import Path
from uuid import uuid4

import httpx
import yaml


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    args = parser.parse_args()
    scenarios = yaml.safe_load((Path(__file__).parents[1] /
        'evals/speaking-grade5/scenarios.yaml').read_text())
    passed = 0
    with httpx.Client(base_url=args.base_url, timeout=30) as api:
        for scenario in scenarios:
            session = api.post('/api/speaking/sessions', json={
                'grade': 5, 'topic': scenario['topic'], 'words': scenario['words']
            }).raise_for_status().json()
            for text in scenario['turns']:
                result = api.post(f"/api/speaking/sessions/{session['session_id']}/turns", json={
                    'turn_id': str(uuid4()), 'text': text,
                    'expected_version': session['version'],
                }).raise_for_status().json()
                session = result['state']
            expected_status = scenario['expect'].get('status')
            ok = expected_status is None or session['status'] == expected_status
            print(('PASS' if ok else 'FAIL'), scenario['name'])
            passed += int(ok)
    if passed != len(scenarios): raise SystemExit(1)


if __name__ == '__main__': main()
