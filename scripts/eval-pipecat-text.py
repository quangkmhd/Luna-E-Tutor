"""Run real text teaching cases, preserving outputs and pending semantic criteria.

Run with the voice/server environment after uv sync. No speech providers are used.
"""
import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'voice/server'))

import pipecat
from dotenv import dotenv_values
from luna_tutor.config import Settings
from luna_tutor.curriculum.registry import CurriculumRegistry, SUPPORTED_UNIT_IDS
from luna_tutor.evals.behavior import BehaviorRunner
from luna_tutor.evals.loader import load_scenarios
from luna_tutor.llm.evaluator import GeminiEvaluator
from luna_tutor.llm.openrouter import OpenRouterClient, OpenRouterError, _redact_contact
from luna_tutor.llm.teacher import GeminiTeacher
from luna_tutor.teaching.engine import TeachingEngine
from luna_tutor.teaching.planner import TurnPlanner
from luna_tutor.teaching.turn_service import TurnService
from text_pipeline import PipecatTurnService


class DiagnosticClient(OpenRouterClient):
    """Synthetic eval-only diagnostics; never retain HTTP requests or credentials."""

    def __init__(self, settings):
        super().__init__(settings)
        self.calls = []

    async def structured_chat(self, messages, schema, request_id):
        call = {'turn_id': request_id,
                'component': 'teacher' if 'spoken_text' in schema.get('properties', {}) else 'evaluator',
                'input': _redact_contact(json.loads(messages[-1]['content']))}
        self.calls.append(call)
        try:
            output = await super().structured_chat(messages, schema, request_id)
        except Exception as error:
            call['error_type'] = type(error).__name__
            if isinstance(error, OpenRouterError):
                call.update(error_status=error.status_code, error_reason=error.reason)
            raise
        call['parsed_output'] = _redact_contact(output)
        return output


async def run(args):
    registry = CurriculumRegistry(
        ROOT / 'curriculum',
        SUPPORTED_UNIT_IDS,
    )
    unit = registry.get(args.unit)
    unit_slug = (
        f'grade-{unit.grade:02d}-unit-{unit.unit:02d}'
        if unit.grade != 5 else f'unit-{unit.unit:02d}'
    )
    scenario_dir = ROOT / 'evals' / unit_slug
    curriculum_dir = ROOT / 'curriculum' / f'grade-{unit.grade:02d}' / f'unit-{unit.unit:02d}'
    scenarios = [s for s in load_scenarios(scenario_dir)
                 if s.id in args.scenario] if args.scenario else [
        s for s in load_scenarios(scenario_dir) if s.source.numbered]
    if args.scenario and set(args.scenario) != {s.id for s in scenarios}:
        raise ValueError('Unknown scenario ID')
    values = dotenv_values(args.env_file)
    settings = Settings(openrouter_api_key=values['OPENROUTER_API_KEY'])
    sources = sorted(set(
        [Path(__file__).resolve()] + list((ROOT / 'backend/src/luna_tutor').rglob('*.py'))
        + list((ROOT / 'backend/src/luna_tutor/prompts').glob('*.yaml'))
        + list(curriculum_dir.rglob('*.yaml'))
        + list((scenario_dir / 'development').glob('*.yaml'))
        + list((ROOT / 'voice/server').glob('*.py'))))
    payload = {
        'scope': 'real_pipecat_evaluator_engine_teacher_text',
        'unit_id': unit.id,
        'pipecat_version': pipecat.__version__,
        'hashes': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in sources},
        'semantic_review': 'pending', 'complete': False, 'records': [],
    }
    # Exclusive creation protects previous experimental evidence.
    with args.output.open('x', encoding='utf-8') as output:
        def checkpoint():
            output.seek(0)
            json.dump(payload, output, indent=2, ensure_ascii=False)
            output.truncate()
            output.flush()
        checkpoint()
        async with DiagnosticClient(settings) as client:
            service = PipecatTurnService(TurnService(
                TurnPlanner(GeminiEvaluator(client, grade=unit.grade), TeachingEngine(), unit),
                GeminiTeacher(client, grade=unit.grade)))
            runner = BehaviorRunner(ROOT, service, unit.id)
            for scenario in scenarios:
                client.calls.clear()
                records = await runner.run([scenario])
                for record in records:
                    turn_id = f"{scenario.id}-{record['turn_index'] - 1}"
                    calls = [call for call in client.calls if call['turn_id'] == turn_id]
                    record['model_attempts'] = {
                        component: sum(call['component'] == component for call in calls)
                        for component in ('evaluator', 'teacher')}
                    if ('turn_execution' in record['failures'] or
                            any(call['input'].get('validation_feedback') for call in calls)):
                        record['model_diagnostics'] = calls
                payload['records'].extend(records)
                checkpoint()
                print(scenario.id, [r['failures'] for r in records], flush=True)
        payload['complete'] = True
        checkpoint()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scenario', action='append', default=[])
    parser.add_argument('--unit', default='grade05.unit01')
    asyncio.run(run(parser.parse_args()))
