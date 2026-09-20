import json
import yaml
import pytest

from luna_tutor.teaching import descriptions
from luna_tutor.teaching.planner import TurnPlanner
from luna_tutor.domain.decisions import TeachingDecision, TeacherTurnRequest
from luna_tutor.llm.teacher import GeminiTeacher
from luna_tutor.prompts.loader import load_system_prompt


def test_teacher_prompt_requires_standard_vietnamese_diacritics():
    prompt = load_system_prompt('teacher-system.yaml')
    assert 'use standard Vietnamese spelling with full diacritics' in prompt
    assert 'Never omit tone marks or other Vietnamese diacritics' in prompt


def test_teacher_prompt_and_descriptions_quote_repeated_target_words_for_tts():
    prompt = load_system_prompt('teacher-system.yaml')
    catalog = yaml.safe_load(descriptions.CATALOG_PATH.read_text())
    constraints = ' '.join(item['description_en'] for item in catalog['additional_constraints'])

    assert 'Never write isolated vocabulary repetitions as separate punctuated sentences' in prompt
    assert '“class”' in prompt
    assert 'Never write isolated vocabulary repetitions as separate punctuated sentences' in constraints
    assert '“class”' in constraints


@pytest.mark.asyncio
async def test_yaml_edits_reach_planner_and_teacher(tmp_path, monkeypatch, unit_01):
    data = yaml.safe_load(descriptions.CATALOG_PATH.read_text())
    data['planner_branches']['clarify']['description_en'] = 'Ask gently what Quang meant.'
    data['activity_instructions'][0]['description_en'] = 'Say a warm hello.'
    path = tmp_path / 'descriptions.yaml'
    path.write_text(yaml.safe_dump(data))
    monkeypatch.setattr(descriptions, 'CATALOG_PATH', path)
    planner = TurnPlanner(None, None, unit_01)
    assert 'clarify' in planner._descriptions.branches
    current = unit_01.activities[0]
    move = planner._next_move_text(current, TeachingDecision(
        feedback_action='clarify', progression_action='stay'))
    assert move == 'Ask gently what Quang meant.'
    current_move = planner._next_move_text(current, TeachingDecision(
        feedback_action='acknowledge_and_continue', progression_action='stay'))
    assert current_move.endswith('Say a warm hello.')
    assert 'Respond to what Quang just said' in current_move

    class CaptureClient:
        async def text_chat(self, messages, request_id):
            self.messages = messages
            return 'Could you help me understand?'

    client = CaptureClient()
    await GeminiTeacher(client).respond(TeacherTurnRequest(
        turn_id='yaml-test', feedback_action='clarify', learner_meaning='CD',
        next_teaching_move=move))
    assert client.messages[0]['content'] == load_system_prompt('teacher-system.yaml')
    assert json.loads(client.messages[1]['content'])['next_teaching_move'] == move
