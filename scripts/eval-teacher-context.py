"""Small live diagnostic; not a substitute for full Pipecat scenario acceptance.

Run from repository root:
uv run --project backend python scripts/eval-teacher-context.py LABEL --env-file PATH
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path

from dotenv import dotenv_values
from luna_tutor.config import Settings
from luna_tutor.curriculum.registry import CurriculumRegistry
from luna_tutor.domain.decisions import TeacherTurnRequest, TeachingDecision
from luna_tutor.llm.openrouter import OpenRouterClient, OpenRouterError
from luna_tutor.llm.teacher import GeminiTeacher
from luna_tutor.teaching.planner import TurnPlanner


async def run(label: str, env_file: Path | None, unit_id: str):
    root = Path(__file__).resolve().parents[1]
    registry = CurriculumRegistry(
        root / 'curriculum',
        tuple(f'grade05.unit{number:02d}' for number in range(1, 6)),
    )
    unit = registry.get(unit_id)
    unit_slug = f'unit-{unit.unit:02d}'
    output = root / 'evals' / unit_slug / 'text-experiments' / f'teacher-context-{label}.json'
    if output.exists():
        raise ValueError('Use a new label to preserve prior experiment evidence')
    builder = TurnPlanner(None, None, unit)
    values = {**(dotenv_values(env_file) if env_file else {}), **os.environ}
    introduction = next(a for a in unit.activities
                        if a.stage_id == 'lesson-01'
                        and a.kind == 'vocabulary_introduction')
    practice = next(a for a in unit.activities
                    if a.stage_id == 'lesson-01'
                    and a.kind in {'guided_response', 'comprehension'})
    ask_teacher = next(a for a in unit.activities
                       if a.stage_id == 'lesson-01' and a.kind == 'ask_teacher')
    cases = [
        ('meaning', introduction.id, f'{introduction.examples[0]} nghĩa là gì hả cô?',
         introduction.examples[0], 'explain_meaning'),
        ('short', practice.id, practice.examples[0], practice.examples[0],
         'acknowledge_and_continue'),
        ('teacher', ask_teacher.id, ask_teacher.examples[0], ask_teacher.examples[0],
         'answer_teacher_question'),
        ('rough-input', practice.id, 'CD', practice.examples[0],
         'acknowledge_and_continue'),
    ]
    records = []
    async with OpenRouterClient(Settings(openrouter_api_key=values['OPENROUTER_API_KEY'])) as client:
        original_chat = client.structured_chat
        captured = {}

        async def record_chat(*args, **kwargs):
            try:
                raw = await original_chat(*args, **kwargs)
            except OpenRouterError as error:
                captured['error'] = {'reason': error.reason, 'status': error.status_code}
                raise
            captured['raw'] = raw
            return raw

        client.structured_chat = record_chat
        teacher = GeminiTeacher(client)
        for name, activity_id, text, previous, action in cases:
            captured.clear()
            activity = next(a for a in unit.activities if a.id == activity_id)
            request = TeacherTurnRequest(
                turn_id='context-' + name, feedback_action=action,
                learner_meaning=text, previous_teacher_turn=previous,
                next_teaching_move=builder._next_move_text(activity, TeachingDecision(
                    feedback_action=action, progression_action='stay')),
                activity_context=builder._teacher_context(activity, enforce_delivery=action not in {'explain_meaning', 'clarify'}))
            reply = await teacher.respond(request)
            records.append({'case': name, 'request': request.model_dump(mode='json'),
                            'output': reply.model_dump(mode='json'), **captured})
    prompt = root / 'backend/src/luna_tutor/prompts/teacher-system.yaml'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({
        'scope': 'isolated_teacher_diagnostic',
        'unit_id': unit.id,
        'model': 'google/gemini-3.5-flash-lite',
        'prompt_sha256': hashlib.sha256(prompt.read_bytes()).hexdigest(),
        'records': records,
    }, indent=2, ensure_ascii=False), encoding='utf-8')
    for record in records:
        print(record['case'], record['output'])
    print(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('label')
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--unit', default='grade05.unit01')
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-_' for c in args.label):
        parser.error('label must contain only lowercase letters, digits, hyphen or underscore')
    asyncio.run(run(args.label, args.env_file, args.unit))
